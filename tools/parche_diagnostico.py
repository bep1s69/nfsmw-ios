#!/usr/bin/env python3
"""
Dos parches al SDK sobre hilos y memoria.  (version 3)

    python tools/parche_diagnostico.py            aplicar
    python tools/parche_diagnostico.py --estado
    python tools/parche_diagnostico.py --revertir

Toca dos ficheros del SDK:
    src/system/xmemory.cpp    el mensaje de la violacion de acceso
    src/system/xthread.cpp    el arranque de cada hilo del guest

Guarda un .original de cada uno la primera vez y es idempotente. Si detecta
una version ANTERIOR de este mismo parche, la revierte antes de aplicar la
nueva: asi se puede reaplicar encima sin acumular capas.


QUE SE SABE YA, Y POR QUE HACE FALTA LA VERSION 2
=================================================

La version 1 contesto la primera pregunta. El log del crash paso de esto:

    Unhandled guest access violation: read of guest 0x00000000
      on thread 0xF8000028

a esto:

    [hilo guest] arrancando: entrada=0x8262E768 start_address=0x8262E768
                 contexto=0x00000000 trampolin_xapi=0x00000000 pila=262144
    [hilo guest] id=0x6 entrada=0x8262E768 principal=true
                 creado_por_el_juego=true
    [contexto ppc] lr=0x00000000 ultimo_salto_indirecto=0x00000000
                   r1=0x70190000 r3=0 r4=0 r5=0 ...

Y eso, en 20 ejecuciones de 20, siempre igual. Lo que dice:

  - 0x8262E768 NO es un hilo secundario: es el PUNTO DE ENTRADA DEL JUEGO.
    principal=true, y start_address sale de la cabecera del XEX, no de
    ninguna heuristica. Nunca llega a arrancar un segundo hilo.
  - lr=0 y ultimo_salto_indirecto=0: muere en las primeras instrucciones,
    antes de llamar a nada.
  - r1 es una pila valida (0x70190000, dentro de 0x70000000-0x7F000000).

Y lo que apunta a la causa: las DOS direcciones que fallan son 0x00000000 y
0x00000100. No son numeros cualesquiera. En el propio xthread.cpp del SDK,
justo encima de donde se reserva el PCR, esta el mapa:

    // 0x000: pointer to tls data
    // 0x100: pointer to TEB(?)

O sea que las dos lecturas que revientan son 0(r13) y 0x100(r13) con r13
valiendo CERO. r13 es el puntero al PCR, y lo pone ThreadState al construirse:

    context_->r13.u64 = pcr_address;   // src/system/thread_state.cpp

La hipotesis, entonces, es que r13 llega a cero al codigo recompilado. Lo que
NO se sabe es si llega a cero porque pcr_address_ es cero -y entonces el fallo
esta en la reserva de memoria del guest- o porque el contexto se pierde entre
la creacion del hilo y la llamada -y entonces el fallo esta en otro sitio-.

Un solo registro separa las dos historias. Por eso esta version 2.


LO QUE ANADE LA VERSION 2
=========================

1. r13 en el volcado de registros, junto con r2, r12 y r30. Y ademas
   pcr_ptr() y tls_ptr() leidos del propio XThread, que es el valor que el
   SDK CREE haber puesto. Si pcr_ptr() trae un valor y r13 vale cero, el
   contexto se esta perdiendo por el camino. Si los dos valen cero, la
   reserva del PCR fallo en silencio.

2. La linea de "arrancando" tambien lleva ahora r13, el PCR y el TLS. Esto es
   lo importante: esa linea sale SIEMPRE, tanto si el arranque va bien como si
   no. Asi se puede comparar directamente un arranque bueno con uno malo
   -misma linea, dos maquinas- en vez de mirar solo el que falla.

3. Si el PCR no es cero, se vuelcan las dos palabras del guest que estan en
   PCR+0x00 y PCR+0x100, que son justo las que el juego intenta leer.


LO QUE ANADE LA VERSION 3, Y NO ES DIAGNOSTICO SINO UN ARREGLO
==============================================================

Leyendo el log de una partida real aparecio esto:

    44.803 lineas en 44 segundos, TODAS la misma:
        [warning] [sys] Too few processor cores - scheduling will be wonky

El 100% del log. Mil avisos por segundo, 105 MB en un cuarto de hora.

Sale de XThread::SetActiveCpu, que el juego llama cada vez que crea un hilo o
le cambia la CPU, y el SDK lo escribia UNA VEZ POR LLAMADA.

Y no es solo ruido molesto. Cada linea es un formateo, un cerrojo y una
escritura a disco, hecha desde un hilo del juego. En un equipo de dos nucleos
-que es exactamente el unico caso en el que esa rama se ejecuta- eso le roba
la CPU a todo lo demas. El sintoma que lo destapo: el audio se cortaba a los
segundos de salir del taller y el juego se volvia un barrizal.

O sea que el aviso que decia "aqui la planificacion va a ir mal" era, el
mismo, una parte importante de por que iba mal.

Ahora sale una sola vez por ejecucion. El texto original se conserva entero
por si algo lo busca.
"""

import argparse
import os
import pathlib
import shutil
import sys

MARCA = "PARCHE LOCAL - diagnostico y ruido v3"

# Marcas de versiones anteriores. Si aparece alguna, se revierte antes de
# aplicar la nueva: reaplicar encima no encontraria los anclajes -ya estan
# reescritos- y el script se pararia diciendo que el SDK ha cambiado.
MARCAS_VIEJAS = [
    "PARCHE LOCAL - diagnostico del hilo que revienta v2",
    "PARCHE LOCAL - diagnostico del hilo que revienta",
]

# ---------------------------------------------------------------------------
#  1. src/system/xmemory.cpp
# ---------------------------------------------------------------------------

MEM_ANCLA_INC = """#include <rex/system/xmemory.h>
#include <rex/thread.h>
"""

MEM_NUEVO_INC = """#include <rex/system/xmemory.h>
#include <rex/system/xthread.h>  // PARCHE LOCAL - diagnostico y ruido v3
#include <rex/thread.h>
"""

MEM_ANCLA = """    REXSYS_ERROR(
        "Unhandled guest access violation: {} of guest 0x{:08X} (host 0x{:016X}) on thread 0x{:X}",
        is_write ? "write" : "read", virtual_address, reinterpret_cast<uintptr_t>(host_address),
        rex::thread::current_thread_id());
    return false;
"""

MEM_NUEVO = """    REXSYS_ERROR(
        "Unhandled guest access violation: {} of guest 0x{:08X} (host 0x{:016X}) on thread 0x{:X}",
        is_write ? "write" : "read", virtual_address, reinterpret_cast<uintptr_t>(host_address),
        rex::thread::current_thread_id());

    // ============ PARCHE LOCAL - diagnostico y ruido v3 ======
    //
    // El mensaje de arriba se deja TAL CUAL: tools\\\\matriz.ps1 lo busca por
    // texto para clasificar los intentos. Aqui solo se anade debajo quien ha
    // muerto y con que valores.
    //
    // Se llama a REXSYS_ERROR igual que arriba, asi que no se introduce
    // ninguna forma nueva de bloquearse: este camino ya estaba logueando.
    {
      // IsInThread() antes de GetCurrentThread(): el segundo dispara un
      // assert_always si no hay hilo del kernel enlazado, y aqui es un caso
      // perfectamente posible -y ademas informativo-.
      auto* hilo =
          rex::system::XThread::IsInThread() ? rex::system::XThread::GetCurrentThread() : nullptr;
      if (!hilo) {
        REXSYS_ERROR(
            "  [hilo guest] no hay XThread en este hilo: el fallo NO viene de "
            "codigo del juego, sino del propio runtime.");
      } else {
        const auto* cp = hilo->creation_params();
        REXSYS_ERROR(
            "  [hilo guest] id=0x{:X} entrada=0x{:08X} contexto=0x{:08X} "
            "trampolin_xapi=0x{:08X} principal={} creado_por_el_juego={}",
            hilo->thread_id(), cp->start_address, cp->start_context,
            cp->xapi_thread_startup, hilo->main_thread(), hilo->is_guest_thread());

        // Lo que el SDK CREE haber reservado para este hilo. Comparado con
        // r13 mas abajo, esto separa "la reserva fallo" de "el contexto se
        // perdio por el camino".
        REXSYS_ERROR("  [bloques del hilo] pcr=0x{:08X} tls=0x{:08X}", hilo->pcr_ptr(),
                     hilo->tls_ptr());

        auto* estado = hilo->thread_state();
        if (estado && estado->context()) {
          const auto& c = *estado->context();
          // r13 ES EL REGISTRO CLAVE: apunta al PCR, y ThreadState lo pone al
          // construirse. Las dos direcciones que revientan -0x00000000 y
          // 0x00000100- son exactamente los desplazamientos que el propio
          // xthread.cpp documenta dentro del PCR: el puntero al TLS y el
          // puntero al TEB. O sea que un r13 a cero explica el crash entero.
          //
          // lr = a donde volveria la funcion actual, o sea QUIEN llamo.
          // last_indirect_target lo mantiene el SDK aunque ctr se haya
          // optimizado a variable local (REX_CONFIG_CTR_AS_LOCAL).
          REXSYS_ERROR(
              "  [contexto ppc] r13=0x{:08X} r2=0x{:08X} lr=0x{:08X} "
              "ultimo_salto_indirecto=0x{:08X} r1=0x{:08X}",
              c.r13.u32, c.r2.u32, static_cast<uint32_t>(c.lr), c.last_indirect_target, c.r1.u32);
          REXSYS_ERROR(
              "  [registros] r3=0x{:08X} r4=0x{:08X} r5=0x{:08X} r6=0x{:08X} "
              "r7=0x{:08X} r11=0x{:08X} r12=0x{:08X} r30=0x{:08X} r31=0x{:08X}",
              c.r3.u32, c.r4.u32, c.r5.u32, c.r6.u32, c.r7.u32, c.r11.u32, c.r12.u32, c.r30.u32,
              c.r31.u32);
        }

        // Y si el PCR SI existe, que dicen las dos palabras que el juego
        // intenta leer. Si el PCR es valido y estan a cero, el problema es su
        // contenido; si r13 es cero, ni siquiera se llega a mirarlas.
        const uint32_t pcr = hilo->pcr_ptr();
        if (pcr) {
          auto* p0 = TranslateVirtual<const uint8_t*>(pcr);
          auto* p100 = TranslateVirtual<const uint8_t*>(pcr + 0x100);
          if (p0 && p100) {
            // Cualificado del todo: este fichero ya vive dentro de
            // namespace rex::memory, asi que sin cualificar tambien valdria,
            // pero escrito entero es el mismo nombre que usa xthread.cpp y no
            // depende de donde acabe cayendo el bloque si el SDK se reordena.
            REXSYS_ERROR("  [contenido del pcr] +0x000={:08X} +0x100={:08X}",
                         rex::memory::load_and_swap<uint32_t>(p0),
                         rex::memory::load_and_swap<uint32_t>(p100));
          }
        }
      }
    }
    // ======================= fin del parche local ==========================

    return false;
"""

# ---------------------------------------------------------------------------
#  2. src/system/xthread.cpp
# ---------------------------------------------------------------------------

RUIDO_ANCLA = """  } else {
    REXSYS_WARN("Too few processor cores - scheduling will be wonky");
  }
"""

RUIDO_NUEVO = """  } else {
    // PARCHE LOCAL - diagnostico y ruido v3
    //
    // Este aviso salia UNA VEZ POR LLAMADA, y SetActiveCpu se llama cada vez
    // que el juego crea un hilo o le cambia la CPU. Medido en una partida
    // real: 44.803 avisos en 44 segundos -unos mil por segundo-, y 105 MB de
    // log en un cuarto de hora. El 100% de las lineas del log eran esta.
    //
    // No es solo ruido. Cada linea es un formateo, un cerrojo y una escritura
    // a disco, hecha DESDE UN HILO DEL JUEGO. En un equipo de dos nucleos
    // -que es justo el caso en el que esta rama se ejecuta- eso le roba la
    // CPU al resto: el audio se corta y el juego se vuelve un barrizal.
    //
    // O sea que el aviso que dice "aqui va a ir mal" era, el mismo, una parte
    // importante de por que iba mal.
    //
    // Se deja una sola vez por proceso. El texto original se conserva entero
    // para no romper nada que lo busque.
    static std::atomic_flag avisado = ATOMIC_FLAG_INIT;
    if (!avisado.test_and_set(std::memory_order_relaxed)) {
      REXSYS_WARN("Too few processor cores - scheduling will be wonky"
                  " (este aviso solo se muestra una vez por ejecucion)");
    }
  }
"""

HILO_ANCLA = """  auto* dispatcher = runtime->function_dispatcher();
  auto* memory = runtime->memory();
  PPCFunc* func = dispatcher->GetFunction(address);
"""

HILO_NUEVO = """  auto* dispatcher = runtime->function_dispatcher();
  auto* memory = runtime->memory();

  // PARCHE LOCAL - diagnostico y ruido v3
  //
  // Una linea por hilo del guest que arranca. Los puntos de entrada de los
  // hilos son INVISIBLES para el analisis estatico -la direccion se pasa como
  // parametro a ExCreateThread, no aparece como destino de ningun salto-, asi
  // que sin esto no hay forma de saber cuantos hilos crea el juego, en que
  // orden ni cual es el que no vuelve.
  //
  // Y lleva r13, el PCR y el TLS a proposito: esta linea sale SIEMPRE, tanto
  // si el arranque va bien como si no. Es la unica forma de comparar un
  // arranque bueno con uno malo mirando exactamente lo mismo en las dos
  // maquinas, en vez de mirar solo la que falla.
  //
  // Nivel info y una sola linea por hilo: no cambia el timing de forma
  // apreciable, que es justo lo que hay que cuidar cuando se persigue algo
  // que solo pasa en maquinas rapidas.
  {
    auto* ctx_log = thread_state_ ? thread_state_->context() : nullptr;
    REXSYS_INFO(
        "[hilo guest] arrancando: entrada=0x{:08X} start_address=0x{:08X} "
        "contexto=0x{:08X} trampolin_xapi=0x{:08X} pila={} bytes | "
        "pcr=0x{:08X} tls=0x{:08X} r13=0x{:08X} r1=0x{:08X}",
        address, creation_params_.start_address, creation_params_.start_context,
        creation_params_.xapi_thread_startup, creation_params_.stack_size, pcr_address_,
        tls_static_address_, ctx_log ? ctx_log->r13.u32 : 0u, ctx_log ? ctx_log->r1.u32 : 0u);
  }

  PPCFunc* func = dispatcher->GetFunction(address);
"""


def localizar_sdk():
    raiz = pathlib.Path(__file__).resolve().parent.parent
    # NFSMW_SDK apunta a otro arbol del SDK (el de Android, por ejemplo). Si
    # esta puesta se usa SOLO esa ruta: caer en silencio en el SDK de Windows
    # parchearia el arbol equivocado.
    otro = os.environ.get("NFSMW_SDK")
    candidatos = [pathlib.Path(otro)] if otro else [raiz.parent / "rexglue-sdk", raiz / "sdk"]
    for cand in candidatos:
        if (cand / "src" / "system" / "xmemory.cpp").exists():
            return cand
    sys.exit("[ERROR] No encuentro el SDK (src/system/xmemory.cpp).\n"
             "        Se busca en ..\\rexglue-sdk y en .\\sdk")


def main():
    p = argparse.ArgumentParser(add_help=True)
    p.add_argument("--estado", action="store_true")
    p.add_argument("--revertir", action="store_true")
    args = p.parse_args()

    sdk = localizar_sdk()
    f_mem = sdk / "src" / "system" / "xmemory.cpp"
    f_hilo = sdk / "src" / "system" / "xthread.cpp"

    trabajos = [
        (f_mem, [("includes", MEM_ANCLA_INC, MEM_NUEVO_INC),
                 ("mensaje de violacion de acceso", MEM_ANCLA, MEM_NUEVO)]),
        (f_hilo, [("arranque de hilo del guest", HILO_ANCLA, HILO_NUEVO),
                  ("aviso de pocos nucleos", RUIDO_ANCLA, RUIDO_NUEVO)]),
    ]

    if args.estado:
        for f, _ in trabajos:
            t = f.read_text(encoding="utf-8")
            if MARCA in t:
                estado = "v2 APLICADO"
            elif any(m in t for m in MARCAS_VIEJAS):
                estado = "v1 aplicado (hace falta reaplicar para pasar a la v2)"
            else:
                estado = "sin aplicar"
            print(f"  {f.name:16s}  {estado}")
        return 0

    if args.revertir:
        for f, _ in trabajos:
            original = f.with_suffix(".cpp.original")
            if original.exists():
                shutil.copy2(original, f)
                print(f"[ok] Restaurado {f.name} desde .original")
            else:
                print(f"[aviso] No hay .original de {f.name}.")
        return 0

    # Si esta puesta una version anterior, se quita primero. Reaplicar encima
    # nunca encontraria los anclajes -ya estan reescritos- y el script se
    # pararia diciendo que el SDK ha cambiado, que es un mensaje enganoso.
    for f, _ in trabajos:
        t = f.read_text(encoding="utf-8")
        if MARCA not in t and any(m in t for m in MARCAS_VIEJAS):
            original = f.with_suffix(".cpp.original")
            if not original.exists():
                sys.exit(f"[ERROR] {f.name} tiene una version anterior del parche pero no\n"
                         f"        hay .original para deshacerla. No sigo: restaura ese\n"
                         f"        fichero desde el repositorio del SDK y vuelve a lanzarme.")
            shutil.copy2(original, f)
            print(f"[ok] Quitada la version anterior de {f.name}")

    # Comprobar TODOS los anclajes de TODOS los ficheros antes de escribir
    # nada. Si el SDK cambia de version y alguno no cuadra, es mucho peor
    # dejar un fichero parcheado y otro no que no parchear ninguno.
    planes = []
    for f, anclas in trabajos:
        txt = f.read_text(encoding="utf-8")
        if MARCA in txt:
            print(f"[ok] {f.name} ya estaba en la v2.")
            planes.append((f, txt, None))
            continue
        for nombre, ancla, _ in anclas:
            n = txt.count(ancla)
            if n != 1:
                sys.exit(f"[ERROR] En {f.name}, el anclaje '{nombre}' aparece {n} veces,\n"
                         f"        esperaba 1. El SDK habra cambiado. No he tocado nada.")
        planes.append((f, txt, anclas))

    if all(a is None for _, _, a in planes):
        print("[ok] Todo estaba ya aplicado. No toco nada.")
        return 0

    for f, txt, anclas in planes:
        if anclas is None:
            continue
        original = f.with_suffix(".cpp.original")
        if not original.exists():
            shutil.copy2(f, original)
            print(f"[ok] Copia de seguridad: {original.name}")
        for _, ancla, nuevo in anclas:
            txt = txt.replace(ancla, nuevo)
        f.write_text(txt, encoding="utf-8")
        print(f"[ok] Parcheado {f.name}")

    print()
    print("  HAY QUE RECOMPILAR EL SDK para que sirva de algo:")
    print("    cmake --build out/build/win-amd64 --config Release --target install")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
