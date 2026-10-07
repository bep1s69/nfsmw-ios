#!/usr/bin/env python3
"""
Deja conceder los privilegios de Xbox Live, para poder entrar al multijugador.

    python tools/parche_privilegios.py            aplicar
    python tools/parche_privilegios.py --estado
    python tools/parche_privilegios.py --revertir

Toca un fichero del SDK:  src/kernel/xam/xam_user.cpp

No guarda .original: aplica y deshace por sustitucion de texto exacta, bloque a
bloque, como los demas parches de este proyecto.


DE DONDE SALE ESTO
==================

Al entrar al multijugador, el juego saca este cartel:

    ATENCION
    Los privilegios que tienes en Xbox Live no te permiten acceder a esta
    funcion.

No es un fallo ni un cuelgue: es un NO limpio, y llega mucho antes de que se
toque la red. El juego pregunta por sus privilegios y se le contesta que no
tiene ninguno.

La respuesta esta en xam_user.cpp, y el comentario original no deja lugar a
dudas:

    u32 XamUserCheckPrivilege_entry(u32 user_index, u32 mask, mapped_u32 out_value) {
      ...
      // If we deny everything, games should hopefully not try to do stuff.
      *out_value = 0;
      return X_ERROR_SUCCESS;
    }

Deniega TODOS los privilegios, siempre, sea cual sea el que se pregunte. Viene
de Xenia y para un emulador sin Xbox Live tiene su logica: si el juego se cree
sin permisos, ni lo intenta, y te ahorras que se cuelgue contra unos servidores
que llevan años apagados.

Lo raro es que el resto del SDK dice justo lo contrario:

    XamUserIsOnlineEnabled   -> 1        (hay conexion)
    XamUserGetMembershipTier -> 6        (que es Gold)
    user_profile.signin_state -> 1       (hay sesion iniciada)
    user_profile.type         -> 1 | 2   (perfil local y online)

O sea que la unica pieza que dice que no es esta. El perfil esta montado, la
sesion iniciada y la membresia es Gold; solo faltan los permisos.


LO QUE ESTO NO ARREGLA, QUE ES LO IMPORTANTE
============================================

Esto abre la PUERTA del menu. No hace que el multijugador funcione. Detras
sigue faltando media capa de red, y conviene saberlo antes de probar para no
llevarse un chasco:

  - De las 158 funciones de red que declara la tabla de ordinales del SDK, 114
    no tienen implementacion. Entre ellas estan justo las del System Link:

        0x36  XNetCreateKey          0x41  XNetConnect
        0x37  XNetRegisterKey        0x42  XNetGetConnectStatus
        0x38  XNetUnregisterKey      0x53  XNetGetSystemLinkPort
        0x3F  XNetUnregisterInAddr   0x09  getsockname

    Ese trio CreateKey/RegisterKey/UnregisterKey es el que asocia la XNKID y
    la XNKEY de la partida; XNetConnect y XNetGetConnectStatus son los que
    levantan el enlace con el otro equipo.

  - Los manejadores de sesion de xam/apps/xgi_app.cpp son de adorno: leen los
    parametros, los escriben en el log y devuelven X_E_SUCCESS sin hacer nada.
    XSessionSearch ni siquiera toca el buffer de resultados, asi que un cliente
    buscando partidas siempre encontrara cero.

Asi que la utilidad de este parche es AVERIGUAR DONDE ESTA EL SIGUIENTE MURO.
Con el puesto, el menu deberia dejarte pasar, y lo que salga en el log a partir
de ahi dice que necesita este juego en concreto, que puede ser bastante menos
de lo que falta en total.


VIENE APAGADO
=============

El ajuste nuevo es  grant_user_privileges  y por defecto esta en false, o sea
que el comportamiento no cambia hasta que tu lo enciendas. Se lee en CADA
llamada, asi que se puede encender desde el menu de F4 sin reiniciar el juego:
lo enciendes, sales del menu del multijugador y vuelves a entrar.

Si al concederlos el juego se pone a intentar cosas de Xbox Live y se cuelga,
apagalo y vuelves a estar como antes. Por eso es un interruptor y no un cambio
fijo.
"""

import argparse
import os
import pathlib
import sys


# ---------------------------------------------------------------------------
#  Bloque 1: el ajuste
# ---------------------------------------------------------------------------

CVAR_ANCLA = '''REXCVAR_DEFINE_UINT32(user_language, 1, "Kernel", "User's language ID");
'''

CVAR_NUEVO = '''REXCVAR_DEFINE_UINT32(user_language, 1, "Kernel", "User's language ID");

// PARCHE LOCAL - privilegios de Xbox Live
//
// Apagado por defecto: encendido cambia lo que el juego cree poder hacer, y eso
// merece ser una decision y no una sorpresa.
//
// kHotReload y no kRequiresRestart porque XamUserCheckPrivilege lo lee en cada
// llamada. Se puede encender desde F4 con el juego abierto; basta con salir del
// menu que dio el aviso y volver a entrar.
//
// El texto va en ingles porque es lo que sale en la ventana de F4, que es del
// SDK y esta entera en ingles.
REXCVAR_DEFINE_BOOL(grant_user_privileges, false, "Kernel",
                    "Tell the game it has every Xbox Live privilege. Off by default, which "
                    "makes the game refuse to open its multiplayer menus. Turning it on only "
                    "opens the door: system link also needs the XNet layer, which is only "
                    "half implemented here.")
    .lifecycle(rex::cvar::Lifecycle::kHotReload);
'''


# ---------------------------------------------------------------------------
#  Bloque 2: la respuesta
# ---------------------------------------------------------------------------

CHEQUEO_ANCLA = '''  // If we deny everything, games should hopefully not try to do stuff.
  *out_value = 0;
  return X_ERROR_SUCCESS;
}
'''

CHEQUEO_NUEVO = '''  // PARCHE LOCAL - privilegios de Xbox Live
  //
  // Aqui decia esto, y hacia exactamente lo que dice:
  //
  //     // If we deny everything, games should hopefully not try to do stuff.
  //     *out_value = 0;
  //
  // Deniega todos los privilegios, siempre, sea cual sea el que pregunten. Es
  // de Xenia y para un emulador sin Xbox Live se entiende: si el juego se cree
  // sin permisos ni lo intenta, y no se cuelga contra servidores apagados.
  //
  // En Most Wanted el efecto es el cartel "Los privilegios que tienes en Xbox
  // Live no te permiten acceder a esta funcion" nada mas tocar el multijugador.
  // Que ademas se contradice con el resto del SDK: XamUserIsOnlineEnabled
  // devuelve 1, XamUserGetMembershipTier devuelve 6 -que es Gold- y el perfil
  // dice signin_state 1 y type local|online. El unico que decia que no era este.
  //
  // OJO CON LO QUE ESTO NO HACE. Abre la puerta del menu y nada mas. El System
  // Link de detras necesita la capa XNet, y en este SDK faltan XNetCreateKey,
  // XNetRegisterKey, XNetUnregisterKey, XNetConnect y XNetGetConnectStatus,
  // ademas de que los manejadores de sesion de xgi_app.cpp devuelven exito sin
  // hacer nada. Esto sirve para ver donde esta el siguiente muro, no para
  // jugar en red.
  *out_value = REXCVAR_GET(grant_user_privileges) ? 1 : 0;
  return X_ERROR_SUCCESS;
}
'''


BLOQUES = [
    ("el ajuste grant_user_privileges", CVAR_ANCLA, CVAR_NUEVO),
    ("la respuesta de XamUserCheckPrivilege", CHEQUEO_ANCLA, CHEQUEO_NUEVO),
]


# Todavia no ha habido ninguna version anterior de este parche. La lista existe
# para que la maquinaria de migracion sea la misma que en los demas scripts: el
# dia que haya una v2, se anade aqui y ya funciona.
VIEJOS = []


def localizar_sdk():
    raiz = pathlib.Path(__file__).resolve().parent.parent
    # NFSMW_SDK apunta a otro arbol del SDK (el de Android, por ejemplo). Si
    # esta puesta se usa SOLO esa ruta: caer en silencio en el SDK de Windows
    # parchearia el arbol equivocado.
    otro = os.environ.get("NFSMW_SDK")
    candidatos = [pathlib.Path(otro)] if otro else [raiz.parent / "rexglue-sdk", raiz / "sdk"]
    for cand in candidatos:
        if (cand / "src" / "kernel" / "xam" / "xam_user.cpp").exists():
            return cand
    sys.exit("[ERROR] No encuentro src/kernel/xam/xam_user.cpp del SDK.\n"
             "        Se busca en ..\\rexglue-sdk y en .\\sdk")


def quitar_version_vieja(txt):
    """Quita los restos de una version anterior de este mismo parche.

    Misma regla que en los otros parches del proyecto: encontrar el bloque
    viejo solo cuenta si NO puede ser el bueno visto a medias.

        es_de_verdad_vieja = (viejo in txt) and
                             (viejo not in nuevo or nuevo not in txt)

    Ver parche_backend.py, donde esta contado entero y donde costo tres
    intentos dar con ella.
    """
    ahora = {ancla: nuevo for _, ancla, nuevo in BLOQUES}
    quitados = 0
    anclajes_hechos = set()
    for nombre, huella, viejo, ancla in VIEJOS:
        if ancla in anclajes_hechos:
            continue
        nuevo = ahora[ancla]
        if viejo not in txt:
            if huella in txt and nuevo not in txt:
                print(f"[aviso] Veo restos de '{nombre}' pero no en la forma que esperaba.")
                print(f"        Lo dejo estar; miralo a mano si algo va raro.")
            continue
        if viejo in nuevo and nuevo in txt:
            anclajes_hechos.add(ancla)
            continue
        txt = txt.replace(viejo, ancla)
        anclajes_hechos.add(ancla)
        print(f"[ok] Quitada la version anterior: {nombre}")
        quitados += 1
    return txt, quitados


def main():
    p = argparse.ArgumentParser(add_help=True)
    p.add_argument("--estado", action="store_true")
    p.add_argument("--revertir", action="store_true")
    args = p.parse_args()

    f = localizar_sdk() / "src" / "kernel" / "xam" / "xam_user.cpp"
    txt = f.read_text(encoding="utf-8")

    if args.estado:
        puestos = sum(1 for _, _, nuevo in BLOQUES if nuevo in txt)
        print(f"  {f.name:26s} {puestos} de {len(BLOQUES)} bloques aplicados")
        for nombre, _, nuevo in BLOQUES:
            print(f"      {'si' if nuevo in txt else 'NO':>2}  {nombre}")
        return 0

    if args.revertir:
        quitados = 0
        for nombre, ancla, nuevo in BLOQUES:
            if nuevo not in txt:
                continue
            if txt.count(nuevo) != 1:
                sys.exit(f"[ERROR] El bloque '{nombre}' aparece {txt.count(nuevo)} veces.\n"
                         f"        No lo toco, quitalo tu.")
            txt = txt.replace(nuevo, ancla)
            quitados += 1
        txt, viejos = quitar_version_vieja(txt)
        quitados += viejos
        if not quitados:
            print(f"[ok] {f.name}: no habia nada puesto")
            return 0
        f.write_text(txt, encoding="utf-8")
        print(f"[ok] Quitados {quitados} bloques de {f.name}")
        print()
        print("  HAY QUE RECOMPILAR EL SDK.")
        return 0

    txt, _ = quitar_version_vieja(txt)

    faltan = [(n, a, v) for n, a, v in BLOQUES if v not in txt]
    if not faltan:
        print(f"[ok] {f.name}: los {len(BLOQUES)} bloques ya estaban")
        return 0

    for nombre, ancla, _ in faltan:
        n = txt.count(ancla)
        if n != 1:
            sys.exit(f"[ERROR] El anclaje de '{nombre}' aparece {n} veces, esperaba 1.\n"
                     f"        El SDK habra cambiado. No he tocado nada.")

    for nombre, ancla, nuevo in faltan:
        txt = txt.replace(ancla, nuevo)
        print(f"[ok] Aplicado: {nombre}")

    f.write_text(txt, encoding="utf-8")
    print()
    print("  En F4, categoria Kernel, ajuste  grant_user_privileges")
    print("  Viene APAGADO. Encendido, el juego se cree con todos los permisos.")
    print()
    print("  HAY QUE RECOMPILAR EL SDK:")
    print("    cmake --build out/build/win-amd64 --config Release --target install")
    return 0


if __name__ == "__main__":
    sys.exit(main())
