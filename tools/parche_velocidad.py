#!/usr/bin/env python3
"""
Anade un ajuste de velocidad del juego, en porcentaje, movible desde F4.

    python tools/parche_velocidad.py            aplicar
    python tools/parche_velocidad.py --estado
    python tools/parche_velocidad.py --revertir

Toca un fichero del SDK:  src/system/runtime.cpp

No guarda .original y no le hace falta: aplica y deshace por sustitucion de
texto exacta, bloque a bloque. Es a proposito: runtime.cpp YA lleva otro
parche encima, y guardar ahi un ".original" a estas alturas guardaria el
fichero ya parcheado como si fuera el limpio; de paso, un --revertir se
llevaria por delante el parche del otro.

Y va bloque a bloque en vez de con una marca global POR UN FALLO QUE YA PASO
en el parche hermano: con una sola marca, cambiar el contenido del parche no
servia de nada -encontraba la marca de la version anterior, decia "ya estaba"
y no tocaba nada-. Aqui ademas hay migracion: si detecta la version vieja del
propio parche, la quita antes de poner la nueva.


PRIMERO, LA PREGUNTA: LAS ANIMACIONES VAN CON LOS FPS?
======================================================

No. Y se puede comprobar leyendo el SDK, en src/graphics/graphics_system.cpp:

    // Guest vblank timer based on the configured guest video mode.
    ...
    double refresh_rate_hz = video_mode.refresh_rate;         // 60 por defecto
    uint64_t vsync_interval_ticks = guest_tick_frequency / refresh_rate_hz;
    while (vsync_worker_running_) {
      uint64_t current_time = Clock::QueryGuestTickCount();
      while (current_time - last_frame_time >= interval_ticks) {
        MarkVblank();
        last_frame_time += interval_ticks;
      }
      Sleep(1ms);
    }

El parpadeo vertical -el latido al que el juego mide el tiempo- lo genera un
HILO APARTE con un reloj de pared, no el bucle de dibujado. A 18 fps el juego
sigue recibiendo sus 60 avisos por segundo; lo unico que pasa es que se
dibujan menos fotogramas. Limitar a 30 fps NO ralentiza el juego.

UNA TRAMPA QUE SI IMPORTA, Y ESTA EN LA MISMA FUNCION:

    uint64_t no_vsync_interval_ticks = guest_tick_frequency / 1000;
    interval_ticks = vsync ? vsync_interval_ticks : no_vsync_interval_ticks;

Con vsync APAGADO el aviso pasa a 1000 por segundo en vez de 60. Es a
proposito -asi el juego no se queda esperando al parpadeo-, pero si el juego
contase el tiempo por esos avisos en vez de por el reloj, con vsync apagado
iria disparado. Merece la pena mirarlo, porque las pruebas de rendimiento las
estamos haciendo justo asi.


QUE ANADE ESTE PARCHE
=====================

Un cvar  game_speed  EN PORCENTAJE: 100 es normal, 50 la mitad, 200 el doble.

En porcentaje y no en multiplicador porque en la ventana de F4 sale un numero
pelado y "1.0" no dice de que; escribir "100" ahi era lo natural, y con el
rango de multiplicador -0.05 a 4.0- eso se recortaba al maximo y el ajuste se
quedaba clavado en 4. Ademas 0..200 es un recorrido comodo para una barra.

No lo inventa: el SDK ya trae Clock::set_guest_time_scalar(), que escala el
reloj del guest entero -el contador de ticks, la hora del sistema, los
temporizadores y las esperas-. Estaba fijado a 1.0 y sin forma de tocarlo.
Como el hilo del parpadeo compara ticks del guest, ese tambien se ajusta solo:
no hay nada que pueda quedarse desincronizado.

Y se puede mover en marcha. El SDK tiene RegisterChangeCallback para eso -ya
lo usa para el modo pantalla completa-, asi que en cuanto mueves la barra en
F4 se aplica, sin reiniciar.

OJO CON LO QUE ES Y LO QUE NO ES:

  - limitar los fps  = cuantas veces se DIBUJA por segundo
  - game_speed       = a que velocidad PASA EL TIEMPO dentro del juego

Son cosas distintas. Esto no da rendimiento: bajarlo hace que el juego vaya a
camara lenta, no que vaya mas fino.
"""

import argparse
import os
import pathlib
import sys

# ---------------------------------------------------------------------------
#  1) Cabeceras
# ---------------------------------------------------------------------------

CAB_ANCLA = """#include <rex/chrono/clock.h>
#include <rex/cvar.h>
"""

CAB_NUEVO = """#include <algorithm>  // PARCHE LOCAL - std::max, para el suelo de la velocidad

#include <rex/chrono/clock.h>
#include <rex/cvar.h>
"""

# ---------------------------------------------------------------------------
#  2) El cvar y la funcion que lo aplica
# ---------------------------------------------------------------------------

CVAR_ANCLA = """REXCVAR_DEFINE_STRING(metadata_root, "", "Runtime", "Override metadata path");
"""

CVAR_NUEVO = """REXCVAR_DEFINE_STRING(metadata_root, "", "Runtime", "Override metadata path");

// PARCHE LOCAL - velocidad del juego ajustable
//
// Velocidad a la que pasa el tiempo DENTRO del juego, EN PORCENTAJE: 100 es
// normal, 50 la mitad, 200 el doble. No tiene nada que ver con el limite de
// fps: los fps son cuantas veces se dibuja, esto es a que ritmo avanza.
//
// En porcentaje y no en multiplicador porque en la ventana de F4 sale un
// numero pelado, y "1.0" no dice de que. Ademas 0..200 es un recorrido comodo
// para una barra; 0.05..4.0 se apelotonaba todo a la izquierda.
//
// El texto va en ingles porque es lo que sale en esa ventana, que es del SDK
// y esta entera en ingles.
REXCVAR_DEFINE_DOUBLE(game_speed, 100.0, "Runtime",
                      "Speed of in-game time, as a percentage. 100 = normal, 50 = half, "
                      "200 = double. This is not an fps limit: it changes how fast time "
                      "passes in the game, not how often it is drawn.")
    .range(0.0, 200.0)
    .lifecycle(rex::cvar::Lifecycle::kHotReload);

namespace {

// PARCHE LOCAL - velocidad del juego ajustable
//
// Pasa el porcentaje a la escala que espera el reloj, con un SUELO. El suelo
// no es capricho: en src/core/clock.cpp, RecomputeGuestTickScalar hace esto
// cuando la escala es <= 1.0
//
//     frac.second *= static_cast<uint64_t>(10.0 / guest_time_scalar_);
//
// Con la escala a cero eso es 10.0/0.0 = infinito, y convertir infinito a
// uint64_t es comportamiento indefinido; en la practica sale 0 o un numero
// enorme. Si sale 0, la division de UpdateGuestClock revienta. O sea que un
// 0% literal no cuelga el juego: lo tumba.
//
// Asi que el 0% de la barra se queda en una milesima de la velocidad normal.
// A ese ritmo el juego esta parado a todos los efectos -un segundo suyo son
// mas de dieciseis minutos- pero el reloj sigue siendo un numero valido.
void aplicar_velocidad_del_juego() {
  const double por_ciento = REXCVAR_GET(game_speed);
  const double escala = std::max(por_ciento, 0.1) / 100.0;
  rex::chrono::Clock::set_guest_time_scalar(escala);
  REXSYS_INFO("[velocidad] el tiempo del juego pasa al {:.0f}% (escala x{:.3f})", por_ciento,
              escala);
}

}  // namespace
"""

# ---------------------------------------------------------------------------
#  3) Aplicarlo al arrancar, y engancharlo al cambio en caliente
# ---------------------------------------------------------------------------

RELOJ_ANCLA = """  chrono::Clock::set_guest_tick_frequency(50000000);
  chrono::Clock::set_guest_system_time_base(chrono::Clock::QueryHostSystemTime());
  chrono::Clock::set_guest_time_scalar(1.0);
"""

RELOJ_NUEVO = """  chrono::Clock::set_guest_tick_frequency(50000000);
  chrono::Clock::set_guest_system_time_base(chrono::Clock::QueryHostSystemTime());

  // PARCHE LOCAL - velocidad del juego ajustable
  //
  // set_guest_time_scalar escala el reloj del guest ENTERO: el contador de
  // ticks, la hora del sistema, los temporizadores y las esperas. Por eso vale
  // como mando de velocidad y no hace falta tocar nada mas: el hilo que genera
  // el parpadeo vertical compara ticks del guest, asi que se ajusta solo y no
  // queda nada desincronizado.
  //
  // Antes esto era un 1.0 fijo.
  aplicar_velocidad_del_juego();

  // Y para poder moverlo desde F4 sin reiniciar. El aviso llega DESPUES de que
  // el valor nuevo este puesto -asi lo hace SetFlagFromSource-, o sea que
  // REXCVAR_GET dentro ya devuelve el nuevo y no el anterior.
  rex::cvar::RegisterChangeCallback(
      "game_speed", [](std::string_view, std::string_view) { aplicar_velocidad_del_juego(); });
"""

BLOQUES = [
    ("cabeceras", CAB_ANCLA, CAB_NUEVO),
    ("el cvar y su funcion", CVAR_ANCLA, CVAR_NUEVO),
    ("arranque del reloj", RELOJ_ANCLA, RELOJ_NUEVO),
]

# ---------------------------------------------------------------------------
#  Version anterior de ESTE parche, para poder migrar
#
#  La v1 definia game_speed como MULTIPLICADOR (1.0, rango 0.05..4.0) y llamaba
#  al reloj directamente, sin funcion auxiliar. Si sigue puesta hay que
#  quitarla antes, o los anclajes de arriba no encajan: su sitio esta ocupado.
# ---------------------------------------------------------------------------

VIEJO_CVAR = """REXCVAR_DEFINE_STRING(metadata_root, "", "Runtime", "Override metadata path");

// PARCHE LOCAL - velocidad del juego ajustable
//
// Multiplica la velocidad a la que pasa el tiempo DENTRO del juego. No tiene
// nada que ver con el limite de fps: los fps son cuantas veces se dibuja, esto
// es a que ritmo avanza el juego.
//
// El texto va en ingles porque es lo que sale en la ventana de F4, que es del
// SDK y esta entera en ingles.
REXCVAR_DEFINE_DOUBLE(game_speed, 1.0, "Runtime",
                      "Speed of in-game time. 1.0 = normal, 0.5 = half, 2.0 = double. "
                      "This is not an fps limit: it changes how fast time passes in the "
                      "game, not how often it is drawn.")
    .range(0.05, 4.0)
    .lifecycle(rex::cvar::Lifecycle::kHotReload);
"""

VIEJO_RELOJ = """  chrono::Clock::set_guest_tick_frequency(50000000);
  chrono::Clock::set_guest_system_time_base(chrono::Clock::QueryHostSystemTime());

  // PARCHE LOCAL - velocidad del juego ajustable
  //
  // set_guest_time_scalar escala el reloj del guest ENTERO: el contador de
  // ticks, la hora del sistema, los temporizadores y las esperas. Por eso vale
  // como mando de velocidad y no hace falta tocar nada mas: el hilo que genera
  // el parpadeo vertical compara ticks del guest, asi que se ajusta solo y no
  // queda nada desincronizado.
  //
  // Antes esto era un 1.0 fijo.
  chrono::Clock::set_guest_time_scalar(REXCVAR_GET(game_speed));

  // Y para poder moverlo desde F4 sin reiniciar. El aviso llega DESPUES de que
  // el valor nuevo este puesto -asi lo hace SetFlagFromSource-, o sea que
  // REXCVAR_GET aqui dentro ya devuelve el nuevo y no el anterior.
  rex::cvar::RegisterChangeCallback("game_speed", [](std::string_view, std::string_view) {
    const double escala = REXCVAR_GET(game_speed);
    chrono::Clock::set_guest_time_scalar(escala);
    REXSYS_INFO("[velocidad] el tiempo del juego pasa a x{:.2f}", escala);
  });
"""

VIEJOS = [
    # (nombre, huella que SOLO aparece en esa version, bloque entero, anclaje)
    ("cvar de la v1 (multiplicador)",
     'REXCVAR_DEFINE_DOUBLE(game_speed, 1.0, "Runtime",', VIEJO_CVAR, CVAR_ANCLA),
    ("reloj de la v1 (sin funcion auxiliar)",
     'chrono::Clock::set_guest_time_scalar(REXCVAR_GET(game_speed));', VIEJO_RELOJ, RELOJ_ANCLA),
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
             "        Se busca en ..\\rexglue-sdk y en .\\sdk")


def quitar_version_vieja(txt):
    """Quita los restos de una version anterior de este mismo parche.

    EL PROBLEMA, QUE ME COSTO TRES INTENTOS
    ---------------------------------------
    Un bloque viejo y el de ahora pueden solaparse de dos maneras, y cada una
    rompe la solucion obvia de la otra:

      * EL VIEJO ES UN TROZO DEL DE AHORA (al bloque se le anadio codigo).
        Buscar el viejo lo encuentra DENTRO del bueno, y sustituirlo por el
        anclaje le corta la cabeza al bloque recien puesto. Luego se vuelve a
        aplicar y queda la cola DUPLICADA. El fichero crecia cada pasada.

      * EL DE AHORA ES UN TROZO DEL VIEJO (al bloque se le quito codigo).
        Entonces "el bloque bueno esta" da que si aunque lo que hay siga
        siendo el viejo entero, y el script se da por aplicado dejando dentro
        codigo muerto.

    Intente resolverlo con una HUELLA por version -un trozo que solo estuviera
    en esa version-. No siempre existe: cuando el viejo es prefijo exacto del
    nuevo, TODO lo que hay en el viejo esta tambien en el nuevo.

    LA REGLA QUE SI VALE, Y NO NECESITA HUELLAS
    -------------------------------------------
    Encontrar el bloque viejo solo cuenta si NO puede ser el bueno visto a
    medias:

        es_de_verdad_vieja = (viejo in txt) and
                             (viejo not in nuevo or nuevo not in txt)

    Los dos casos de arriba salen bien con eso, y se comprueba solo con los
    textos, sin que yo tenga que acertar a mano con ninguna huella.

    VIEJOS sigue yendo DE MAS NUEVO A MAS VIEJO, y en cuanto una version
    encaja para un anclaje las demas de ese anclaje se saltan: si la v2 es la
    v1 con cosas anadidas, mirar la v1 primero dejaria huerfana la cola de la
    v2. Eso tambien paso.

    Y esto se prueba corriendo el parche DOS VECES seguidas sobre el fichero
    de verdad y comparando. El fallo del duplicado no se ve en la primera
    pasada, que es la unica que se suele mirar.
    """
    ahora = {ancla: nuevo for _, ancla, nuevo in BLOQUES}
    quitados = 0
    anclajes_hechos = set()
    for nombre, huella, viejo, ancla in VIEJOS:
        if ancla in anclajes_hechos:
            continue
        nuevo = ahora[ancla]
        if viejo not in txt:
            # La huella solo se usa para avisar: si asoma un trozo de esa
            # version pero el bloque entero no cuadra, alguien lo ha editado a
            # mano y prefiero no adivinar.
            if huella in txt and nuevo not in txt:
                print(f"[aviso] Veo restos de '{nombre}' pero no en la forma que esperaba.")
                print(f"        Lo dejo estar; miralo a mano si algo va raro.")
            continue
        if viejo in nuevo and nuevo in txt:
            # No es una version vieja: es el bloque de ahora, que contiene al
            # viejo dentro. Este anclaje ya esta al dia.
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

    f = localizar_sdk() / "src" / "system" / "runtime.cpp"
    txt = f.read_text(encoding="utf-8")

    if args.estado:
        puestos = sum(1 for _, _, nuevo in BLOQUES if nuevo in txt)
        print(f"  {f.name:26s} {puestos} de {len(BLOQUES)} bloques aplicados")
        for nombre, _, nuevo in BLOQUES:
            print(f"      {'si' if nuevo in txt else 'NO':>2}  {nombre}")
        # Con la misma regla que usa la migracion, para que --estado no avise
        # de restos que en realidad son trozos del bloque bueno.
        ahora = {ancla: nuevo for _, ancla, nuevo in BLOQUES}
        viejos = sum(1 for _, _, viejo, ancla in VIEJOS
                     if viejo in txt
                     and (viejo not in ahora[ancla] or ahora[ancla] not in txt))
        if viejos:
            print(f"      -- quedan {viejos} bloques de la version anterior")
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
                     f"        El SDK habra cambiado, o quedan restos de una version\n"
                     f"        anterior que no reconozco. No he tocado nada.")

    for nombre, ancla, nuevo in faltan:
        txt = txt.replace(ancla, nuevo)
        print(f"[ok] Aplicado: {nombre}")
    f.write_text(txt, encoding="utf-8")
    print()
    print("  En F4, categoria Runtime, ajuste  game_speed  (0 a 200 %)")
    print()
    print("  HAY QUE RECOMPILAR EL SDK para que sirva de algo:")
    print("    cmake --build out/build/win-amd64 --config Release --target install")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
