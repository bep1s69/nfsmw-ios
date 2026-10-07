#!/usr/bin/env python3
"""
Hace que las esperas multiples de POSIX duerman de verdad.

    python tools/parche_esperas.py            aplicar
    python tools/parche_esperas.py --estado
    python tools/parche_esperas.py --revertir

Toca un fichero del SDK:  src/core/threading_posix.cpp

No guarda .original: aplica y deshace por sustitucion de texto exacta.


EL FALLO
========

En el movil el hilo "Audio Worker" se comia un nucleo entero, al 96-107 %, y
simpleperf lo pillaba en PosixConditionBase::WaitMultiple haciendo try_lock y
unlock sin parar. Ese hilo espera a cualquiera de ~65 semaforos (WaitAny) de
forma "alertable", para poder atender llamadas asincronas del guest.

En POSIX esa espera no duerme en una variable de condicion: sondea. La espera
alertable parte el tiempo en rodajas de 1 ms, y dentro de cada rodaja el bucle
hace:

    auto remaining = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - now);
    auto sleep_time = std::min(remaining, std::chrono::milliseconds(1));
    std::this_thread::sleep_for(sleep_time);

El resto se pasa a MILISEGUNDOS ENTEROS. Tras la primera vuelta quedan, por
ejemplo, 0,7 ms, que truncados son 0: sleep_for(0) no duerme, y el bucle gira
en vacio hasta agotar la rodaja. Rodaja tras rodaja. El hilo NUNCA duerme.

Afecta a toda espera multiple con tiempo limite, no solo al audio: tambien a
las del juego (KeWaitForMultipleObjects).


EL ARREGLO
==========

Calcular lo que queda con la resolucion del reloj, no en milisegundos. Asi se
duerme lo que falta de la rodaja -0,7 ms- y la comprobacion vuelve una vez por
milisegundo como estaba pensado, en vez de miles de veces.
"""

import argparse
import os
import pathlib
import sys


ANCLA = '''      if (timeout == std::chrono::milliseconds::max()) {
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
      } else {
        auto remaining = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - now);
        auto sleep_time = std::min(remaining, std::chrono::milliseconds(1));
        std::this_thread::sleep_for(sleep_time);
      }
'''

NUEVO = '''      if (timeout == std::chrono::milliseconds::max()) {
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
      } else {
        // PARCHE LOCAL - esperas: lo que queda, con la resolucion del reloj.
        // Pasado a milisegundos enteros, 0,7 ms se volvia 0, sleep_for(0) no
        // dormia y el hilo giraba en vacio hasta agotar la rodaja: el trabajador
        // de audio se comia un nucleo entero sin hacer nada.
        const std::chrono::steady_clock::duration remaining = end_time - now;
        const std::chrono::steady_clock::duration rodaja = std::chrono::milliseconds(1);
        std::this_thread::sleep_for(std::min(remaining, rodaja));
      }
'''

FICHERO = "src/core/threading_posix.cpp"


def localizar_sdk():
    raiz = pathlib.Path(__file__).resolve().parent.parent
    # NFSMW_SDK apunta a otro arbol del SDK (el de Android, por ejemplo). Si
    # esta puesta se usa SOLO esa ruta: caer en silencio en el SDK de Windows
    # parchearia el arbol equivocado.
    otro = os.environ.get("NFSMW_SDK")
    candidatos = [pathlib.Path(otro)] if otro else [raiz.parent / "rexglue-sdk", raiz / "sdk"]
    for cand in candidatos:
        if (cand / FICHERO).exists():
            return cand
    sys.exit(f"[ERROR] No encuentro {FICHERO} del SDK.\n"
             "        Se busca en NFSMW_SDK, o en ..\\rexglue-sdk y .\\sdk")


def leer(f):
    with open(f, encoding="utf-8", newline="") as h:
        txt = h.read()
    eol = "\r\n" if "\r\n" in txt else "\n"
    return txt.replace("\r\n", "\n"), eol


def escribir(f, txt, eol):
    with open(f, "w", encoding="utf-8", newline="") as h:
        h.write(txt.replace("\n", eol))


def main():
    p = argparse.ArgumentParser(add_help=True)
    p.add_argument("--estado", action="store_true")
    p.add_argument("--revertir", action="store_true")
    args = p.parse_args()

    f = localizar_sdk() / FICHERO
    txt, eol = leer(f)

    if args.estado:
        print(f"  esperas                    {'aplicado' if NUEVO in txt else 'sin aplicar'}")
        return 0

    if args.revertir:
        if NUEVO not in txt:
            print("[ok] esperas: no habia nada puesto")
            return 0
        escribir(f, txt.replace(NUEVO, ANCLA), eol)
        print("[ok] Quitado")
        return 0

    if NUEVO in txt:
        print("[ok] esperas: ya estaba")
        return 0
    n = txt.count(ANCLA)
    if n != 1:
        sys.exit(f"[ERROR] El anclaje aparece {n} veces en {FICHERO}, esperaba 1.\n"
                 "        El SDK habra cambiado. No he tocado nada.")
    escribir(f, txt.replace(ANCLA, NUEVO), eol)
    print("[ok] Aplicado: las esperas multiples duermen lo que falta de la rodaja")
    return 0


if __name__ == "__main__":
    sys.exit(main())
