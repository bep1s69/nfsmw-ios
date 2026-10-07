#!/usr/bin/env python3
"""
Anade el cvar user_gamertag: el gamertag del perfil de Xbox 360 emulado.

    python tools/parche_gamertag.py            aplicar
    python tools/parche_gamertag.py --estado
    python tools/parche_gamertag.py --revertir

Toca un fichero del SDK:  src/system/xam/user_profile.cpp
No guarda .original: aplica y deshace por sustitucion de texto exacta.


POR QUE
=======

El SDK tiene un solo perfil, y su nombre va fijo a "User" en el constructor de
UserProfile. De ahi lo sacan XamUserGetName, XamUserGetGamerTag y
XamUserGetSigninInfo, que es lo que el juego pregunta. Con este cvar se elige.

Solo cambia el nombre. El XUID sigue siendo el mismo, asi que las partidas
guardadas no se pierden al cambiarlo.

Un gamertag de Xbox 360 tiene como mucho 15 caracteres: esas funciones copian a
un bufer de 16 con el terminador, y lo que sobre se cortaria. Aqui se corta a
15 y, si queda vacio, se deja "User". Que empiece por letra y solo lleve
letras, numeros y espacios lo comprueba la app antes de pasarlo.
"""

import argparse
import os
import pathlib
import sys


FICHERO = "src/system/xam/user_profile.cpp"

BLOQUES = [
    (
        '''#include <rex/system/xam/user_profile.h>
''',
        '''#include <rex/system/xam/user_profile.h>
#include <rex/cvar.h>

// PARCHE LOCAL - gamertag (tools/parche_gamertag.py).
REXCVAR_DEFINE_STRING(user_gamertag, "User", "Kernel",
                      "Gamertag del perfil de Xbox 360: hasta 15 caracteres");
''',
    ),
    (
        '''  name_ = "User";
''',
        '''  // PARCHE LOCAL - gamertag: el del cvar, cortado a los 15 de Xbox 360.
  name_ = REXCVAR_GET(user_gamertag).substr(0, 15);
  if (name_.empty()) {
    name_ = "User";
  }
  REXLOG_INFO("[perfil] gamertag '{}'", name_);
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
        print(f"  gamertag                   {estado}")
        return 0

    if args.revertir:
        if puestos == 0:
            print("[ok] gamertag: no habia nada puesto")
            return 0
        for ancla, nuevo in BLOQUES:
            txt = txt.replace(nuevo, ancla)
        escribir(f, txt, eol)
        print(f"[ok] Quitados {puestos} bloques")
        return 0

    if puestos == len(BLOQUES):
        print("[ok] gamertag: ya estaba")
        return 0
    if puestos:
        sys.exit(f"[ERROR] gamertag esta a medias ({puestos}/{len(BLOQUES)}). "
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
    print("[ok] Aplicado: cvar user_gamertag disponible")
    return 0


if __name__ == "__main__":
    sys.exit(main())
