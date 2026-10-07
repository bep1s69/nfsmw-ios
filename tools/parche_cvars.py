#!/usr/bin/env python3
"""
Que los ajustes de un plugin sobrevivan a que el plugin se cargue dos veces.

    python tools/parche_cvars.py            aplicar
    python tools/parche_cvars.py --estado
    python tools/parche_cvars.py --revertir

Toca un fichero del SDK:  src/core/cvar.cpp
No guarda .original: aplica y deshace por sustitucion de texto exacta.


EL FALLO
========

Los cvars del plugin de GPU (librexgpu-xenos.so) se registran cuando se carga
el plugin, despues de leer la linea de comandos. Para eso cvar::Init guarda los
--nombre=valor que aun no conoce como "pendientes", y al registrarse el cvar se
aplica su pendiente y se borra.

Pero el plugin se carga DOS veces: gpu_backend vale d3d12 por defecto, el
plugin no lo tiene en Android, se descarga y se carga otra vez para Vulkan. La
primera carga consumia los pendientes; al descargarse, sus cvars se
desregistraban y el valor se perdia; en la segunda, la que se usa, cada cvar
volvia a su valor por defecto. Medido (con un registro temporal):

    cvar tardio occlusion_query_enable = false -> aplicado      (1a carga)
    cvar tardio occlusion_query_enable SIN pendiente            (2a carga)

Asi que --occlusion_query_enable=false, --readback_memexport=false,
--clear_memory_page_state=false, --anisotropic_override=0,
--resolution_scale=2, --readback_resolve=none... no hacian nada. Ni desde la
pantalla de ajustes de la app.


EL ARREGLO
==========

Al desregistrar un cvar que venia de la linea de comandos o del fichero de
configuracion, su valor vuelve a los pendientes. Si el plugin se carga otra
vez, lo recupera. (La app, ademas, pasa --gpu_backend=vulkan y el plugin se
carga una sola vez.)
"""

import argparse
import os
import pathlib
import sys


FICHERO = "src/core/cvar.cpp"

ANCLA = '''  size_t pos = idx_it->second;
  index.erase(idx_it);
  storage.erase(storage.begin() + pos);
'''

NUEVO = '''  size_t pos = idx_it->second;
  // PARCHE LOCAL - cvars: si el valor vino de la linea de comandos o de la
  // configuracion, que vuelva a pendientes. Un plugin que se descarga y se
  // vuelve a cargar (el de GPU, al caer de d3d12 a vulkan) lo recupera.
  {
    const FlagEntry& saliente = storage[pos];
    if (saliente.source == Source::kCommandLine) {
      GetPendingValuesStorage()[key].cmdline = saliente.getter();
    } else if (saliente.source == Source::kConfig) {
      GetPendingValuesStorage()[key].config = saliente.getter();
    }
  }
  index.erase(idx_it);
  storage.erase(storage.begin() + pos);
'''


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
        print(f"  cvars                      {'aplicado' if NUEVO in txt else 'sin aplicar'}")
        return 0

    if args.revertir:
        if NUEVO not in txt:
            print("[ok] cvars: no habia nada puesto")
            return 0
        escribir(f, txt.replace(NUEVO, ANCLA), eol)
        print("[ok] Quitado")
        return 0

    if NUEVO in txt:
        print("[ok] cvars: ya estaba")
        return 0
    n = txt.count(ANCLA)
    if n != 1:
        sys.exit(f"[ERROR] El anclaje aparece {n} veces en {FICHERO}, esperaba 1.\n"
                 "        El SDK habra cambiado. No he tocado nada.")
    escribir(f, txt.replace(ANCLA, NUEVO), eol)
    print("[ok] Aplicado: los cvars de un plugin recargado conservan su valor")
    return 0


if __name__ == "__main__":
    sys.exit(main())
