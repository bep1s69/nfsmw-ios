#!/usr/bin/env python3
"""
Anade dos ajustes de MSAA: pintar con una muestra aunque el juego pida cuatro
("sin MSAA"), o con dos.

    python tools/parche_msaa.py            aplicar
    python tools/parche_msaa.py --estado
    python tools/parche_msaa.py --revertir

Toca un fichero del SDK:  src/graphics/command_processor.cpp
No guarda .original: aplica y deshace por sustitucion de texto exacta.


POR QUE
=======

Medido en el movil (Adreno 830), en el menu 3D:

    con MSAA 4x   46,2 fps
    sin MSAA      59,7 fps   <- el tope de 60

El juego pide MSAA 4x. En la Xbox 360 eso se pintaba en la EDRAM, 10 MB de
memoria dedicada con ancho de banda de sobra. Aqui cada pase de render tiene
que mover las cuatro muestras de color y profundidad -1280x512 por cuatro, dos
adjuntos: unos 42 MB por pase- entre la GPU y la memoria del movil, y hay una
decena de pases por fotograma. Con el perfil de GPU por pases medido, la mitad
del tiempo de GPU del menu se iba ahi.

A 2688x1216 de pantalla, en un movil, el MSAA 4x de una imagen de 1280x720 se
nota poco; los 14 fps se notan mucho.


COMO
====

RB_SURFACE_INFO es el registro donde el juego declara el formato de la
superficie, con las muestras en los bits 16-17 (0 = 1x, 1 = 2x, 2 = 4x). Segun
entra ese registro en el procesador de comandos se le recortan a lo pedido. De
ahi en adelante todo -objetivos de render, pipelines, volcados de EDRAM y
resolves- ve esas muestras y es coherente entre si. Con menos muestras la
superficie ocupa menos EDRAM, asi que las direcciones que el juego calculo para
4x siguen sin solaparse.

El juego NO se entera: sigue troceando la pantalla en tres franjas, porque esa
decision la toma su propio codigo. O sea que esto ahorra trabajo de GPU, no de
CPU. Quitar tambien el troceado pide parchear el juego, no el emulador.

Cvars:
  gpu_sin_msaa       una sola muestra. Apagado por defecto.
  gpu_msaa_muestras  tope de muestras: 1, 2 o 4 (por defecto 4, lo del juego).
                     gpu_sin_msaa manda sobre este.
"""

import argparse
import os
import pathlib
import sys


FICHERO = "src/graphics/command_processor.cpp"

BLOQUES = [
    (
        '''namespace rex::graphics {
''',
        '''// PARCHE LOCAL - sin MSAA (tools/parche_msaa.py).
REXCVAR_DEFINE_BOOL(gpu_sin_msaa, false, "GPU",
                    "Pintar con una sola muestra aunque el juego pida MSAA: mucho menos trabajo "
                    "de GPU, a cambio de bordes con mas dientes de sierra");
REXCVAR_DEFINE_INT32(gpu_msaa_muestras, 4, "GPU",
                     "Tope de muestras de MSAA: 1, 2 o 4. El juego pide 4; con 2 cuesta la mitad. "
                     "gpu_sin_msaa manda sobre este");

namespace rex::graphics {
''',
    ),
    (
        '''  // Volatile for the WAIT_REG_MEM loop.
  const_cast<volatile uint32_t&>(regs.values[index]) = value;
''',
        '''  // PARCHE LOCAL - MSAA a la carta: al emulador se le dicen como mucho las
  // muestras pedidas; el juego sigue creyendo que pinta con MSAA 4x
  // (tools/parche_msaa.py). Bits 16-17: 0 = 1x, 1 = 2x, 2 = 4x.
  if (index == XE_GPU_REG_RB_SURFACE_INFO) {
    const int32_t muestras = REXCVAR_GET(gpu_sin_msaa) ? 1 : REXCVAR_GET(gpu_msaa_muestras);
    const uint32_t tope = muestras >= 4 ? 2u : muestras >= 2 ? 1u : 0u;
    if (((value >> 16) & 3u) > tope) {
      value = (value & ~(UINT32_C(3) << 16)) | (tope << 16);
    }
  }

  // Volatile for the WAIT_REG_MEM loop.
  const_cast<volatile uint32_t&>(regs.values[index]) = value;
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
        estado = ("aplicado" if puestos == len(BLOQUES) else "sin aplicar" if puestos == 0
                  else f"A MEDIAS ({puestos}/{len(BLOQUES)})")
        print(f"  msaa                       {estado}")
        return 0

    if args.revertir:
        if puestos == 0:
            print("[ok] msaa: no habia nada puesto")
            return 0
        for ancla, nuevo in BLOQUES:
            txt = txt.replace(nuevo, ancla)
        escribir(f, txt, eol)
        print(f"[ok] Quitados {puestos} bloques")
        return 0

    if puestos == len(BLOQUES):
        print("[ok] msaa: ya estaba")
        return 0
    if puestos:
        sys.exit(f"[ERROR] msaa esta a medias ({puestos}/{len(BLOQUES)}). "
                 "Revierte primero con --revertir.")
    for ancla, _ in BLOQUES:
        n = txt.count(ancla)
        if n != 1:
            sys.exit(f"[ERROR] Un anclaje aparece {n} veces en {FICHERO}, esperaba 1:\n"
                     f"        {ancla.splitlines()[0].strip()}\n"
                     "        El SDK habra cambiado. No he tocado nada.")
    for ancla, nuevo in BLOQUES:
        txt = txt.replace(ancla, nuevo, 1)
    escribir(f, txt, eol)
    print("[ok] Aplicado: ajustes gpu_sin_msaa y gpu_msaa_muestras disponibles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
