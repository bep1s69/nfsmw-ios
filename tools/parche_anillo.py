#!/usr/bin/env python3
"""
Escucha la conversacion entre el juego y el XMA, del lado del kernel.  (v3)

    python tools/parche_anillo.py            aplicar
    python tools/parche_anillo.py --estado
    python tools/parche_anillo.py --revertir

Toca un fichero del SDK:  src/kernel/xboxkrnl/xboxkrnl_audio_xma.cpp


DONDE ESTAMOS
=============

El cuelgue esta acorralado hasta el milisegundo. Esta es la voz 19 muriendo,
tal cual salio en el log:

    57.907  Work escritura=8  lectura=12  hueco=4     <- ultimo pase que produjo
    57.924  Work escritura=12 lectura=16  hueco=4     NO PRODUJO NADA ent0=0 ent1=0
    57.935  Work escritura=12 lectura=20  hueco=8     NO PRODUJO NADA ent0=0 ent1=0
    57.945  Work escritura=12 lectura=0   hueco=12    NO PRODUJO NADA ent0=0 ent1=0
    57.964  Work escritura=12 lectura=4   hueco=16    NO PRODUJO NADA ent0=0 ent1=0
    57.974  Work escritura=12 lectura=8   hueco=20    NO PRODUJO NADA ent0=0 ent1=0
    58.333  [guest] pide escritura: escritura=12 lectura=8 valida=1 ent0=0 ent1=0
            ... y esa misma linea 90 segundos seguidos.

O sea: a las 57.907 el descodificador gasta lo ultimo que tenia de entrada.
Los dos buffers de entrada quedan en cero. El juego sigue dando kicks cinco
veces mas y sigue consumiendo lo que quedaba -la lectura avanza 16, 20, 0, 4,
8-, y al llegar a 8 se para en seco. La escritura lleva congelada en 12 desde
el principio de esa tanda, porque no hay nada que descodificar.

La lectura se queda a UN PASO de alcanzar la escritura. Y eso importa, porque
el bucle del juego solo pregunta si el buffer de salida sigue valido cuando
lectura y escritura coinciden. Al quedarse a un bloque, no llega a preguntar
nunca, y se queda esperando audio que no puede llegar.


LO QUE FALTA POR SABER, Y POR QUE NO SE SUPO ANTES
==================================================

La pregunta que queda es una sola: DESPUES de las 57.907, el juego le vuelve a
dar entrada a esa voz?

  - Si NO se la da, el fallo esta en el juego: se ha metido en el bucle antes
    de rellenar, y hay que mirar por que llego a quedarse sin datos.
  - Si SI se la da y el descodificador sigue diciendo ent0=0 ent1=0, entonces
    la estamos perdiendo nosotros al recibirla, y el fallo es del SDK.

La v2 no lo pudo contestar por un fallo mio: puse UN limite de una linea por
segundo a todas las funciones por igual. Tiene sentido para las dos que el
juego consulta miles de veces por segundo en el bucle, pero no para las que
ESCRIBEN, que se llaman a un ritmo normal. Con ese limite, de las entregas de
entrada solo se veia una por segundo, y ademas la que tocara de cualquier
contexto, no del que interesa.

Asi que ahora:

  - las de consulta -pedir offsets, preguntar validez- siguen limitadas
  - las que ESCRIBEN van sin limite: dar entrada, entregar el buffer con su
    cuenta de paquetes, mover la lectura, revalidar la salida, apagar

Los kicks ya salen enteros por el otro parche, asi que no hacen falta aqui.

Con esto, el tramo entre las 57.907 y el cuelgue queda registrado entero y la
pregunta se contesta sola.
"""

import argparse
import os
import pathlib
import shutil
import sys

MARCA = "PARCHE LOCAL - escucha de la conversacion XMA v3"
MARCAS_VIEJAS = [
    "PARCHE LOCAL - escucha de la conversacion XMA",
    "PARCHE LOCAL - el anillo de salida no se llena del todo",
]

CAB_ANCLA = """#include <cstring>
"""

CAB_NUEVO = """#include <atomic>   // PARCHE LOCAL - escucha de la conversacion XMA v3
#include <chrono>   // PARCHE LOCAL - escucha de la conversacion XMA v3
#include <cstring>
"""

# El ayudante y la primera funcion instrumentada van juntos, para no depender
# de un anclaje mas en la cabecera del namespace.
# El ayudante tiene que quedar declarado ANTES de su primer uso, y la primera
# funcion que lo usa en este fichero es XMAIsInputBuffer0Valid, que aparece
# bastante antes que las de salida. Por eso el bloque cuelga de esa.
AYUDA_ANCLA = """u32 XMAIsInputBuffer0Valid_entry(mapped_void context_ptr) {
  XMA_CONTEXT_DATA context(context_ptr);
  return context.input_buffer_0_valid;
}
"""

AYUDA_NUEVO = """// PARCHE LOCAL - escucha de la conversacion XMA v3
//
// El bucle del juego llama a estas funciones miles de veces por segundo, asi
// que van limitadas a una linea por segundo CADA UNA. Cada una lleva su propio
// reloj -la estatica dentro de la macro-, para que la mas ruidosa no tape a
// las demas.
namespace {
bool XmaDiagToca(std::atomic<int64_t>& ultimo) {
  const int64_t ahora = std::chrono::duration_cast<std::chrono::milliseconds>(
                            std::chrono::steady_clock::now().time_since_epoch())
                            .count();
  int64_t anterior = ultimo.load(std::memory_order_relaxed);
  return ahora - anterior >= 1000 && ultimo.compare_exchange_strong(anterior, ahora);
}
}  // namespace

#define REX_DIAG_XMA(...)                          \\
  do {                                             \\
    static std::atomic<int64_t> _ultimo{0};        \\
    if (XmaDiagToca(_ultimo)) {                    \\
      REXAPU_DEBUG(__VA_ARGS__);                   \\
    }                                              \\
  } while (0)

u32 XMAIsInputBuffer0Valid_entry(mapped_void context_ptr) {
  XMA_CONTEXT_DATA context(context_ptr);
  REX_DIAG_XMA("[guest] pregunta entrada 0: ctx={:08X} -> {}", context_ptr.guest_address(),
               uint32_t(context.input_buffer_0_valid));
  return context.input_buffer_0_valid;
}
"""

PARES = [
("""u32 XMAIsOutputBufferValid_entry(mapped_void context_ptr) {
  XMA_CONTEXT_DATA context(context_ptr);
  return context.output_buffer_valid;
}
""",
 """u32 XMAIsOutputBufferValid_entry(mapped_void context_ptr) {
  XMA_CONTEXT_DATA context(context_ptr);
  REX_DIAG_XMA("[guest] pregunta si la salida vale: ctx={:08X} -> {}", context_ptr.guest_address(),
               uint32_t(context.output_buffer_valid));
  return context.output_buffer_valid;
}
"""),

("""u32 XMASetOutputBufferValid_entry(mapped_void context_ptr) {
  XMA_CONTEXT_DATA context(context_ptr);
  context.output_buffer_valid = 1;
""",
 """u32 XMASetOutputBufferValid_entry(mapped_void context_ptr) {
  XMA_CONTEXT_DATA context(context_ptr);
  REXAPU_DEBUG("[guest] revalida la salida: ctx={:08X}", context_ptr.guest_address());
  context.output_buffer_valid = 1;
"""),

("""u32 XMAGetOutputBufferReadOffset_entry(mapped_void context_ptr) {
  XMA_CONTEXT_DATA context(context_ptr);
  return context.output_buffer_read_offset;
}
""",
 """u32 XMAGetOutputBufferReadOffset_entry(mapped_void context_ptr) {
  XMA_CONTEXT_DATA context(context_ptr);
  REX_DIAG_XMA("[guest] pide lectura: ctx={:08X} lectura={} escritura={} valida={} ent0={} ent1={}",
               context_ptr.guest_address(), uint32_t(context.output_buffer_read_offset),
               uint32_t(context.output_buffer_write_offset),
               uint32_t(context.output_buffer_valid), uint32_t(context.input_buffer_0_valid),
               uint32_t(context.input_buffer_1_valid));
  return context.output_buffer_read_offset;
}
"""),

("""u32 XMASetOutputBufferReadOffset_entry(mapped_void context_ptr, u32 value) {
  XMA_CONTEXT_DATA context(context_ptr);
  context.output_buffer_read_offset = value;
""",
 """u32 XMASetOutputBufferReadOffset_entry(mapped_void context_ptr, u32 value) {
  XMA_CONTEXT_DATA context(context_ptr);
  REXAPU_DEBUG("[guest] mueve la lectura: ctx={:08X} {} -> {}", context_ptr.guest_address(),
               uint32_t(context.output_buffer_read_offset), value);
  context.output_buffer_read_offset = value;
"""),

("""u32 XMAGetOutputBufferWriteOffset_entry(mapped_void context_ptr) {
  XMA_CONTEXT_DATA context(context_ptr);
  return context.output_buffer_write_offset;
}
""",
 """u32 XMAGetOutputBufferWriteOffset_entry(mapped_void context_ptr) {
  XMA_CONTEXT_DATA context(context_ptr);
  REX_DIAG_XMA("[guest] pide escritura: ctx={:08X} escritura={} lectura={} valida={} ent0={} ent1={}",
               context_ptr.guest_address(), uint32_t(context.output_buffer_write_offset),
               uint32_t(context.output_buffer_read_offset),
               uint32_t(context.output_buffer_valid), uint32_t(context.input_buffer_0_valid),
               uint32_t(context.input_buffer_1_valid));
  return context.output_buffer_write_offset;
}
"""),

# --- la entrada, que es lo nuevo y lo que importa ---
("""u32 XMASetInputBuffer0Valid_entry(mapped_void context_ptr) {
  XMA_CONTEXT_DATA context(context_ptr);
  context.input_buffer_0_valid = 1;
""",
 """u32 XMASetInputBuffer0Valid_entry(mapped_void context_ptr) {
  XMA_CONTEXT_DATA context(context_ptr);
  REXAPU_DEBUG("[guest] DA ENTRADA 0: ctx={:08X}", context_ptr.guest_address());
  context.input_buffer_0_valid = 1;
"""),

("""u32 XMAIsInputBuffer1Valid_entry(mapped_void context_ptr) {
  XMA_CONTEXT_DATA context(context_ptr);
  return context.input_buffer_1_valid;
}
""",
 """u32 XMAIsInputBuffer1Valid_entry(mapped_void context_ptr) {
  XMA_CONTEXT_DATA context(context_ptr);
  REX_DIAG_XMA("[guest] pregunta entrada 1: ctx={:08X} -> {}", context_ptr.guest_address(),
               uint32_t(context.input_buffer_1_valid));
  return context.input_buffer_1_valid;
}
"""),

("""u32 XMASetInputBuffer1Valid_entry(mapped_void context_ptr) {
  XMA_CONTEXT_DATA context(context_ptr);
  context.input_buffer_1_valid = 1;
""",
 """u32 XMASetInputBuffer1Valid_entry(mapped_void context_ptr) {
  XMA_CONTEXT_DATA context(context_ptr);
  REXAPU_DEBUG("[guest] DA ENTRADA 1: ctx={:08X}", context_ptr.guest_address());
  context.input_buffer_1_valid = 1;
"""),

("""u32 XMAEnableContext_entry(mapped_void context_ptr) {
  StoreXmaContextIndexedRegister(REX_KERNEL_STATE(), 0x1940, context_ptr.guest_address());
""",
 """u32 XMAEnableContext_entry(mapped_void context_ptr) {
  REX_DIAG_XMA("[guest] enciende el contexto: ctx={:08X}", context_ptr.guest_address());
  StoreXmaContextIndexedRegister(REX_KERNEL_STATE(), 0x1940, context_ptr.guest_address());
"""),

("""u32 XMADisableContext_entry(mapped_void context_ptr, u32 wait) {
  X_HRESULT result = X_E_SUCCESS;
""",
 """u32 XMADisableContext_entry(mapped_void context_ptr, u32 wait) {
  REXAPU_DEBUG("[guest] apaga el contexto: ctx={:08X} esperar={}", context_ptr.guest_address(),
               wait);
  X_HRESULT result = X_E_SUCCESS;
"""),
("""u32 XMASetInputBuffer0_entry(mapped_void context_ptr, mapped_void buffer, u32 packet_count) {
""",
 """u32 XMASetInputBuffer0_entry(mapped_void context_ptr, mapped_void buffer, u32 packet_count) {
  REXAPU_DEBUG("[guest] ENTREGA BUFFER 0: ctx={:08X} datos={:08X} paquetes={}",
               context_ptr.guest_address(), buffer.guest_address(), packet_count);
"""),

("""u32 XMASetInputBuffer1_entry(mapped_void context_ptr, mapped_void buffer, u32 packet_count) {
""",
 """u32 XMASetInputBuffer1_entry(mapped_void context_ptr, mapped_void buffer, u32 packet_count) {
  REXAPU_DEBUG("[guest] ENTREGA BUFFER 1: ctx={:08X} datos={:08X} paquetes={}",
               context_ptr.guest_address(), buffer.guest_address(), packet_count);
"""),
]

ANCLAS = ([("cabeceras", CAB_ANCLA, CAB_NUEVO),
           ("ayudante y consulta de la entrada 0", AYUDA_ANCLA, AYUDA_NUEVO)]
          + [(f"funcion {i + 1}", a, b) for i, (a, b) in enumerate(PARES)])


def localizar_sdk():
    raiz = pathlib.Path(__file__).resolve().parent.parent
    # NFSMW_SDK apunta a otro arbol del SDK (el de Android, por ejemplo). Si
    # esta puesta se usa SOLO esa ruta: caer en silencio en el SDK de Windows
    # parchearia el arbol equivocado.
    otro = os.environ.get("NFSMW_SDK")
    candidatos = [pathlib.Path(otro)] if otro else [raiz.parent / "rexglue-sdk", raiz / "sdk"]
    for cand in candidatos:
        if (cand / "src" / "audio" / "xma_context.cpp").exists():
            return cand
    sys.exit("[ERROR] No encuentro el SDK. Se busca en ..\\rexglue-sdk y en .\\sdk")


def main():
    p = argparse.ArgumentParser(add_help=True)
    p.add_argument("--estado", action="store_true")
    p.add_argument("--revertir", action="store_true")
    args = p.parse_args()

    f = localizar_sdk() / "src" / "kernel" / "xboxkrnl" / "xboxkrnl_audio_xma.cpp"
    if not f.exists():
        sys.exit(f"[ERROR] No encuentro {f}")
    orig = f.with_suffix(f.suffix + ".original")

    if args.estado:
        t = f.read_text(encoding="utf-8")
        if MARCA in t:
            print(f"  {f.name:30s} aplicado")
        elif any(m in t for m in MARCAS_VIEJAS):
            print(f"  {f.name:30s} version ANTERIOR (se cambiara al aplicar)")
        else:
            print(f"  {f.name:30s} sin aplicar")
        return 0

    if args.revertir:
        if orig.exists():
            shutil.copy2(orig, f)
            print(f"[ok] Restaurado {f.name}")
        else:
            print(f"[aviso] No hay copia de {f.name}, no habia nada que deshacer")
        print()
        print("  HAY QUE RECOMPILAR EL SDK.")
        return 0

    txt = f.read_text(encoding="utf-8")
    if MARCA in txt:
        print(f"[ok] {f.name}: ya estaba al dia, no lo toco")
        return 0

    # La version anterior de este parche dejaba sus lineas por medio, y los
    # anclajes de abajo estan escritos contra el fichero limpio.
    if any(m in txt for m in MARCAS_VIEJAS):
        if not orig.exists():
            sys.exit(f"[ERROR] {f.name} tiene la version anterior pero no hay\n"
                     f"        {orig.name} para deshacerla.")
        shutil.copy2(orig, f)
        txt = f.read_text(encoding="utf-8")
        print(f"[ok] {f.name}: quitada la version anterior")

    for nombre, ancla, _ in ANCLAS:
        n = txt.count(ancla)
        if n != 1:
            sys.exit(f"[ERROR] El anclaje '{nombre}' aparece {n} veces, esperaba 1.\n"
                     f"        El SDK habra cambiado. No he tocado nada.")

    if not orig.exists():
        shutil.copy2(f, orig)
        print(f"[ok] Copia de seguridad: {orig.name}")

    for _, ancla, nuevo in ANCLAS:
        txt = txt.replace(ancla, nuevo)
    f.write_text(txt, encoding="utf-8")
    print(f"[ok] Parcheado {f.name}")
    print()
    print("  Se vera la conversacion entera entre el juego y el XMA.")
    print("  Las consultas van limitadas a una linea por segundo; las que")
    print("  ESCRIBEN -dar entrada, mover la lectura, apagar- van enteras,")
    print("  que son las que hacian falta y el limite tapaba.")
    print()
    print("  HAY QUE RECOMPILAR EL SDK para que sirva de algo:")
    print("    cmake --build out/build/win-amd64 --config Release --target install")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
