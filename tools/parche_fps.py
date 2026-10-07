#!/usr/bin/env python3
"""
Escribe los fps en el log, una linea cada cinco segundos.

    python tools/parche_fps.py            aplicar
    python tools/parche_fps.py --estado
    python tools/parche_fps.py --revertir

Toca un fichero del SDK:

    src/graphics/vulkan/command_processor.cpp

Solo Vulkan: es el unico backend que se compila en Android, que es donde hace
falta. En Windows ya esta el overlay de F3.

No guarda .original: aplica y deshace por sustitucion de texto exacta, bloque a
bloque, como los demas parches de este proyecto.


POR QUE HACE FALTA
==================

En escritorio los fps se miran con el overlay de F3. En un movil no hay teclado
para abrirlo, y medir desde fuera tampoco siempre se puede:

  - Hay ROMs que capan logcat. En la nubia NX789J, `adb logcat` devuelve cero
    lineas para cualquier app.
  - `dumpsys SurfaceFlinger --latency <capa>` devuelve solo el periodo de
    refresco, sin fotogramas, para la capa del juego.
  - Subir el log a `debug` para contar las lineas de PRESENT MIDE OTRA COSA:
    escribir una linea por fotograma en el almacenamiento compartido cuesta
    tanto que cambia el resultado. Con `debug` salian 8 fps donde sin el
    salen bastantes mas.

Asi que el contador va dentro, cuenta los fotogramas que el JUEGO presenta -no
los que compone Android- y escribe una sola linea cada cinco segundos, a nivel
info, que es barato y no ensucia.

Va en el procesador de comandos de cada backend, que es donde el guest pide el
cambio de buffer.
"""

import argparse
import os
import pathlib
import sys


CUENTA = '''  // PARCHE LOCAL - contador de fps
  //
  // Los fotogramas que presenta el JUEGO: una linea cada cinco segundos a
  // nivel info, y cada medio segundo en nfsmw_fps_invitado para el contador en
  // pantalla. Esto corre siempre en el hilo del procesador de comandos, asi que
  // las estaticas no necesitan candado.
  {
    using RelojFps = std::chrono::steady_clock;
    static RelojFps::time_point fps_desde{};
    static RelojFps::time_point fps_desde_corto{};
    static uint32_t fps_cuenta = 0;
    static uint32_t fps_cuenta_corta = 0;
    static RelojFps::time_point fps_anterior{};
    static double fps_peor_ms = 0.0;
    const auto fps_ahora = RelojFps::now();
    if (fps_desde == RelojFps::time_point{}) {
      fps_desde = fps_ahora;
      fps_desde_corto = fps_ahora;
    } else {
      ++fps_cuenta;
      ++fps_cuenta_corta;
      if (fps_anterior != RelojFps::time_point{}) {
        const double fps_este_ms =
            std::chrono::duration<double, std::milli>(fps_ahora - fps_anterior).count();
        if (fps_este_ms > fps_peor_ms) {
          fps_peor_ms = fps_este_ms;
        }
      }
      fps_anterior = fps_ahora;
      const double fps_corto =
          std::chrono::duration<double>(fps_ahora - fps_desde_corto).count();
      if (fps_corto >= 0.5) {
        nfsmw_fps_invitado.store(float(fps_cuenta_corta / fps_corto), std::memory_order_relaxed);
        nfsmw_ms_invitado.store(float(fps_corto * 1000.0 / fps_cuenta_corta),
                                std::memory_order_relaxed);
        nfsmw_ms_peor_invitado.store(float(fps_peor_ms), std::memory_order_relaxed);
        fps_peor_ms = 0.0;
        fps_cuenta_corta = 0;
        fps_desde_corto = fps_ahora;
      }
      const double fps_segundos = std::chrono::duration<double>(fps_ahora - fps_desde).count();
      if (fps_segundos >= 5.0) {
        REXGPU_INFO("fps: {:.1f}  ({} fotogramas en {:.1f} s, {:.1f} ms por fotograma)",
                    fps_cuenta / fps_segundos, fps_cuenta, fps_segundos,
                    fps_segundos * 1000.0 / fps_cuenta);
        fps_cuenta = 0;
        fps_desde = fps_ahora;
      }
    }
  }
'''


VK_ANCLA = '''  REXGPU_DEBUG(
      "XELOG_GPU PRESENT: swap_texture_view={:p} packet_size={}x{} src_size={}x{} "
'''

VK_NUEVO = CUENTA + VK_ANCLA

VK_INC_ANCLA = '''#include <algorithm>
#include <array>
#include <atomic>
'''

VK_INC_NUEVO = '''#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>  // PARCHE LOCAL - contador de fps

// PARCHE LOCAL - contador de fps: los fps del juego, medidos sobre el ultimo
// medio segundo. Con nombre C y visibilidad por defecto para que se pueda leer
// con dlsym desde fuera del plugin: la app Android lo pinta en pantalla
// (android/app/src/main/cpp/android_main.cpp, nativeFps).
extern "C" __attribute__((visibility("default"))) std::atomic<float> nfsmw_fps_invitado{0.0f};

// PARCHE LOCAL - contador de fps: el tiempo por fotograma, en milisegundos. La
// media dice el ritmo; el peor del ultimo medio segundo dice los tirones, que
// es lo que no se ve en una media.
extern "C" __attribute__((visibility("default"))) std::atomic<float> nfsmw_ms_invitado{0.0f};
extern "C" __attribute__((visibility("default"))) std::atomic<float> nfsmw_ms_peor_invitado{0.0f};
'''


BLOQUES = [
    ("src/graphics/vulkan/command_processor.cpp", "cabecera <chrono> (Vulkan)",
     VK_INC_ANCLA, VK_INC_NUEVO),
    ("src/graphics/vulkan/command_processor.cpp", "contador de fps (Vulkan)",
     VK_ANCLA, VK_NUEVO),
]


def localizar_sdk():
    raiz = pathlib.Path(__file__).resolve().parent.parent
    # NFSMW_SDK apunta a otro arbol del SDK (el de Android, por ejemplo). Si
    # esta puesta se usa SOLO esa ruta: caer en silencio en el SDK de Windows
    # parchearia el arbol equivocado.
    otro = os.environ.get("NFSMW_SDK")
    candidatos = [pathlib.Path(otro)] if otro else [raiz.parent / "rexglue-sdk", raiz / "sdk"]
    for cand in candidatos:
        if (cand / "src" / "graphics" / "vulkan" / "command_processor.cpp").exists():
            return cand
    sys.exit("[ERROR] No encuentro src/graphics/vulkan/command_processor.cpp del SDK.\n"
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
    ficheros = {}
    for ruta, _, _, _ in BLOQUES:
        if ruta not in ficheros:
            f = sdk / ruta
            if not f.exists():
                sys.exit(f"[ERROR] No encuentro {f}")
            ficheros[ruta] = [f, *leer(f)]

    if args.estado:
        puestos = sum(1 for r, _, _, nuevo in BLOQUES if nuevo in ficheros[r][1])
        print(f"  fps                        {puestos} de {len(BLOQUES)} bloques aplicados")
        for ruta, nombre, _, nuevo in BLOQUES:
            print(f"      {'si' if nuevo in ficheros[ruta][1] else 'NO':>2}  {nombre}")
        return 0

    if args.revertir:
        quitados = 0
        for ruta, nombre, ancla, nuevo in BLOQUES:
            txt = ficheros[ruta][1]
            if nuevo not in txt:
                continue
            if txt.count(nuevo) != 1:
                sys.exit(f"[ERROR] El bloque '{nombre}' aparece {txt.count(nuevo)} veces "
                         f"en {ruta}. No lo toco, quitalo tu.")
            ficheros[ruta][1] = txt.replace(nuevo, ancla)
            quitados += 1
        if not quitados:
            print("[ok] fps: no habia nada puesto")
            return 0
        for f, txt, eol in ficheros.values():
            escribir(f, txt, eol)
        print(f"[ok] Quitados {quitados} bloques")
        return 0

    faltan = [b for b in BLOQUES if b[3] not in ficheros[b[0]][1]]
    if not faltan:
        print(f"[ok] fps: los {len(BLOQUES)} bloques ya estaban")
        return 0

    for ruta, nombre, ancla, _ in faltan:
        n = ficheros[ruta][1].count(ancla)
        if n != 1:
            sys.exit(f"[ERROR] El anclaje de '{nombre}' aparece {n} veces en {ruta}, "
                     f"esperaba 1. El SDK habra cambiado. No he tocado nada.")

    for ruta, nombre, ancla, nuevo in faltan:
        ficheros[ruta][1] = ficheros[ruta][1].replace(ancla, nuevo)
        print(f"[ok] Aplicado: {nombre}")

    for f, txt, eol in ficheros.values():
        escribir(f, txt, eol)
    return 0


if __name__ == "__main__":
    sys.exit(main())
