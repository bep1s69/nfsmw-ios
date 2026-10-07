#!/usr/bin/env python3
"""
Hace baratos los fallos de pagina de la vigilancia de escritura en Linux/Android.

    python tools/parche_fallos.py            aplicar
    python tools/parche_fallos.py --estado
    python tools/parche_fallos.py --revertir

Toca un fichero del SDK:  src/system/mmio_handler.cpp

No guarda .original: aplica y deshace por sustitucion de texto exacta.


EL FALLO
========

Encontrado perfilando el juego en un Snapdragon 8 Elite con simpleperf: el 82 %
del tiempo del hilo principal del juego se iba en el manejador de SIGSEGV,

    MMIOHandler::ExceptionCallback
      -> memory::QueryProtect
        -> leer /proc/self/maps y parsearlo con sscanf   (read, push_back, sscanf)

Para que la emulacion de la GPU sepa cuando el juego escribe en memoria que ya
ha subido a la GPU -texturas, vertices-, esas paginas se protegen contra
escritura. La primera escritura falla, el manejador avisa y quita la proteccion.
Es un mecanismo normal y el juego lo dispara muchisimo.

Antes de avisar, el manejador comprueba si OTRO hilo ha quitado ya la
proteccion en ese instante (una carrera), preguntando al sistema que proteccion
tiene la pagina. En Windows eso es VirtualQuery, una llamada barata. En Linux y
Android no hay llamada para eso: QueryProtect LEE /proc/self/maps ENTERO -cientos
de lineas con un driver de Vulkan cargado- y lo parsea. En cada fallo.

El parche Android del SDK ya intento cachear ese fichero, pero la cache se tira
en cada cambio de proteccion, y el ciclo de la vigilancia (fallo, desproteger,
volver a proteger) cambia protecciones sin parar. En la practica se relee
siempre.


EL ARREGLO
==========

Invertir el orden. El callback de la vigilancia mira primero un bitmap EN
MEMORIA (PhysicalHeap::TriggerCallbacks, system_page_flags_) para saber si la
pagina esta vigilada, y si lo esta la desprotege y avisa. Ese es el caso comun y
no necesita al sistema para nada.

Solo si el callback NO reconoce el fallo se hace la comprobacion cara de la
carrera. Si otro hilo ya habia quitado la vigilancia, el callback lo resuelve
igual (ve la pagina escribible para el guest, la deja escribible y devuelve
true, con un aviso "Recovered stale physical page protection" que en la carrera
es inofensivo). Un fallo de verdad -memoria sin mapear- sigue llegando al final y
devolviendo false, como antes.
"""

import argparse
import os
import pathlib
import sys


ANCLA = '''  if (!range) {
    // Recheck if the pages are still protected (race condition - another thread
    // clears the watch we just hit).
    // Do this under the lock so we don't introduce another race condition.
    auto lock = global_critical_region_.Acquire();
    memory::PageAccess cur_access;
    size_t page_length = memory::page_size();
    memory::QueryProtect(fault_host_address, page_length, cur_access);
    if (cur_access != memory::PageAccess::kNoAccess &&
        (!is_write || cur_access != memory::PageAccess::kReadOnly)) {
      // Another thread has cleared this watch. Abort.
      return true;
    }
    // The address is not found within any range, so either a write watch or an
    // actual access violation.
    if (access_violation_callback_) {
      return access_violation_callback_(std::move(lock), access_violation_callback_context_,
                                        fault_host_address, is_write);
    }
    return false;
  }
'''

NUEVO = '''  if (!range) {
    // PARCHE LOCAL - fallos baratos
    //
    // Primero el callback de la vigilancia de escritura: mira un bitmap en
    // memoria y, si la pagina esta vigilada, la desprotege y avisa. Es el caso
    // comun y no toca al sistema.
    //
    // La comprobacion de la carrera de abajo (otro hilo ya quito la vigilancia)
    // usa QueryProtect, que en Linux y Android LEE /proc/self/maps ENTERO y lo
    // parsea: en un movil se comia el 82 % del hilo principal del juego. Ahora
    // solo se hace si el callback no reconoce el fallo.
    if (access_violation_callback_) {
      auto lock = global_critical_region_.Acquire();
      if (access_violation_callback_(std::move(lock), access_violation_callback_context_,
                                     fault_host_address, is_write)) {
        return true;
      }
    }
    // Recheck if the pages are still protected (race condition - another thread
    // clears the watch we just hit).
    // Do this under the lock so we don't introduce another race condition.
    auto lock = global_critical_region_.Acquire();
    memory::PageAccess cur_access;
    size_t page_length = memory::page_size();
    memory::QueryProtect(fault_host_address, page_length, cur_access);
    if (cur_access != memory::PageAccess::kNoAccess &&
        (!is_write || cur_access != memory::PageAccess::kReadOnly)) {
      // Another thread has cleared this watch. Abort.
      return true;
    }
    return false;
  }
'''

FICHERO = "src/system/mmio_handler.cpp"


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
        print(f"  fallos                     {'aplicado' if NUEVO in txt else 'sin aplicar'}")
        return 0

    if args.revertir:
        if NUEVO not in txt:
            print("[ok] fallos: no habia nada puesto")
            return 0
        escribir(f, txt.replace(NUEVO, ANCLA), eol)
        print("[ok] Quitado")
        return 0

    if NUEVO in txt:
        print("[ok] fallos: ya estaba")
        return 0
    n = txt.count(ANCLA)
    if n != 1:
        sys.exit(f"[ERROR] El anclaje aparece {n} veces en {FICHERO}, esperaba 1.\n"
                 "        El SDK habra cambiado. No he tocado nada.")
    escribir(f, txt.replace(ANCLA, NUEVO), eol)
    print("[ok] Aplicado: el callback de la vigilancia antes que /proc/self/maps")
    return 0


if __name__ == "__main__":
    sys.exit(main())
