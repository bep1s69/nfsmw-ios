#!/usr/bin/env python3
"""
Desatasca la voz XMA cuando el juego se queda girando sobre ella.

    python tools/parche_desatasco.py            aplicar
    python tools/parche_desatasco.py --estado
    python tools/parche_desatasco.py --revertir

Toca un fichero del SDK:  src/kernel/xboxkrnl/xboxkrnl_audio_xma.cpp
Va DESPUES de tools/parche_anillo.py, sobre ese mismo fichero.

AVISO POR DELANTE: esto es un APANO, no la cura. Rompe el atasco desde fuera
en vez de evitar que ocurra. Lo digo aqui para que quede escrito.


LO QUE YA ESTA MEDIDO, SIN HUECOS
=================================

Todo el audio del juego lo lleva UN SOLO hilo, el 0xD. El mismo alimenta al
descodificador, consume lo descodificado y mezcla. Esto es el final, con el
detalle al milisegundo:

  01.528  el juego le da entrada a la voz 19
  01.679  entra en el bucle de mezcla (sub_825E1CD0) para esa voz
  01.679  Work produce, escritura 0 -> 4
  01.700  Work produce, escritura 4 -> 8
  01.709  Work produce, escritura 8 -> 12
  01.728  Work NO PRODUCE NADA.  ent0=0 ent1=0.  Se acabo la entrada.
  01.739  ...
  01.782  ...  y el juego, mientras, mueve su lectura 16, 20, 0, 4, 8: una
               vuelta entera al anillo consumiendo lo que ya nadie rellena.
               Al volver a 8 se para.
  02.119  a partir de aqui, 90 segundos leyendo los dos offsets y nada mas.

Y en ese mismo tramo el juego SI le da entrada a las voces vecinas -6500 y
6540- a las 01.549, 01.608, 01.658, 01.698, 01.759 y 01.779. A la voz 19 no le
da ninguna. No es que se le olvide: para llegar a alimentarla tendria que
salir del bucle de mezcla, y de ahi ya no sale.


POR QUE NO SALE
===============

El bucle, leido instruccion a instruccion:

  - si una voz esta mal servida, pone una bandera y NO pasa a la siguiente:
    repite esa misma voz sin parar
  - para saber cuanto audio hay, resta:  escritura*256 - su cursor
  - si esa resta da CERO, y solo entonces, pregunta si el buffer de salida
    sigue valido. Si le dicen que no, lo entiende como "buffer completo" y se
    lleva los 6144 bytes de golpe. Esa es su salida de emergencia.

En el atasco la resta da unos 1000, no cero: la lectura del juego se queda a
UN BLOQUE de alcanzar a la escritura. Asi que nunca llega a preguntar, y su
salida de emergencia no se dispara. Espera audio que solo podria producir un
descodificador que no tiene con que, alimentado por el mismo hilo que espera.


QUE HACE ESTE PARCHE
====================

Vigila esa situacion exacta, en la propia funcion que el juego consulta en
bucle. Cuando lleva mas de 250 ms cumpliendose TODO esto a la vez:

  - el juego pide el offset de escritura del mismo contexto una y otra vez
  - ese contexto tiene la salida marcada como valida
  - sus dos buffers de entrada estan vacios, o sea que el descodificador no
    tiene absolutamente nada que producir
  - y escritura y lectura no coinciden, que es lo que impide que el juego
    llegue a hacer su pregunta

entonces le da la senal que su propio codigo sabe interpretar: iguala la
escritura a la lectura y apaga output_buffer_valid. Es decir, "este buffer
esta terminado". El juego hace su resta, le da cero o negativo, pregunta, se
entera, se lleva lo que queda y sigue.

Los 250 ms son de sobra: en marcha normal esas consultas se resuelven en
microsegundos. La condicion no se cumple jugando bien.

El precio es un tropiezo de audio en esa voz, porque parte de lo que se lleva
es material viejo del anillo. A cambio de no colgarse.


POR QUE ES UN APANO Y NO LA CURA
================================

La cura seria que el descodificador no se quedara nunca seco a media mezcla, y
eso pasa por entender por que el juego llega tan justo de entrada. Sospecho
del ritmo: en esta maquina, a 18 fps y con el log a tope, el hilo de audio
llega tarde a rellenar. Pero sospechar no es saberlo, y no lo voy a vender
como que lo se.

Lo que si se puede decir es que ataca una situacion IMPOSIBLE de alcanzar
jugando bien -un hilo girando un cuarto de segundo sobre una voz sin entrada-
y que si se dispara deja un aviso en el log. Si aparece a menudo, el problema
de ritmo es gordo y hay que ir a por el. Si no aparece nunca y el juego deja
de colgarse, era esto.
"""

import argparse
import os
import pathlib
import sys

MARCA = "PARCHE LOCAL - desatasco de la voz XMA"

ANCLA = """u32 XMAGetOutputBufferWriteOffset_entry(mapped_void context_ptr) {
  XMA_CONTEXT_DATA context(context_ptr);
"""

NUEVO = """u32 XMAGetOutputBufferWriteOffset_entry(mapped_void context_ptr) {
  XMA_CONTEXT_DATA context(context_ptr);

  // PARCHE LOCAL - desatasco de la voz XMA
  //
  // Aqui es donde el juego se queda girando cuando se cuelga: pide este
  // offset, pide el de lectura, y vuelta a empezar, para siempre.
  //
  // Se vigila un solo contexto a la vez, el ultimo que haya preguntado. No
  // hace falta mas: cuando se atasca pregunta por uno y solo por uno, asi que
  // dos enteros atomicos bastan y esto no cuesta nada en el camino normal,
  // que es lo que importa estando en un bucle tan caliente.
  {
    const uint32_t direccion = context_ptr.guest_address();
    static std::atomic<uint32_t> vigilado{0};
    static std::atomic<int64_t> desde{0};

    const int64_t ahora = std::chrono::duration_cast<std::chrono::milliseconds>(
                              std::chrono::steady_clock::now().time_since_epoch())
                              .count();

    if (vigilado.load(std::memory_order_relaxed) != direccion) {
      vigilado.store(direccion, std::memory_order_relaxed);
      desde.store(ahora, std::memory_order_relaxed);
    } else {
      const int64_t llevo = ahora - desde.load(std::memory_order_relaxed);

      // La foto exacta del atasco, y nada mas que esa:
      //   salida valida  +  las dos entradas vacias  +  offsets distintos.
      // Con las entradas vacias el descodificador no puede producir ni una
      // muestra por mucho que se le insista, asi que esperar no arregla nada.
      // Y con los offsets distintos el juego nunca llega a preguntar si el
      // buffer sigue valido, que es su unica salida.
      const bool atascado = llevo > 250 && context.output_buffer_valid &&
                            !context.input_buffer_0_valid && !context.input_buffer_1_valid &&
                            context.output_buffer_write_offset != context.output_buffer_read_offset;

      if (atascado) {
        REXAPU_WARN(
            "[desatasco] ctx={:08X} lleva {} ms girando sin entrada "
            "(escritura={} lectura={}). Le digo que el buffer esta terminado.",
            direccion, llevo, uint32_t(context.output_buffer_write_offset),
            uint32_t(context.output_buffer_read_offset));

        // Igualar los dos offsets hace que la resta del juego de cero o
        // negativo, que es lo que le empuja a preguntar; y apagar la validez
        // es la respuesta que su codigo entiende como "buffer completo".
        context.output_buffer_write_offset = context.output_buffer_read_offset;
        context.output_buffer_valid = 0;
        context.Store(context_ptr);

        // El reloj se reinicia para no repetirlo en la vuelta siguiente si el
        // juego tardara un poco en reaccionar.
        desde.store(ahora, std::memory_order_relaxed);
        return context.output_buffer_write_offset;
      }
    }
  }
"""


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

    if args.estado:
        puesto = MARCA in f.read_text(encoding="utf-8")
        print(f"  {f.name:30s} desatasco {'aplicado' if puesto else 'sin aplicar'}")
        return 0

    if args.revertir:
        # La copia de seguridad de este fichero la hace parche_anillo.py, que es
        # quien lo toca primero. Restaurarla aqui se llevaria por delante su
        # instrumentacion, asi que se manda al que corresponde.
        print("  Este parche va encima de parche_anillo.py y comparte con el la")
        print("  copia de seguridad, asi que se deshace desde alli:")
        print(r"    py -3 tools\parche_anillo.py --revertir")
        print()
        print("  Y si quieres la instrumentacion pero sin el desatasco, ejecuta")
        print(r"  despues tools\parche_anillo.py otra vez.")
        return 0

    txt = f.read_text(encoding="utf-8")
    if MARCA in txt:
        print(f"[ok] {f.name}: el desatasco ya estaba puesto")
        return 0

    # Este parche usa std::atomic y std::chrono, y quien mete esas dos
    # cabeceras en el fichero es parche_anillo.py. Sin el, esto compilaria mal
    # y el error saldria a mitad de la build del SDK, que es el peor sitio
    # posible para enterarse. Mejor pararlo aqui.
    if "PARCHE LOCAL - escucha de la conversacion XMA" not in txt:
        sys.exit("[ERROR] Falta parche_anillo.py, que es quien pone las cabeceras\n"
                 "        que este necesita. Ejecutalo antes:\n"
                 "            py -3 tools\\parche_anillo.py\n"
                 "        No he tocado nada.")

    n = txt.count(ANCLA)
    if n != 1:
        sys.exit(f"[ERROR] El anclaje aparece {n} veces, esperaba 1.\n"
                 f"        Ejecuta antes tools\\parche_anillo.py. No he tocado nada.")

    f.write_text(txt.replace(ANCLA, NUEVO), encoding="utf-8")
    print(f"[ok] Desatasco puesto en {f.name}")
    print()
    print("  Si salta, dejara un aviso [desatasco] en el log.")
    print()
    print("  HAY QUE RECOMPILAR EL SDK para que sirva de algo:")
    print("    cmake --build out/build/win-amd64 --config Release --target install")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
