#!/usr/bin/env python3
"""
Deja que --game_data_root sea una ISO, y en Android una URI content://.

    python tools/parche_iso.py            aplicar
    python tools/parche_iso.py --estado
    python tools/parche_iso.py --revertir

Toca tres ficheros del SDK:

    src/ui/rex_app.cpp             la comprobacion de que game_data_root vale
    src/system/runtime.cpp         el montaje en el VFS
    src/core/mapped_memory_posix.cpp   abrir una URI content:// al mapear

No guarda .original: aplica y deshace por sustitucion de texto exacta, bloque a
bloque, como los demas parches de este proyecto.


POR QUE HACE FALTA
==================

nfsmw_app.h busca una .iso junto al ejecutable y la pone en game_data_root, y
su comentario dice que "el parche de la ISO dejo --game_data_root aceptando las
dos cosas". Ese parche nunca llego a este repositorio, y en la etiqueta v0.10.0
del SDK faltan las tres piezas:

1. ReXApp::ConstructRuntime exige un DIRECTORIO:

       if (!std::filesystem::is_directory(paths.game_data_root)) {
         ... "--game_data_root does not exist: ..." ...

   Una imagen de disco es un fichero, asi que ni se llegaba al VFS.

2. Runtime::SetupVfs monta game_data_root SIEMPRE con HostPathDevice, que
   espera una carpeta, aunque el SDK trae un DiscImageDevice completo -lee el
   GDFX mapeando la imagen- que no usaba nadie.

3. MappedMemory::Open abre por ruta. En Android eso no vale para la ISO.

Los tres se vieron en el movil, uno detras de otro, en arranques sucesivos.


LO DE ANDROID, QUE ES LO MENOS OBVIO
====================================

La app abre la ISO con el selector del sistema (SAF) y recibe una URI
content://, no una ruta. El primer intento fue pasar /proc/self/fd/N, con el
descriptor ya abierto: es una ruta valida y is_regular_file la acepta... pero
abrirla NO funciona. open() sobre /proc/self/fd/N no duplica el descriptor:
reabre el fichero de verdad por su ruta, y la app no tiene permiso sobre el
almacenamiento compartido. En el log:

    [error] [fs] Disc image could not be mapped

Asi que la URI se pasa tal cual y MappedMemory::Open la reconoce y pide el
descriptor a Java (OpenForAndroidContentUri, del parche Android del SDK, que se
apoya en el metodo openContentFd de la actividad). Ni se copia la ISO ni hace
falta el permiso de "acceso a todos los archivos".

Y como una URI no es una ruta, en SetupVfs hay que saltarse absolute() y
exists(), que la destrozarian.
"""

import argparse
import os
import pathlib
import sys


# ---------------------------------------------------------------------------
#  src/ui/rex_app.cpp
# ---------------------------------------------------------------------------

RAIZ_ANCLA = '''  if (!std::filesystem::is_directory(paths.game_data_root)) {
    auto msg = fmt::format("--game_data_root does not exist: {}", paths.game_data_root.string());
'''

RAIZ_NUEVO = '''  // PARCHE LOCAL - ISO
  //
  // Aqui se exigia un DIRECTORIO. Una imagen de disco es un fichero, y en
  // Android puede llegar como URI content:// del selector del sistema, que no
  // es una ruta del sistema de ficheros.
  std::error_code ec_raiz;
  bool raiz_valida = std::filesystem::is_directory(paths.game_data_root, ec_raiz) ||
                     std::filesystem::is_regular_file(paths.game_data_root, ec_raiz);
#if REX_PLATFORM_ANDROID
  raiz_valida =
      raiz_valida || rex::filesystem::IsAndroidContentUri(paths.game_data_root.string());
#endif
  if (!raiz_valida) {
    auto msg = fmt::format("--game_data_root does not exist: {}", paths.game_data_root.string());
'''


XEX_ANCLA = '''    auto xex_host = paths.game_data_root / host_tail;
    if (!std::filesystem::is_regular_file(xex_host)) {
'''

XEX_NUEVO = '''    // PARCHE LOCAL - ISO
    //
    // Esta comprobacion previa traduce game:\\ a una ruta del host, y eso solo
    // tiene sentido si la raiz es una CARPETA. En una imagen de disco el XEX
    // vive DENTRO, y de resolverlo se encarga el VFS en LoadXexImage, unas
    // lineas mas abajo.
    std::error_code ec_xex;
    const bool raiz_es_carpeta = std::filesystem::is_directory(paths.game_data_root, ec_xex);
    auto xex_host = paths.game_data_root / host_tail;
    if (raiz_es_carpeta && !std::filesystem::is_regular_file(xex_host)) {
'''


# ---------------------------------------------------------------------------
#  src/system/runtime.cpp
# ---------------------------------------------------------------------------

INC_ANCLA = '''#include <rex/filesystem/devices/host_path_device.h>
'''

INC_NUEVO = '''#include <rex/filesystem.h>                            // PARCHE LOCAL - ISO
#include <rex/filesystem/devices/disc_image_device.h>  // PARCHE LOCAL - ISO
#include <rex/filesystem/devices/host_path_device.h>
'''

RUTA_ANCLA = '''  auto abs_game_root = std::filesystem::absolute(game_data_root_);
  if (!std::filesystem::exists(abs_game_root)) {
    REXSYS_ERROR("Runtime::SetupVfs: game_data_root does not exist: {}", abs_game_root.string());
    return false;
  }
'''

RUTA_NUEVO = '''  // PARCHE LOCAL - ISO
  //
  // Una URI content:// de Android NO es una ruta: absolute() le pegaria delante
  // el directorio de trabajo y exists() diria que no esta. Se deja tal cual y se
  // abre mas abajo por el puente de Java.
  bool es_uri_android = false;
#if REX_PLATFORM_ANDROID
  es_uri_android = rex::filesystem::IsAndroidContentUri(game_data_root_.string());
#endif
  auto abs_game_root = game_data_root_;
  if (!es_uri_android) {
    abs_game_root = std::filesystem::absolute(game_data_root_);
    if (!std::filesystem::exists(abs_game_root)) {
      REXSYS_ERROR("Runtime::SetupVfs: game_data_root does not exist: {}", abs_game_root.string());
      return false;
    }
  }
'''

MONTAJE_ANCLA = '''  auto device = std::make_unique<rex::filesystem::HostPathDevice>(
      mount_path, abs_game_root, !REXCVAR_GET(allow_game_relative_writes));
  if (!device->Initialize()) {
    REXSYS_ERROR("Runtime::SetupVfs: Failed to initialize host path device");
    return false;
  }
'''

MONTAJE_NUEVO = '''  // PARCHE LOCAL - ISO
  //
  // Un FICHERO -o una URI content:// en Android- es una imagen de disco y se
  // monta con DiscImageDevice, que el SDK ya traia y nadie usaba. Una carpeta
  // sigue yendo por HostPathDevice, como siempre.
  std::unique_ptr<rex::filesystem::Device> device;
  std::error_code ec_imagen;
  if (es_uri_android || std::filesystem::is_regular_file(abs_game_root, ec_imagen)) {
    REXSYS_INFO("Runtime::SetupVfs: game_data_root es una imagen de disco: {}",
                abs_game_root.string());
    device = std::make_unique<rex::filesystem::DiscImageDevice>(mount_path, abs_game_root);
  } else {
    device = std::make_unique<rex::filesystem::HostPathDevice>(
        mount_path, abs_game_root, !REXCVAR_GET(allow_game_relative_writes));
  }
  if (!device->Initialize()) {
    REXSYS_ERROR("Runtime::SetupVfs: Failed to initialize game data device ({})",
                 abs_game_root.string());
    return false;
  }
'''


# ---------------------------------------------------------------------------
#  src/core/mapped_memory_posix.cpp
# ---------------------------------------------------------------------------

MAPEO_ANCLA = '''  int file_descriptor = open(path.c_str(), open_flags);
  if (file_descriptor < 0) {
    return nullptr;
  }
  return PosixMappedMemory::WrapFileDescriptor(file_descriptor, mode, offset, length);
}
'''

MAPEO_NUEVO = '''  // PARCHE LOCAL - ISO
  //
  // En Android la ISO llega como URI content:// del selector del sistema.
  // Abrirla por ruta no vale -ni siquiera como /proc/self/fd/N, que reabre el
  // fichero de verdad y choca con los permisos del almacenamiento compartido-,
  // asi que el descriptor se le pide a Java.
#if REX_PLATFORM_ANDROID
  if (rex::filesystem::IsAndroidContentUri(path.string())) {
    return OpenForAndroidContentUri(path.string(), mode, offset, length);
  }
#endif
  int file_descriptor = open(path.c_str(), open_flags);
  if (file_descriptor < 0) {
    return nullptr;
  }
  return PosixMappedMemory::WrapFileDescriptor(file_descriptor, mode, offset, length);
}
'''


BLOQUES = [
    ("src/ui/rex_app.cpp", "aceptar un fichero o URI como game_data_root", RAIZ_ANCLA, RAIZ_NUEVO),
    ("src/ui/rex_app.cpp", "no buscar el XEX fuera de la imagen", XEX_ANCLA, XEX_NUEVO),
    ("src/system/runtime.cpp", "cabeceras del VFS", INC_ANCLA, INC_NUEVO),
    ("src/system/runtime.cpp", "no tocar la ruta si es una URI", RUTA_ANCLA, RUTA_NUEVO),
    ("src/system/runtime.cpp", "montar una imagen de disco", MONTAJE_ANCLA, MONTAJE_NUEVO),
    ("src/core/mapped_memory_posix.cpp", "mapear una URI content://", MAPEO_ANCLA, MAPEO_NUEVO),
]


def localizar_sdk():
    raiz = pathlib.Path(__file__).resolve().parent.parent
    # NFSMW_SDK apunta a otro arbol del SDK (el de Android, por ejemplo). Si
    # esta puesta se usa SOLO esa ruta: caer en silencio en el SDK de Windows
    # parchearia el arbol equivocado.
    otro = os.environ.get("NFSMW_SDK")
    candidatos = [pathlib.Path(otro)] if otro else [raiz.parent / "rexglue-sdk", raiz / "sdk"]
    for cand in candidatos:
        if (cand / "src" / "system" / "runtime.cpp").exists():
            return cand
    sys.exit("[ERROR] No encuentro src/system/runtime.cpp del SDK.\n"
             "        Se busca en NFSMW_SDK, o en ..\\rexglue-sdk y .\\sdk")


def leer(f):
    # newline="" para respetar los finales de linea que haya (LF o CRLF).
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
        print(f"  iso                        {puestos} de {len(BLOQUES)} bloques aplicados")
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
            print("[ok] iso: no habia nada puesto")
            return 0
        for f, txt, eol in ficheros.values():
            escribir(f, txt, eol)
        print(f"[ok] Quitados {quitados} bloques")
        return 0

    faltan = [b for b in BLOQUES if b[3] not in ficheros[b[0]][1]]
    if not faltan:
        print(f"[ok] iso: los {len(BLOQUES)} bloques ya estaban")
        return 0

    # Se comprueban TODOS los anclajes antes de escribir nada: un parche a
    # medias entre tres ficheros es peor que uno que no entra.
    for ruta, nombre, ancla, _ in faltan:
        n = ficheros[ruta][1].count(ancla)
        if n != 1:
            sys.exit(f"[ERROR] El anclaje de '{nombre}' aparece {n} veces en {ruta}, "
                     f"esperaba 1. Puede que este SDK ya monte ISOs. No he tocado nada.")

    for ruta, nombre, ancla, nuevo in faltan:
        ficheros[ruta][1] = ficheros[ruta][1].replace(ancla, nuevo)
        print(f"[ok] Aplicado: {nombre}")

    for f, txt, eol in ficheros.values():
        escribir(f, txt, eol)
    return 0


if __name__ == "__main__":
    sys.exit(main())
