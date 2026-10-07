#!/usr/bin/env python3
"""
Hace que el teclado sirva en los menus del juego.

    python tools/parche_teclado.py            aplicar
    python tools/parche_teclado.py --estado
    python tools/parche_teclado.py --revertir

Toca un fichero del SDK:  src/input/mnk/mnk_input_driver.cpp

No guarda .original: aplica y deshace por sustitucion de texto exacta.


EL FALLO
========

El driver de teclado y raton (--mnk_mode=true) emula un mando. XInput tiene dos
formas de leer un mando, y el juego usa las dos:

    XInputGetState       el estado de los botones ahora mismo. La usa, por
                         ejemplo, para saltar los videos.
    XInputGetKeystroke   una cola de pulsaciones (tecla abajo / tecla arriba).
                         La usan los menus, empezando por "Presionar START".

El driver responde a la primera, pero la cola de la segunda no se llena nunca:
EnqueueKeystroke esta escrito y NADIE lo llama. Con teclado se saltan los
videos y el juego se queda para siempre en la pantalla de titulo.

Afecta a cualquiera que juegue con teclado, tambien en Windows. En Android
sirve ademas para el banco de pruebas: adb puede pulsar teclas
(`input keyevent --longpress`), pero no botones de un mando que no existe.


EL ARREGLO
==========

Al pedir una pulsacion, si la cola esta vacia, comparar los botones de ahora
(con las mismas teclas asignadas que usa XInputGetState) con los de la ultima
vez y encolar un evento por cada boton que haya cambiado: primero los que se
sueltan y luego los que se pulsan, como hace el driver de mandos SDL. Entran
los botones, los gatillos y las cuatro direcciones del stick izquierdo, que es
con lo que se navega por un menu.
"""

import argparse
import os
import pathlib
import sys


ANCLA = '''  std::lock_guard lock(state_mutex_);
  if (keystroke_queue_.empty()) {
    return X_ERROR_EMPTY;
  }
'''

NUEVO = '''  std::lock_guard lock(state_mutex_);
  if (keystroke_queue_.empty()) {
    // PARCHE LOCAL - teclado: nadie llamaba a EnqueueKeystroke, asi que la cola
    // de XInputGetKeystroke estaba siempre vacia y los menus (que leen por
    // ahi, no por XInputGetState) no veian ninguna tecla. Aqui se comparan los
    // botones de ahora con los de la ultima vez y se encola un evento por
    // cambio: primero los que se sueltan, luego los que se pulsan.
    static uint64_t botones_previos = 0;  // un solo dispositivo; bajo state_mutex_
    struct Boton {
      std::string asignacion;
      VirtualKey vk;
    };
    const Boton botones[] = {
        {REXCVAR_GET(keybind_dpad_up), VirtualKey::kXInputPadDpadUp},
        {REXCVAR_GET(keybind_dpad_down), VirtualKey::kXInputPadDpadDown},
        {REXCVAR_GET(keybind_dpad_left), VirtualKey::kXInputPadDpadLeft},
        {REXCVAR_GET(keybind_dpad_right), VirtualKey::kXInputPadDpadRight},
        {REXCVAR_GET(keybind_start), VirtualKey::kXInputPadStart},
        {REXCVAR_GET(keybind_back), VirtualKey::kXInputPadBack},
        {REXCVAR_GET(keybind_lstick_press), VirtualKey::kXInputPadLThumbPress},
        {REXCVAR_GET(keybind_rstick_press), VirtualKey::kXInputPadRThumbPress},
        {REXCVAR_GET(keybind_left_shoulder), VirtualKey::kXInputPadLShoulder},
        {REXCVAR_GET(keybind_right_shoulder), VirtualKey::kXInputPadRShoulder},
        {REXCVAR_GET(keybind_a), VirtualKey::kXInputPadA},
        {REXCVAR_GET(keybind_b), VirtualKey::kXInputPadB},
        {REXCVAR_GET(keybind_x), VirtualKey::kXInputPadX},
        {REXCVAR_GET(keybind_y), VirtualKey::kXInputPadY},
        {REXCVAR_GET(keybind_left_trigger), VirtualKey::kXInputPadLTrigger},
        {REXCVAR_GET(keybind_right_trigger), VirtualKey::kXInputPadRTrigger},
        {REXCVAR_GET(keybind_lstick_up), VirtualKey::kXInputPadLThumbUp},
        {REXCVAR_GET(keybind_lstick_down), VirtualKey::kXInputPadLThumbDown},
        {REXCVAR_GET(keybind_lstick_right), VirtualKey::kXInputPadLThumbRight},
        {REXCVAR_GET(keybind_lstick_left), VirtualKey::kXInputPadLThumbLeft},
    };
    uint64_t ahora = 0;
    if (is_active() && has_focus_) {
      for (size_t i = 0; i < std::size(botones); ++i) {
        if (IsBindPressed(key_down_, botones[i].asignacion)) {
          ahora |= uint64_t(1) << i;
        }
      }
    }
    const uint64_t cambiados = ahora ^ botones_previos;
    for (int pasada = 0; pasada < 2; ++pasada) {
      const bool pulsados = pasada == 1;
      for (size_t i = 0; i < std::size(botones); ++i) {
        const uint64_t bit = uint64_t(1) << i;
        if ((cambiados & bit) && ((ahora & bit) != 0) == pulsados) {
          EnqueueKeystroke(static_cast<uint16_t>(botones[i].vk), pulsados);
        }
      }
    }
    botones_previos = ahora;
  }
  if (keystroke_queue_.empty()) {
    return X_ERROR_EMPTY;
  }
'''

FICHERO = "src/input/mnk/mnk_input_driver.cpp"


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
        print(f"  teclado                    {'aplicado' if NUEVO in txt else 'sin aplicar'}")
        return 0

    if args.revertir:
        if NUEVO not in txt:
            print("[ok] teclado: no habia nada puesto")
            return 0
        escribir(f, txt.replace(NUEVO, ANCLA), eol)
        print("[ok] Quitado")
        return 0

    if NUEVO in txt:
        print("[ok] teclado: ya estaba")
        return 0
    n = txt.count(ANCLA)
    if n != 1:
        sys.exit(f"[ERROR] El anclaje aparece {n} veces en {FICHERO}, esperaba 1.\n"
                 "        El SDK habra cambiado. No he tocado nada.")
    escribir(f, txt.replace(ANCLA, NUEVO), eol)
    print("[ok] Aplicado: el teclado genera pulsaciones para los menus")
    return 0


if __name__ == "__main__":
    sys.exit(main())
