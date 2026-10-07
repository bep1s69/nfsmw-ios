#!/usr/bin/env python3
"""
Deja de recompilar el pipeline de salida de la imagen en CADA fotograma.

    python tools/parche_pipeline.py            aplicar
    python tools/parche_pipeline.py --estado
    python tools/parche_pipeline.py --revertir

Toca un fichero del SDK:  src/ui/vulkan/vulkan_presenter.cpp

No guarda .original: aplica y deshace por sustitucion de texto exacta.


EL FALLO
========

Encontrado perfilando el juego en un Snapdragon 8 Elite con simpleperf: en el
menu, el 84 % del hilo de la interfaz se iba aqui

    VulkanPresenter::PaintAndPresentImpl
      -> CreateGuestOutputPaintPipeline
        -> vkCreateGraphicsPipelines          (libllvm-qgl.so, el compilador
                                               de shaders de Qualcomm)

es decir, compilando shaders una y otra vez, a 11 fps.

El presentador guarda el pipeline que pinta la imagen del juego en la pantalla,
y lo rehace solo si ha cambiado el formato del swapchain:

    if (swapchain_effect_pipeline.swapchain_pipeline != VK_NULL_HANDLE &&
        swapchain_effect_pipeline.swapchain_format !=
            paint_context_.swapchain_render_pass_format) {
      AwaitSubmissionCompletion(...);      // espera a la GPU
      vkDestroyPipeline(...);
    }
    if (swapchain_effect_pipeline.swapchain_pipeline == VK_NULL_HANDLE) {
      ... = CreateGuestOutputPaintPipeline(...);
    }

Pero swapchain_format NO SE ASIGNA NUNCA. Se declara a VK_FORMAT_UNDEFINED en
include/rex/ui/vulkan/presenter.h, se compara, y ahi se queda. Asi que la
comparacion da "distinto" en todos los fotogramas y cada uno:

  1. espera a que la GPU termine el fotograma anterior (CPU y GPU dejan de
     trabajar en paralelo),
  2. destruye el pipeline,
  3. lo vuelve a compilar desde cero.

En escritorio pasa igual, pero NVIDIA y AMD tienen cache interna de pipelines y
el paso 3 sale casi gratis; el 1 sigue costando. En Qualcomm, el 3 es un
compilador LLVM entero en cada fotograma.

El arreglo es una linea: apuntar el formato con el que se ha creado.
"""

import argparse
import os
import pathlib
import sys


ANCLA = '''            swapchain_effect_pipeline.swapchain_pipeline = CreateGuestOutputPaintPipeline(
                swapchain_effect, paint_context_.swapchain_render_pass);
            if (swapchain_effect_pipeline.swapchain_pipeline == VK_NULL_HANDLE) {
              guest_output_flow.effect_count = 0;
            }
'''

NUEVO = '''            swapchain_effect_pipeline.swapchain_pipeline = CreateGuestOutputPaintPipeline(
                swapchain_effect, paint_context_.swapchain_render_pass);
            if (swapchain_effect_pipeline.swapchain_pipeline == VK_NULL_HANDLE) {
              guest_output_flow.effect_count = 0;
            } else {
              // PARCHE LOCAL - pipeline: apuntar el formato con el que se ha
              // creado. Sin esto swapchain_format se queda en UNDEFINED, la
              // comparacion de arriba da "distinto" en todos los fotogramas y
              // cada uno espera a la GPU, destruye el pipeline y lo recompila.
              swapchain_effect_pipeline.swapchain_format =
                  paint_context_.swapchain_render_pass_format;
            }
'''

FICHERO = "src/ui/vulkan/vulkan_presenter.cpp"


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
        print(f"  pipeline                   {'aplicado' if NUEVO in txt else 'sin aplicar'}")
        return 0

    if args.revertir:
        if NUEVO not in txt:
            print("[ok] pipeline: no habia nada puesto")
            return 0
        escribir(f, txt.replace(NUEVO, ANCLA), eol)
        print("[ok] Quitado")
        return 0

    if NUEVO in txt:
        print("[ok] pipeline: ya estaba")
        return 0
    n = txt.count(ANCLA)
    if n != 1:
        sys.exit(f"[ERROR] El anclaje aparece {n} veces en {FICHERO}, esperaba 1.\n"
                 "        El SDK habra cambiado. No he tocado nada.")
    escribir(f, txt.replace(ANCLA, NUEVO), eol)
    print("[ok] Aplicado: apuntar el formato del pipeline de salida")
    return 0


if __name__ == "__main__":
    sys.exit(main())
