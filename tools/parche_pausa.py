#!/usr/bin/env python3
"""
Suelta la superficie cuando Android manda la app a segundo plano.

    python tools/parche_pausa.py            aplicar
    python tools/parche_pausa.py --estado
    python tools/parche_pausa.py --revertir

Toca tres ficheros del SDK:

    include/rex/ui/window_sdl.h        el metodo nuevo
    src/ui/window_sdl.cpp              lo que hace
    src/ui/windowed_app_context_sdl.cpp  los eventos de SDL que lo disparan

No guarda .original: aplica y deshace por sustitucion de texto exacta, bloque a
bloque, como los demas parches de este proyecto.


DE DONDE SALE ESTO
==================

Primera partida de verdad en el movil: el juego llega al menu, se sale a la
pantalla de inicio de Android y el proceso revienta. En el log:

    VulkanPresenter: Failed to submit command buffers
    VulkanPresenter: Created 2688x1216 swapchain ...      (otra vez)
    VulkanPresenter: Failed to submit command buffers     (y otra)
    ...
    Vulkan Warning (tu_knl_kgsl.cc:1723): GPU faulted or hung (VK_ERROR_DEVICE_LOST)

Y el volcado: SIGABRT en el hilo "GPU Commands", dentro de librexgpu-xenos.

Al pasar a segundo plano, Android DESTRUYE la superficie de la ventana. El
ANativeWindow que tiene el presentador deja de valer, cada envio falla, y el
presentador responde recreando el swapchain y volviendo a intentarlo, en
bucle, hasta que el driver da el dispositivo por perdido.

El SDK ya sabe hacer lo correcto -Window::OnSurfaceChanged(false) suelta el
presentador de la superficie y para de pintar-, pero en Android no lo llama
nadie: SDL avisa con eventos de aplicacion (SDL_EVENT_DID_ENTER_BACKGROUND y
compania), y el SDK solo mira los eventos de ventana.

Este parche conecta las dos cosas.


POR QUE DID_ENTER y no WILL_ENTER
=================================

SDL manda cuatro: WILL_ENTER_BACKGROUND, DID_ENTER_BACKGROUND,
WILL_ENTER_FOREGROUND y DID_ENTER_FOREGROUND.

Para SOLTAR se usa WILL_ENTER_BACKGROUND, que llega ANTES de que la superficie
desaparezca: soltarla despues es tarde, que es justo el problema.

Para RECUPERAR se usa DID_ENTER_FOREGROUND, que llega cuando la superficie ya
esta creada otra vez. Con WILL_ENTER_FOREGROUND todavia no la hay y
CreateSurface devolveria nulo.
"""

import argparse
import os
import pathlib
import sys


# ---------------------------------------------------------------------------
#  include/rex/ui/window_sdl.h
# ---------------------------------------------------------------------------

DECL_ANCLA = '''  void HandlePaintEvent();
'''

DECL_NUEVO = '''  void HandlePaintEvent();
  // PARCHE LOCAL - pausa: la superficie de Android se va y vuelve con la app.
  void HandleSurfaceAvailability(bool available);
'''


# ---------------------------------------------------------------------------
#  src/ui/window_sdl.cpp
# ---------------------------------------------------------------------------

IMPL_ANCLA = '''void WindowSDL::HandlePaintEvent() {
'''

IMPL_NUEVO = '''// PARCHE LOCAL - pausa
//
// Android destruye la superficie de la ventana al mandar la app a segundo
// plano. OnSurfaceChanged(false) suelta al presentador de ella y deja de
// pintar; sin eso, cada envio a la cola falla, el presentador recrea el
// swapchain una y otra vez y el driver acaba dando el dispositivo por perdido
// (VK_ERROR_DEVICE_LOST) y abortando.
void WindowSDL::HandleSurfaceAvailability(bool available) {
  REXLOG_INFO("WindowSDL: la superficie {}", available ? "vuelve" : "se va");
  OnSurfaceChanged(available);
}

void WindowSDL::HandlePaintEvent() {
'''


# ---------------------------------------------------------------------------
#  src/ui/windowed_app_context_sdl.cpp
# ---------------------------------------------------------------------------

EVENTO_ANCLA = '''  switch (event.type) {
    case SDL_EVENT_QUIT:
'''

EVENTO_NUEVO = '''  switch (event.type) {
    // PARCHE LOCAL - pausa
    //
    // Estos son eventos de APLICACION, sin ventana asociada, asi que no entran
    // por el reparto de eventos de ventana de mas arriba. En Android marcan el
    // momento en que la superficie se destruye y se vuelve a crear.
    //
    // WILL_ y no DID_ al irse: la superficie tiene que soltarse ANTES de que
    // desaparezca. Al volver es al reves, DID_, porque hasta entonces todavia
    // no hay superficie que coger.
    case SDL_EVENT_WILL_ENTER_BACKGROUND:
    case SDL_EVENT_DID_ENTER_FOREGROUND: {
      const bool disponible = event.type == SDL_EVENT_DID_ENTER_FOREGROUND;
#if REX_PLATFORM_ANDROID
      if (disponible) break;
#endif
      for (const auto& [id, window] : windows_) {
        if (window) {
          window->HandleSurfaceAvailability(disponible);
        }
      }
      break;
    }
    case SDL_EVENT_QUIT:
'''


# ---------------------------------------------------------------------------
#  src/ui/window_sdl.cpp: recuperar la superficie al volver (Android)
#
#  En Android DID_ENTER_FOREGROUND llega en onResume, ANTES de que la actividad
#  tenga otra vez superficie: pedirla ahi la deja sin crear y la pantalla se
#  queda en negro. Llega despues, con el foco de la ventana o al restaurarse,
#  y es ahi donde se recupera. Por eso el bloque de eventos de arriba no hace
#  nada al volver en Android.
# ---------------------------------------------------------------------------

FOCO_ANCLA = '''    case SDL_EVENT_WINDOW_FOCUS_GAINED:
      OnFocusUpdate(true, destruction_receiver);
      break;
'''

FOCO_NUEVO = '''    case SDL_EVENT_WINDOW_FOCUS_GAINED:
      OnFocusUpdate(true, destruction_receiver);
#if REX_PLATFORM_ANDROID
      if (!HasSurface()) {
        HandleSurfaceAvailability(true);
      }
#endif
      break;
'''

RESTAURAR_ANCLA = '''    case SDL_EVENT_WINDOW_RESTORED:
      OnRestored(destruction_receiver);
      break;
'''

RESTAURAR_NUEVO = '''    case SDL_EVENT_WINDOW_RESTORED:
      OnRestored(destruction_receiver);
#if REX_PLATFORM_ANDROID
      HandleSurfaceAvailability(true);
#endif
      break;
'''


BLOQUES = [
    ("include/rex/ui/window_sdl.h", "declarar HandleSurfaceAvailability", DECL_ANCLA, DECL_NUEVO),
    ("src/ui/window_sdl.cpp", "soltar y recuperar la superficie", IMPL_ANCLA, IMPL_NUEVO),
    ("src/ui/window_sdl.cpp", "recuperarla con el foco (Android)", FOCO_ANCLA, FOCO_NUEVO),
    ("src/ui/window_sdl.cpp", "recuperarla al restaurar (Android)", RESTAURAR_ANCLA, RESTAURAR_NUEVO),
    ("src/ui/windowed_app_context_sdl.cpp", "eventos de segundo plano", EVENTO_ANCLA,
     EVENTO_NUEVO),
]


def localizar_sdk():
    raiz = pathlib.Path(__file__).resolve().parent.parent
    # NFSMW_SDK apunta a otro arbol del SDK (el de Android, por ejemplo). Si
    # esta puesta se usa SOLO esa ruta: caer en silencio en el SDK de Windows
    # parchearia el arbol equivocado.
    otro = os.environ.get("NFSMW_SDK")
    candidatos = [pathlib.Path(otro)] if otro else [raiz.parent / "rexglue-sdk", raiz / "sdk"]
    for cand in candidatos:
        if (cand / "src" / "ui" / "window_sdl.cpp").exists():
            return cand
    sys.exit("[ERROR] No encuentro src/ui/window_sdl.cpp del SDK.\n"
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
        print(f"  pausa                      {puestos} de {len(BLOQUES)} bloques aplicados")
        for ruta, nombre, _, nuevo in BLOQUES:
            print(f"      {'si' if nuevo in ficheros[ruta][1] else 'NO':>2}  {nombre}  ({ruta})")
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
            print("[ok] pausa: no habia nada puesto")
            return 0
        for f, txt, eol in ficheros.values():
            escribir(f, txt, eol)
        print(f"[ok] Quitados {quitados} bloques")
        return 0

    faltan = [b for b in BLOQUES if b[3] not in ficheros[b[0]][1]]
    if not faltan:
        print(f"[ok] pausa: los {len(BLOQUES)} bloques ya estaban")
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
