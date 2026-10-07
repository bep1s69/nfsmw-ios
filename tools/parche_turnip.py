#!/usr/bin/env python3
"""
Deja cargar un driver Vulkan propio (Turnip) en moviles Qualcomm Adreno.

    python tools/parche_turnip.py            aplicar
    python tools/parche_turnip.py --estado
    python tools/parche_turnip.py --revertir

SOLO PARA EL ARBOL DEL SDK DE ANDROID. Se lanza con NFSMW_SDK apuntando a el:

    set NFSMW_SDK=..\\rexglue-sdk-android
    python tools/parche_turnip.py

Va DESPUES del parche Android del SDK, porque dos de sus anclajes (el bloque
ANDROID de src/ui/CMakeLists.txt y el de SDL3 en thirdparty) los mete ese parche.
tools/android/preparar_sdk.py los aplica en ese orden.

Toca cuatro ficheros del SDK:

    include/rex/platform/dynlib.h       DynamicLibrary::Adopt()
    src/ui/vulkan/vulkan_instance.cpp   los ajustes y la carga con adrenotools
    src/ui/CMakeLists.txt               enlazar adrenotools en Android
    thirdparty/CMakeLists.txt           compilar libadrenotools si esta clonado

No guarda .original: aplica y deshace por sustitucion de texto exacta, bloque a
bloque, como los demas parches de este proyecto.


POR QUE HACE FALTA
==================

El driver Vulkan que traen los moviles Snapdragon es el propietario de
Qualcomm. Para un juego normal va bien; para la emulacion de la GPU Xenos, que
tira de extensiones y combinaciones de estado poco habituales, es donde mas
fallos de render aparecen. Turnip es el driver libre de Mesa para Adreno, y es
el que usan los emuladores de Android que funcionan bien en Snapdragon.

Pero una app de Android no puede cargar otro libvulkan.so sin mas: el cargador
de Android restringe que librerias ve cada espacio de nombres, y el driver del
sistema llega siempre primero. libadrenotools (Billy Laws, BSD-2) resuelve eso:
crea un espacio de nombres propio, engancha la carga del driver y devuelve un
handle de dlopen de un libvulkan que ya habla con el driver elegido.

El SDK carga el libvulkan en un solo sitio, VulkanInstance::Create, con
DynamicLibrary::Load. Este parche hace que, en Android y si la app lo pide,
primero se intente con adrenotools y el handle que devuelve se adopte en ese
mismo DynamicLibrary. Si falla, se sigue con el driver del sistema y se dice en
el log: un driver roto nunca deja el juego sin arrancar.


COMO SE LO PIDE LA APP
======================

Con cvars, y no con una variable global compartida, por la misma leccion que
cuenta parche_restaurar.py: vulkan_instance.cpp acaba dentro de
librexruntime.so y la app es otra libreria. El registro de cvars es lo unico
comun a las dos.

    android_gpu_driver_dir    carpeta del driver, en el almacenamiento INTERNO
                              de la app (adrenotools no carga nada de /sdcard)
    android_gpu_driver_name   nombre del .so del driver, p.ej.
                              libvulkan_freedreno.so. Vacio = driver del sistema
    android_native_lib_dir    nativeLibraryDir de la app, donde van los hooks
                              (libmain_hook.so y compania)
    android_tmp_dir           escribible; adrenotools solo lo usa en Android < 10
    android_gpu_turbo         apaga el control de energia de la GPU en KGSL
                              (KGSL_PROP_PWRCTRL). OJO: es de todo el
                              dispositivo y persiste; se aplica siempre, con
                              false tambien, para deshacerlo. En un Snapdragon
                              8 Elite RINDE MENOS: menu 3D a 14,6 fps frente a
                              42 sin el
    android_turnip_debug      TU_DEBUG para Turnip (opciones de depuracion de
                              Mesa, p. ej. noubwc,sysmem). Vacio = ninguna

La app Android (android/app/.../GameActivity.java) los pasa por linea de
comandos, asi que mandan sobre cualquier toml.


LO QUE HAY QUE TENER EN CUENTA
==============================

  - El APK tiene que empaquetarse con useLegacyPackaging = true. Si no, las
    .so no se extraen a nativeLibraryDir y los hooks no se encuentran.
  - libadrenotools no es un submodulo del SDK: lo clona
    tools/android/preparar_sdk.py en thirdparty/libadrenotools. Sin el clon,
    el bloque de CMake no hace nada y el SDK compila como antes, sin Turnip.
"""

import argparse
import os
import pathlib
import sys


# ---------------------------------------------------------------------------
#  Bloque 1: DynamicLibrary::Adopt
# ---------------------------------------------------------------------------

ADOPT_ANCLA = '''  void Close();
  explicit operator bool() const { return handle_ != nullptr; }
'''

ADOPT_NUEVO = '''  void Close();
  // PARCHE LOCAL - Turnip: toma posesion de un handle ya abierto por otro
  // cargador (adrenotools en Android). Close() lo libera igual que si lo
  // hubiera abierto Load().
  void Adopt(void* handle) {
    Close();
    handle_ = handle;
  }
  explicit operator bool() const { return handle_ != nullptr; }
'''


# ---------------------------------------------------------------------------
#  Bloque 2: cabeceras de adrenotools
# ---------------------------------------------------------------------------

INC_ANCLA = '''#if REX_PLATFORM_MAC
#include "vulkan_moltenvk.h"
#endif
'''

INC_NUEVO = '''#if REX_PLATFORM_MAC
#include "vulkan_moltenvk.h"
#endif

// PARCHE LOCAL - Turnip. REX_HAS_ADRENOTOOLS lo define src/ui/CMakeLists.txt
// solo si libadrenotools esta clonado en thirdparty.
#if REX_PLATFORM_ANDROID && defined(REX_HAS_ADRENOTOOLS)
#include <dlfcn.h>
#include <adrenotools/driver.h>
#endif
'''


# ---------------------------------------------------------------------------
#  Bloque 3: los ajustes
# ---------------------------------------------------------------------------

CVAR_ANCLA = '''REXCVAR_DEFINE_BOOL(vulkan_log_debug_messages, true, "UI/Vulkan", "Log Vulkan debug messages");
'''

CVAR_NUEVO = '''REXCVAR_DEFINE_BOOL(vulkan_log_debug_messages, true, "UI/Vulkan", "Log Vulkan debug messages");

// PARCHE LOCAL - Turnip
//
// Los rellena la app Android por linea de comandos. kInitOnly porque el
// libvulkan se carga una sola vez, al crear la instancia: cambiarlos despues no
// tendria efecto. El texto va en ingles porque es lo que sale en F4.
#if REX_PLATFORM_ANDROID
REXCVAR_DEFINE_STRING(android_gpu_driver_dir, "", "UI/Vulkan",
                      "Android: folder holding a custom Vulkan driver (app internal storage)")
    .lifecycle(rex::cvar::Lifecycle::kInitOnly);
REXCVAR_DEFINE_STRING(android_gpu_driver_name, "", "UI/Vulkan",
                      "Android: custom Vulkan driver .so name (e.g. Turnip). Empty = system driver")
    .lifecycle(rex::cvar::Lifecycle::kInitOnly);
REXCVAR_DEFINE_STRING(android_native_lib_dir, "", "UI/Vulkan",
                      "Android: the app's nativeLibraryDir, where the adrenotools hooks live")
    .lifecycle(rex::cvar::Lifecycle::kInitOnly);
REXCVAR_DEFINE_STRING(android_tmp_dir, "", "UI/Vulkan",
                      "Android: writable folder adrenotools needs on Android 9 and older")
    .lifecycle(rex::cvar::Lifecycle::kInitOnly);
REXCVAR_DEFINE_BOOL(android_gpu_turbo, false, "UI/Vulkan",
                    "Android (Adreno): disable KGSL GPU power control (device-wide, persistent; "
                    "false restores it). Slower on Snapdragon 8 Elite")
    .lifecycle(rex::cvar::Lifecycle::kInitOnly);
REXCVAR_DEFINE_STRING(android_turnip_debug, "", "UI/Vulkan",
                      "Android: TU_DEBUG for a Turnip driver (Mesa debug options, e.g. "
                      "noubwc,sysmem). Empty = none")
    .lifecycle(rex::cvar::Lifecycle::kInitOnly);
#endif
'''


# ---------------------------------------------------------------------------
#  Bloque 4: cargar el libvulkan con adrenotools
# ---------------------------------------------------------------------------

CARGA_ANCLA = '''#else
  loader_loaded = vulkan_instance->loader_.Load(platform::lib_names::kVulkanLoader);
  if (!loader_loaded) {
'''

CARGA_NUEVO = '''#else
#if REX_PLATFORM_ANDROID && defined(REX_HAS_ADRENOTOOLS)
  // PARCHE LOCAL - Turnip
  //
  // Si la app pidio un driver propio, se abre con adrenotools y el handle que
  // devuelve se adopta: a partir de aqui el resto de la funcion no sabe ni le
  // importa de donde salio el libvulkan. Si falla, se sigue con el del sistema.
  {
    const std::string& nombre = REXCVAR_GET(android_gpu_driver_name);
    if (!nombre.empty()) {
      // adrenotools concatena carpeta + nombre sin poner la barra.
      std::string carpeta = REXCVAR_GET(android_gpu_driver_dir);
      if (!carpeta.empty() && carpeta.back() != '/') {
        carpeta += '/';
      }
      const std::string& hooks = REXCVAR_GET(android_native_lib_dir);
      const std::string& tmp = REXCVAR_GET(android_tmp_dir);
      // Opciones de depuracion de Turnip (Mesa las lee al crear la instancia).
      // Se admite '+' como separador ademas de ',' (la app pasa los extras del
      // banco de pruebas separados por comas).
      std::string tu_debug = REXCVAR_GET(android_turnip_debug);
      for (char& c : tu_debug) {
        if (c == '+') {
          c = ',';
        }
      }
      if (!tu_debug.empty()) {
        setenv("TU_DEBUG", tu_debug.c_str(), 1);
        REXLOG_INFO("Vulkan: TU_DEBUG={}", tu_debug);
      }
      void* handle = adrenotools_open_libvulkan(
          RTLD_NOW, ADRENOTOOLS_DRIVER_CUSTOM, tmp.empty() ? nullptr : tmp.c_str(),
          hooks.c_str(), carpeta.c_str(), nombre.c_str(), nullptr, nullptr);
      if (handle) {
        vulkan_instance->loader_.Adopt(handle);
        loader_loaded = true;
        REXLOG_INFO("Vulkan: driver propio cargado con adrenotools: {}{}", carpeta, nombre);
      } else {
        REXLOG_WARN("Vulkan: adrenotools no pudo cargar {}{} (hooks en '{}'). "
                    "Se usa el driver del sistema.",
                    carpeta, nombre, hooks);
      }
    }
    // Siempre, tambien con false. KGSL_PROP_PWRCTRL es un ajuste de TODO el
    // dispositivo que dura hasta que alguien lo cambie: una partida con turbo
    // dejaba la GPU asi para siempre (hasta reiniciar). Y en un Snapdragon 8
    // Elite el "turbo" fija un reloj peor que el del gobernador: menu 3D a
    // 14,6 fps con turbo frente a 42 sin el.
    adrenotools_set_turbo(REXCVAR_GET(android_gpu_turbo));
  }
  if (!loader_loaded) {
    loader_loaded = vulkan_instance->loader_.Load(platform::lib_names::kVulkanLoader);
  }
#else
  loader_loaded = vulkan_instance->loader_.Load(platform::lib_names::kVulkanLoader);
#endif
  if (!loader_loaded) {
'''


# ---------------------------------------------------------------------------
#  Bloque 5: enlazar adrenotools en rexui (Android)
# ---------------------------------------------------------------------------

UI_ANCLA = '''    target_link_libraries(rexui PUBLIC android log)
'''

UI_NUEVO = '''    target_link_libraries(rexui PUBLIC android log)
    # PARCHE LOCAL - Turnip: drivers Vulkan propios via libadrenotools, si
    # thirdparty/CMakeLists.txt lo ha compilado.
    if(TARGET adrenotools)
        target_link_libraries(rexui PUBLIC adrenotools)
        target_compile_definitions(rexui PRIVATE REX_HAS_ADRENOTOOLS=1)
    endif()
'''


# ---------------------------------------------------------------------------
#  Bloque 5, en el SDK del motor nativo
#
#  El SDK de nfsmw-android (tools/android/preparar_nativo.py) tiene su propio
#  port a Android, sin el de hells-gate, y enlaza rexui con android en PRIVADO.
#  Mismo cambio, otro anclaje.
# ---------------------------------------------------------------------------

UI_ANCLA_NATIVO = '''elseif(ANDROID)
    target_link_libraries(rexui PRIVATE android)
'''

UI_NUEVO_NATIVO = '''elseif(ANDROID)
    target_link_libraries(rexui PRIVATE android)
    # PARCHE LOCAL - Turnip: drivers Vulkan propios via libadrenotools, si
    # thirdparty/CMakeLists.txt lo ha compilado.
    if(TARGET adrenotools)
        target_link_libraries(rexui PUBLIC adrenotools)
        target_compile_definitions(rexui PRIVATE REX_HAS_ADRENOTOOLS=1)
    endif()
'''


# ---------------------------------------------------------------------------
#  Bloque 6: compilar libadrenotools (Android)
# ---------------------------------------------------------------------------

TP_ANCLA = '''add_subdirectory(sdl3)
'''

TP_NUEVO = '''add_subdirectory(sdl3)

#=============================================================================
# PARCHE LOCAL - Turnip: libadrenotools (BSD-2), solo Android
#
# No es submodulo del SDK: lo clona tools/android/preparar_sdk.py del proyecto
# NFSMW en thirdparty/libadrenotools. Sin el clon no se compila y el SDK queda
# como antes, con el driver Vulkan del sistema.
#
# Ademas de la libreria estatica deja cuatro .so de hooks (main_hook,
# file_redirect_hook, gsl_alloc_hook, hook_impl) que el APK tiene que llevar en
# nativeLibraryDir.
#=============================================================================
if(ANDROID AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/libadrenotools/CMakeLists.txt")
    add_subdirectory(libadrenotools)
endif()
'''


# Bloques que en otro arbol del SDK llevan otro anclaje: {nombre: [(ancla, nuevo)]}.
ALTERNATIVAS = {
    "enlazar adrenotools": [(UI_ANCLA_NATIVO, UI_NUEVO_NATIVO)],
}

BLOQUES = [
    ("include/rex/platform/dynlib.h", "DynamicLibrary::Adopt", ADOPT_ANCLA, ADOPT_NUEVO),
    ("src/ui/vulkan/vulkan_instance.cpp", "cabeceras de adrenotools", INC_ANCLA, INC_NUEVO),
    ("src/ui/vulkan/vulkan_instance.cpp", "ajustes android_gpu_*", CVAR_ANCLA, CVAR_NUEVO),
    ("src/ui/vulkan/vulkan_instance.cpp", "carga del driver con adrenotools", CARGA_ANCLA, CARGA_NUEVO),
    ("src/ui/CMakeLists.txt", "enlazar adrenotools", UI_ANCLA, UI_NUEVO),
    ("thirdparty/CMakeLists.txt", "compilar libadrenotools", TP_ANCLA, TP_NUEVO),
]


def localizar_sdk():
    raiz = pathlib.Path(__file__).resolve().parent.parent
    # NFSMW_SDK apunta a otro arbol del SDK (el de Android, por ejemplo). Si
    # esta puesta se usa SOLO esa ruta: caer en silencio en el SDK de Windows
    # parchearia el arbol equivocado.
    otro = os.environ.get("NFSMW_SDK")
    candidatos = [pathlib.Path(otro)] if otro else [raiz.parent / "rexglue-sdk-android"]
    for cand in candidatos:
        if (cand / "src" / "ui" / "vulkan" / "vulkan_instance.cpp").exists():
            return cand
    sys.exit("[ERROR] No encuentro src/ui/vulkan/vulkan_instance.cpp del SDK.\n"
             "        Se busca en NFSMW_SDK, o en ..\\rexglue-sdk-android")


def leer(f):
    # newline="" para no tocar los finales de linea: el arbol de Android viene
    # con LF y los demas parches pueden haberlo dejado en CRLF. Se detecta y se
    # respeta el que haya.
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

    # De cada bloque, la variante que vale en ESTE arbol: la que ya esta puesta,
    # o la unica cuyo anclaje aparece una vez. Si ninguna, la principal (y el
    # aviso de abajo dira que no entra).
    elegidos = []
    for ruta, nombre, ancla, nuevo in BLOQUES:
        txt = ficheros[ruta][1]
        variantes = [(ancla, nuevo), *ALTERNATIVAS.get(nombre, [])]
        puesta = [v for v in variantes if v[1] in txt]
        cabe = [v for v in variantes if txt.count(v[0]) == 1]
        a, n = (puesta or cabe or variantes)[0]
        elegidos.append((ruta, nombre, a, n))
    BLOQUES[:] = elegidos

    if args.estado:
        puestos = sum(1 for r, _, _, nuevo in BLOQUES if nuevo in ficheros[r][1])
        print(f"  turnip                     {puestos} de {len(BLOQUES)} bloques aplicados")
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
                sys.exit(f"[ERROR] El bloque '{nombre}' aparece {txt.count(nuevo)} veces en {ruta}.\n"
                         f"        No lo toco, quitalo tu.")
            ficheros[ruta][1] = txt.replace(nuevo, ancla)
            quitados += 1
        if not quitados:
            print("[ok] turnip: no habia nada puesto")
            return 0
        for f, txt, eol in ficheros.values():
            escribir(f, txt, eol)
        print(f"[ok] Quitados {quitados} bloques")
        return 0

    faltan = [b for b in BLOQUES if b[3] not in ficheros[b[0]][1]]
    if not faltan:
        print(f"[ok] turnip: los {len(BLOQUES)} bloques ya estaban")
        return 0

    # Primero se comprueban TODOS los anclajes y solo despues se escribe: un
    # parche a medias entre cuatro ficheros es peor que uno que no entra.
    for ruta, nombre, ancla, _ in faltan:
        n = ficheros[ruta][1].count(ancla)
        if n != 1:
            sys.exit(f"[ERROR] El anclaje de '{nombre}' aparece {n} veces en {ruta}, esperaba 1.\n"
                     f"        El SDK habra cambiado, o falta el parche Android. No he tocado nada.")

    for ruta, nombre, ancla, nuevo in faltan:
        ficheros[ruta][1] = ficheros[ruta][1].replace(ancla, nuevo)
        print(f"[ok] Aplicado: {nombre}")

    for f, txt, eol in ficheros.values():
        escribir(f, txt, eol)
    print()
    print("  Sin thirdparty/libadrenotools clonado, el SDK compila sin Turnip.")
    print("  tools/android/preparar_sdk.py lo clona.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
