#!/usr/bin/env python3
"""
Escribe en el log que camino de emulacion de EDRAM se acabo usando.

    python tools/parche_camino_edram.py            aplicar
    python tools/parche_camino_edram.py --estado
    python tools/parche_camino_edram.py --revertir

Toca un fichero del SDK:  src/graphics/vulkan/render_target_cache.cpp
No guarda .original: aplica y deshace por sustitucion de texto exacta.


PARA QUE
========

El cvar render_target_path_vulkan acepta [any, fbo, fsi]:

  fbo  objetivos de render del anfitrion, con transferencias de propiedad
  fsi  la EDRAM emulada dentro del shader de pixel (fragment shader interlock)

Pedir "fsi" en una GPU sin la extension NO da error: el SDK vuelve solo a
"fbo" en silencio. O sea que sin esta linea no hay forma de saber si el ajuste
sirvio de algo, y se acaba midiendo lo mismo dos veces creyendo que son cosas
distintas.


EXPECTATIVAS, PARA NO ENGANARSE
===============================

Medido el 2026-09-21 cronometrando las fases de IssueDraw: la emulacion de
EDRAM (render_target_cache_->Update) cuesta ~1,2 ms de los ~68 ms del
fotograma, un 2 %. El camino "fsi" puede ir mejor o peor, pero no es donde esta
el problema de fluidez: eso es el numero de dibujos.
"""

import argparse
import os
import pathlib
import sys


FICHERO = "src/graphics/vulkan/render_target_cache.cpp"

ANCLA = """    if (!fsi_path_supported) {
      path_ = Path::kHostRenderTargets;
    }
  }
"""

NUEVO = """    if (!fsi_path_supported) {
      path_ = Path::kHostRenderTargets;
    }
  }

  // PARCHE LOCAL - camino de EDRAM (tools/parche_camino_edram.py): decirlo en
  // el log. Pedir "fsi" sin la extension cae a "fbo" en silencio, y sin esta
  // linea se acaba midiendo lo mismo dos veces creyendo que son cosas distintas.
  REXGPU_INFO("[edram] camino {} (pedido '{}', fsi {} por la GPU)",
              path_ == Path::kPixelShaderInterlock ? "shader de pixel (fsi)"
                                                   : "objetivos del anfitrion (fbo)",
              REXCVAR_GET(render_target_path_vulkan),
              fsi_path_supported ? "soportado" : "NO soportado");
"""


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
    puesto = NUEVO in txt

    if args.estado:
        print(f"  camino_edram               {'aplicado' if puesto else 'sin aplicar'}")
        return 0

    if args.revertir:
        if not puesto:
            print("[ok] camino_edram: no habia nada puesto")
            return 0
        escribir(f, txt.replace(NUEVO, ANCLA), eol)
        print("[ok] Quitado")
        return 0

    if puesto:
        print("[ok] camino_edram: ya estaba")
        return 0
    n = txt.count(ANCLA)
    if n != 1:
        sys.exit(f"[ERROR] El anclaje aparece {n} veces en {FICHERO}, esperaba 1. "
                 "No he tocado nada.")
    escribir(f, txt.replace(ANCLA, NUEVO, 1), eol)
    print("[ok] Aplicado: linea [edram] con el camino elegido")
    return 0


if __name__ == "__main__":
    sys.exit(main())
