#!/usr/bin/env python3
"""
Despertar al procesador de comandos en cuanto llega el vblank, no cuando toque.

    python tools/parche_vblank.py            aplicar
    python tools/parche_vblank.py --estado
    python tools/parche_vblank.py --revertir

Toca dos ficheros del SDK:
    src/graphics/command_processor.cpp   (la espera WAIT_REG_MEM)
    src/graphics/graphics_system.cpp     (el hilo del vblank)
No guarda .original: aplica y deshace por sustitucion de texto exacta.


EL FALLO
========

Medido en el movil, en el menu 3D: de los 22 ms que duraba cada fotograma,
6,6 ms eran UNA espera del procesador de comandos (CP). Instrumentada, esa
espera resulta ser siempre la misma y acaba SIEMPRE entre 0,15 y 1,07 ms
despues de un vblank.

Es la espera del flip. El juego va a doble buffer con vsync: el paquete
WAIT_REG_MEM aguarda a que una posicion de memoria valga 0, y quien la pone a
0 es la interrupcion de vblank del propio juego. O sea que cada fotograma no
puede empezar a pintar el buffer trasero hasta el siguiente vblank de 60 Hz.

Con eso, el tiempo por fotograma queda cuantizado: si el trabajo cabe en 16,7
ms, salen 60 fps; si se pasa aunque sea por poco, ese fotograma cuesta 33,3.
El trabajo medido era de ~15,4 ms, al borde. Y encima se perdia tiempo tonto
en los dos extremos de la cadena:

  - El CP sondea la memoria con Sleep(1 ms), asi que se entera del vblank
    hasta 1 ms tarde (0,6 ms de media).
  - El hilo del vblank comprueba la hora cada 1 ms, asi que dispara el vblank
    hasta 1 ms tarde, y ademas con temblor.

Mas de un milisegundo de cada 16,7, tirado, y justo en la cadena que decide si
el fotograma entra o no en su vblank.


EL ARREGLO
==========

1. El hilo del vblank duerme hasta el instante exacto del siguiente vblank en
   vez de despertarse cada milisegundo a mirar el reloj.

2. Tras marcar el vblank -y tras la interrupcion del guest, que es la que pone
   la memoria a 0- se publica un contador y se despierta con futex a quien
   espere.

3. WAIT_REG_MEM, en vez de Sleep(1 ms), espera en ese futex con el mismo tope
   de tiempo. Si el vblank llega antes, sigue en el acto; si no, se comporta
   como antes. Para cualquier otra espera que no sea del vblank el futex
   simplemente vence por tiempo, igual que el Sleep.

En Windows no hay futex: ahi se queda el Sleep de siempre.
"""

import argparse
import os
import pathlib
import sys


FICHERO_CP = "src/graphics/command_processor.cpp"
FICHERO_GS = "src/graphics/graphics_system.cpp"

# --- command_processor.cpp -------------------------------------------------

CP_INCLUDE_ANCLA = '''#include <rex/graphics/xenos.h>
'''

CP_INCLUDE_NUEVO = '''#include <rex/graphics/xenos.h>

// PARCHE LOCAL - vblank: futex para que la espera del flip despierte con el
// vblank, y el hilo del vblank con el swap (tools/parche_vblank.py).
#if defined(__linux__)
#include <linux/futex.h>
#include <sys/syscall.h>
#include <unistd.h>
#endif
#include <atomic>
#include <climits>
#include <ctime>
'''

CP_FUNCS_ANCLA = '''void CommandProcessor::WriteRegister(uint32_t index, uint32_t value) {
'''

CP_FUNCS_NUEVO = '''// PARCHE LOCAL - vblank (tools/parche_vblank.py).
namespace {
std::atomic<uint32_t> nfsmw_vblank_seq{0};
// El swap del juego, para el vsync adaptativo: si el fotograma ya llego tarde,
// el flip no tiene por que esperar al siguiente vblank de la rejilla.
std::atomic<uint32_t> nfsmw_swap_seq{0};
}  // namespace

void NfsmwAvisarSwap() {
#if defined(__linux__)
  nfsmw_swap_seq.fetch_add(1, std::memory_order_release);
  syscall(SYS_futex, reinterpret_cast<uint32_t*>(&nfsmw_swap_seq), FUTEX_WAKE_PRIVATE, INT_MAX,
          nullptr, nullptr, 0);
#endif
}

// Duerme hasta el proximo swap, como mucho lo pedido.
void NfsmwEsperarSwap(int64_t nanos) {
#if defined(__linux__)
  const uint32_t antes = nfsmw_swap_seq.load(std::memory_order_acquire);
  timespec t;
  t.tv_sec = time_t(nanos / 1000000000);
  t.tv_nsec = long(nanos % 1000000000);
  syscall(SYS_futex, reinterpret_cast<uint32_t*>(&nfsmw_swap_seq), FUTEX_WAIT_PRIVATE, antes, &t,
          nullptr, 0);
#else
  rex::thread::Sleep(std::chrono::nanoseconds(nanos));
#endif
}

void NfsmwAvisarVblank() {
#if defined(__linux__)
  nfsmw_vblank_seq.fetch_add(1, std::memory_order_release);
  syscall(SYS_futex, reinterpret_cast<uint32_t*>(&nfsmw_vblank_seq), FUTEX_WAKE_PRIVATE, INT_MAX,
          nullptr, nullptr, 0);
#endif
}

// Duerme hasta el proximo vblank, como mucho lo pedido.
static void NfsmwEsperarVblank(std::chrono::milliseconds tope) {
#if defined(__linux__)
  const uint32_t antes = nfsmw_vblank_seq.load(std::memory_order_acquire);
  timespec t;
  t.tv_sec = time_t(tope.count() / 1000);
  t.tv_nsec = long((tope.count() % 1000) * 1000000);
  syscall(SYS_futex, reinterpret_cast<uint32_t*>(&nfsmw_vblank_seq), FUTEX_WAIT_PRIVATE, antes, &t,
          nullptr, 0);
#else
  rex::thread::Sleep(tope);
#endif
}

void CommandProcessor::WriteRegister(uint32_t index, uint32_t value) {
'''

CP_SWAP_ANCLA = '''  IssueSwap(frontbuffer_ptr, frontbuffer_width, frontbuffer_height);
'''

CP_SWAP_NUEVO = '''  IssueSwap(frontbuffer_ptr, frontbuffer_width, frontbuffer_height);

  // PARCHE LOCAL - vblank: avisar al hilo del vblank de que hay fotograma nuevo
  // (vsync adaptativo, tools/parche_vblank.py).
  NfsmwAvisarSwap();
'''

CP_ESPERA_ANCLA = '''        if (!REXCVAR_GET(vsync)) {
          // User wants it fast and dangerous.
          rex::thread::MaybeYield();
        } else {
          rex::thread::Sleep(std::chrono::milliseconds(wait / 0x100));
        }
'''

CP_ESPERA_NUEVO = '''        if (!REXCVAR_GET(vsync)) {
          // User wants it fast and dangerous.
          rex::thread::MaybeYield();
        } else {
          // PARCHE LOCAL - vblank: despertar en cuanto llegue el vblank, que es
          // lo que suele desbloquear esta espera (tools/parche_vblank.py).
          NfsmwEsperarVblank(std::chrono::milliseconds(wait / 0x100));
        }
'''

# --- graphics_system.cpp ---------------------------------------------------

GS_BUCLE_ANCLA = '''        uint64_t last_frame_time = chrono::Clock::QueryGuestTickCount();
        while (vsync_worker_running_) {
          uint64_t current_time = chrono::Clock::QueryGuestTickCount();
          uint64_t interval_ticks =
              REXCVAR_GET(vsync) ? vsync_interval_ticks : no_vsync_interval_ticks;
          while (current_time - last_frame_time >= interval_ticks) {
            MarkVblank();
            last_frame_time += interval_ticks;
          }
          rex::thread::Sleep(std::chrono::milliseconds(1));
        }
'''

GS_BUCLE_NUEVO = '''        uint64_t last_frame_time = chrono::Clock::QueryGuestTickCount();
        while (vsync_worker_running_) {
          uint64_t current_time = chrono::Clock::QueryGuestTickCount();
          uint64_t interval_ticks =
              REXCVAR_GET(vsync) ? vsync_interval_ticks : no_vsync_interval_ticks;
          bool marcado = false;  // PARCHE LOCAL - vblank (tools/parche_vblank.py)
          if (current_time - last_frame_time >= interval_ticks) {
            MarkVblank();
            // La rejilla se reengancha al momento real y no acumula: asi un
            // fotograma tardio marca el ritmo en vez de perder medio vblank.
            last_frame_time = current_time;
            marcado = true;
          }
          // PARCHE LOCAL - vblank: avisar a quien espera el flip (el
          // procesador de comandos) en cuanto la interrupcion del guest ha
          // corrido, y dormir hasta el instante justo del proximo vblank en
          // vez de despertar cada milisegundo a mirar el reloj.
          if (marcado) {
            NfsmwAvisarVblank();
          }
          // Vsync adaptativo: el juego va a doble bufer, asi que el flip de
          // cada fotograma espera al siguiente vblank. Si el fotograma se pasa
          // aunque sea por poco de los 16,7 ms, esperar al siguiente vblank de
          // la rejilla lo deja en 33,3: los fps caen de 60 a 30 de golpe. Con
          // esto, el hilo duerme hasta el proximo swap o hasta el vblank, lo
          // que llegue antes, y si el swap llega cuando ya toca vblank lo
          // dispara en el acto. Nunca antes de tiempo: el tope de 60 se
          // mantiene porque el vblank sigue sin poder adelantarse a su hora.
          uint64_t faltan_ticks = (last_frame_time + interval_ticks) - current_time;
          int64_t faltan_ns =
              int64_t(double(faltan_ticks) * 1000000000.0 / double(guest_tick_frequency));
          if (faltan_ns > 100000) {
            NfsmwEsperarSwap(faltan_ns);
          } else {
            rex::thread::MaybeYield();
          }
        }
'''

GS_DECL_ANCLA = '''namespace rex::graphics {
'''

GS_DECL_NUEVO = '''namespace rex::graphics {

// PARCHE LOCAL - vblank: definido en command_processor.cpp
// (tools/parche_vblank.py).
void NfsmwAvisarVblank();
void NfsmwEsperarSwap(int64_t nanos);
'''

BLOQUES = {
    FICHERO_CP: [(CP_INCLUDE_ANCLA, CP_INCLUDE_NUEVO), (CP_FUNCS_ANCLA, CP_FUNCS_NUEVO),
                 (CP_ESPERA_ANCLA, CP_ESPERA_NUEVO), (CP_SWAP_ANCLA, CP_SWAP_NUEVO)],
    FICHERO_GS: [(GS_DECL_ANCLA, GS_DECL_NUEVO), (GS_BUCLE_ANCLA, GS_BUCLE_NUEVO)],
}


def localizar_sdk():
    raiz = pathlib.Path(__file__).resolve().parent.parent
    # NFSMW_SDK apunta a otro arbol del SDK (el de Android, por ejemplo). Si
    # esta puesta se usa SOLO esa ruta: caer en silencio en el SDK de Windows
    # parchearia el arbol equivocado.
    otro = os.environ.get("NFSMW_SDK")
    candidatos = [pathlib.Path(otro)] if otro else [raiz.parent / "rexglue-sdk", raiz / "sdk"]
    for cand in candidatos:
        if (cand / FICHERO_CP).exists():
            return cand
    sys.exit(f"[ERROR] No encuentro {FICHERO_CP} del SDK.\n"
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

    sdk = localizar_sdk()
    total = sum(len(v) for v in BLOQUES.values())
    puestos = 0
    for rel, bloques in BLOQUES.items():
        txt, _ = leer(sdk / rel)
        puestos += sum(1 for _, nuevo in bloques if nuevo in txt)

    if args.estado:
        estado = ("aplicado" if puestos == total else "sin aplicar" if puestos == 0
                  else f"A MEDIAS ({puestos}/{total})")
        print(f"  vblank                     {estado}")
        return 0

    if args.revertir:
        if puestos == 0:
            print("[ok] vblank: no habia nada puesto")
            return 0
        for rel, bloques in BLOQUES.items():
            txt, eol = leer(sdk / rel)
            for ancla, nuevo in bloques:
                txt = txt.replace(nuevo, ancla)
            escribir(sdk / rel, txt, eol)
        print(f"[ok] Quitados {puestos} bloques")
        return 0

    if puestos == total:
        print("[ok] vblank: ya estaba")
        return 0
    if puestos:
        sys.exit(f"[ERROR] vblank esta a medias ({puestos}/{total}). Revierte con --revertir.")
    for rel, bloques in BLOQUES.items():
        txt, _ = leer(sdk / rel)
        for ancla, _nuevo in bloques:
            n = txt.count(ancla)
            if n != 1:
                sys.exit(f"[ERROR] Un anclaje aparece {n} veces en {rel}, esperaba 1:\n"
                         f"        {ancla.splitlines()[0].strip()}\n"
                         "        El SDK habra cambiado. No he tocado nada.")
    for rel, bloques in BLOQUES.items():
        txt, eol = leer(sdk / rel)
        for ancla, nuevo in bloques:
            txt = txt.replace(ancla, nuevo, 1)
        escribir(sdk / rel, txt, eol)
    print("[ok] Aplicado: el CP despierta con el vblank, y el vblank llega a su hora")
    return 0


if __name__ == "__main__":
    sys.exit(main())
