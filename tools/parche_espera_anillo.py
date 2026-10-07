#!/usr/bin/env python3
"""
Avisa cuando el procesador de comandos publica su puntero de lectura.

    python tools/parche_espera_anillo.py            aplicar
    python tools/parche_espera_anillo.py --estado
    python tools/parche_espera_anillo.py --revertir

Toca un fichero del SDK:  src/graphics/command_processor.cpp
Es la mitad del arreglo; la otra es android/app/src/main/cpp/ganchos.cpp.
No guarda .original: aplica y deshace por sustitucion de texto exacta.


EL FALLO
========

Cuando el anillo de comandos de la GPU se llena, el D3D del juego espera a que
el procesador de comandos (CP) avance. Lo hace girando: relee el puntero de
lectura que el CP copia en memoria, sin parar, y en cada vuelta llama a un
vigilante de cuelgues (sub_825A5D18).

En el movil el CP es el cuello de botella y solo publica ese puntero al acabar
cada tramo del anillo, dos veces por fotograma. Asi que el hilo de render del
juego se pasaba el fotograma entero al 100 % en un nucleo prime. simpleperf:
el 86 % de los ciclos de toda la app, en ese bucle. Tras un rato el movil
llegaba a estrangulamiento termico severo (Thermal Status 3, CPU a 90 grados,
nucleos capados a 2,4 y 2,8 GHz), que frena a todo lo demas, CP incluido.


EL ARREGLO
==========

Aqui, un contador que el CP incrementa justo despues de escribir el puntero,
seguido de FUTEX_WAKE:

    extern "C" std::atomic<uint32_t> nfsmw_cp_rptr_seq;   (visible con dlsym)

En ganchos.cpp, sub_825A5D18 sustituida: si el puntero no se ha movido, duerme
en un futex sobre ese contador (tope 1 ms) en vez de volver a girar. El juego
se entera del avance en el mismo instante que antes, sin quemar un nucleo.

FUTEX_WAKE es una llamada al sistema por publicacion: dos por fotograma.
"""

import argparse
import os
import pathlib
import sys


FICHERO = "src/graphics/command_processor.cpp"

BLOQUES = [
    (
        '''#include <rex/math.h>
''',
        '''#include <rex/math.h>

// PARCHE LOCAL - espera del anillo: ver tools/parche_espera_anillo.py.
#include <atomic>
#include <climits>
#if defined(__linux__)
#include <linux/futex.h>
#include <sys/syscall.h>
#include <unistd.h>
#endif
extern "C" __attribute__((visibility("default"))) std::atomic<uint32_t> nfsmw_cp_rptr_seq{0};
''',
    ),
    (
        '''    // FIXME: We're supposed to process the WAIT_UNTIL register at this point,
''',
        '''    // PARCHE LOCAL - espera del anillo: avisar a quien espere espacio en el
    // anillo (ganchos.cpp, sub_825A5D18) de que el puntero de lectura ha
    // cambiado.
    nfsmw_cp_rptr_seq.fetch_add(1, std::memory_order_release);
#if defined(__linux__)
    syscall(SYS_futex, &nfsmw_cp_rptr_seq, FUTEX_WAKE_PRIVATE, INT_MAX, nullptr, nullptr, 0);
#endif

    // FIXME: We're supposed to process the WAIT_UNTIL register at this point,
''',
    ),
]


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
    puestos = sum(1 for _, nuevo in BLOQUES if nuevo in txt)

    if args.estado:
        estado = ("aplicado" if puestos == len(BLOQUES)
                  else "sin aplicar" if puestos == 0
                  else f"a medias ({puestos}/{len(BLOQUES)})")
        print(f"  espera del anillo          {estado}")
        return 0

    if args.revertir:
        for ancla, nuevo in BLOQUES:
            txt = txt.replace(nuevo, ancla)
        escribir(f, txt, eol)
        print(f"[ok] Quitados {puestos} bloques")
        return 0

    for ancla, nuevo in BLOQUES:
        if nuevo not in txt and txt.count(ancla) != 1:
            sys.exit(f"[ERROR] Un anclaje no aparece exactamente una vez en {FICHERO}.\n"
                     "        El SDK habra cambiado. No he tocado nada.")
    for ancla, nuevo in BLOQUES:
        if nuevo not in txt:
            txt = txt.replace(ancla, nuevo)
    escribir(f, txt, eol)
    print("[ok] Aplicado: el CP avisa al publicar su puntero de lectura")
    return 0


if __name__ == "__main__":
    sys.exit(main())
