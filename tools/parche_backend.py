#!/usr/bin/env python3
"""
Anade un selector de API grafica: D3D12 o Vulkan, elegible desde F4.

    python tools/parche_backend.py            aplicar
    python tools/parche_backend.py --estado
    python tools/parche_backend.py --revertir

Toca un fichero del SDK:  src/ui/rex_app.cpp

No guarda .original: aplica y deshace por sustitucion de texto exacta, bloque
a bloque, como los otros parches de este proyecto.

OJO: esto solo anade el AJUSTE. Para que la opcion "vulkan" sirva de algo, el
SDK tiene que estar compilado con el backend de Vulkan dentro:

    cmake --preset win-amd64 -DREXGLUE_USE_VULKAN=ON

DIST.bat y PARCHE_ARRANQUE.bat ya lo hacen. Y si no esta compilado, elegir
vulkan no deja el juego sin arrancar: se cae a la otra API, lo dice en el log
y sigue.


DIRECTX 11 NO ESTA, Y NO ES UN OLVIDO
=====================================

La pregunta de la que sale esto era si se podia usar DX11 en vez de DX12 para
ganar rendimiento. No: este SDK solo tiene dos backends, y lo dice su CMake.

    option(REXGLUE_USE_D3D12  "Enable D3D12 graphics backend" ON)
    option(REXGLUE_USE_VULKAN "Enable Vulkan graphics backend" OFF)

Y no es casualidad. La emulacion de la Xenos se apoya en cosas de la
generacion de DX12: los rasterizer ordered views del camino ROV, los
descriptores sin limite, las escrituras tipadas desde shaders para el
memexport. Un backend de DX11 no es un ajuste, es rehacer el plugin de GPU.

Ademas no habria arreglado nada: el cuello esta en la GPU -100% de uso, con la
CPU sin saturar-, y la API no cambia cuantos pixeles hay que sombrear. Donde
DX11 gana a veces es cuando el cuello es enviar ordenes de dibujo desde la
CPU, que no es el caso.


LO QUE SI SE PUEDE, Y ES ESTO
=============================

El plugin ya sabe elegir backend por nombre. Esta en src/graphics/plugin_main.cpp:

    std::string_view backend = info->backend ? info->backend : "any";
    if (backend == "any" || backend == "d3d12")  return new D3D12GraphicsSystem();
    if (backend == "any" || backend == "vulkan") return new VulkanGraphicsSystem();

Y LoadGpuPlugin acepta ese nombre como segundo parametro. Lo unico que faltaba
era que alguien se lo pasara: rex_app.cpp llamaba con un solo argumento, asi
que siempre salia "any", que en la practica es D3D12 por ser el primero.

El backend de Vulkan esta entero en el codigo -alrededor de un mega de fuentes
en src/graphics/vulkan- y todo lo que necesita viene ya con el SDK:
vulkan-headers, vulkan-loader, vulkan-memory-allocator, glslang y spirv-tools.
No hay que instalar nada aparte.


QUE ESPERAR
===========

Ni idea, y no te lo voy a adornar. En una Intel de esta generacion el driver
de Vulkan es un camino completamente distinto al de D3D12, y puede ir mejor o
peor. Lo que si es cierto es que el backend de Vulkan de este SDK esta menos
rodado que el de D3D12: si sale con fallos graficos o no arranca, se vuelve a
d3d12 y no se ha perdido mas que el rato de compilar.

UN FALLO DE LA PRIMERA VERSION, PARA QUE CONSTE
==============================================

La v1 marcaba el ajuste como kInitOnly, copiando lo que hacia gpu_plugin. En
el menu salia en rojo y deshabilitado: se veia, y no se podia tocar. Mal.

kInitOnly quiere decir "ni siquiera se puede guardar el valor nuevo", y el
propio SDK rechaza escribirlo una vez arrancado. Pero aqui el valor SI se
puede guardar; lo que no se puede es aplicarlo con el juego abierto. Eso es
kRequiresRestart, que ademas hace que el SDK lo apunte en una lista de cambios
pendientes que ya existia -GetPendingRestartFlags- y que nadie ensenaba. El
parche del menu la ensena ahora, con un boton para reiniciar.

Y de paso se quito "any" de las opciones: con any no habia forma de saber cual
estaba puesta de verdad, que era justo lo que hacia falta ver.
"""

import argparse
import os
import pathlib
import sys

# ---------------------------------------------------------------------------
#  1) El cvar, al lado del de gpu_plugin
# ---------------------------------------------------------------------------

CVAR_ANCLA = """REXCVAR_DEFINE_STRING(gpu_plugin, "", "GPU",
                      "GPU emulation plugin to load at startup (e.g. 'xenos'); empty disables "
                      "GPU emulation")
    .lifecycle(rex::cvar::Lifecycle::kInitOnly);
"""

CVAR_NUEVO = """REXCVAR_DEFINE_STRING(gpu_plugin, "", "GPU",
                      "GPU emulation plugin to load at startup (e.g. 'xenos'); empty disables "
                      "GPU emulation")
    .lifecycle(rex::cvar::Lifecycle::kInitOnly);

// PARCHE LOCAL - selector de API grafica
//
// El plugin ya sabia elegir entre D3D12 y Vulkan por nombre; lo que faltaba
// era que alguien se lo dijera. Ver plugin_main.cpp:
//
//     if (backend == "any" || backend == "d3d12")  -> D3D12GraphicsSystem
//     if (backend == "any" || backend == "vulkan") -> VulkanGraphicsSystem
//
// "any" coge el primero que este compilado, que es D3D12. Con esto se puede
// forzar uno concreto y comparar.
//
// PIDE REINICIO, PERO NO ES DE SOLO LECTURA. La primera version lo puse como
// kInitOnly, igual que gpu_plugin, y el menu de F4 lo pintaba en rojo y
// deshabilitado: se veia pero no se podia tocar. Es que kInitOnly significa
// "no se puede ni guardar el valor nuevo", y aqui si se puede: lo que no se
// puede es aplicarlo sin reiniciar. Eso es kRequiresRestart, que ademas hace
// que el SDK lo apunte en su lista de cambios pendientes -y el menu la
// ensena, con un boton para reiniciar-.
//
// Y ya no hay "any". Con any no se sabia cual estaba puesta de verdad, que era
// justo lo que habia que ensenar. Con dos opciones y ambas explicitas, el
// ajuste ES la respuesta a "cual se esta usando".
//
// El texto va en ingles porque es lo que sale en esa ventana, que es del SDK
// y esta entera en ingles.
REXCVAR_DEFINE_STRING(gpu_backend, "d3d12", "GPU",
                      "Graphics API: d3d12 or vulkan. Takes effect on restart. If the one "
                      "you pick was not built into this copy, the game falls back to the "
                      "other one and says so in the log.")
    .allowed({"d3d12", "vulkan"})
    .lifecycle(rex::cvar::Lifecycle::kRequiresRestart);

"""

# ---------------------------------------------------------------------------
#  2) Pasarselo al cargador
# ---------------------------------------------------------------------------

CARGA_ANCLA = """  if (!config_.graphics && !config_.gpu_plugin.empty()) {
    config_.graphics = rex::system::LoadGpuPlugin(config_.gpu_plugin);
"""

CARGA_NUEVO = """  if (!config_.graphics && !config_.gpu_plugin.empty()) {
    // PARCHE LOCAL - selector de API grafica
    //
    // Antes se llamaba con un solo argumento, asi que el backend quedaba en
    // "any" por defecto y siempre salia D3D12 por ser el primero del if. El
    // segundo parametro ya existia en LoadGpuPlugin; solo faltaba usarlo.
    const std::string backend_elegido = REXCVAR_GET(gpu_backend);
    REXLOG_INFO("API grafica pedida: {}", backend_elegido);
    config_.graphics = rex::system::LoadGpuPlugin(config_.gpu_plugin, backend_elegido);

    // Si la que se ha pedido no esta compilada en esta copia, el plugin
    // devuelve nada. Antes de eso significaba pantalla de error y a editar el
    // toml a mano; ahora se cae a la otra y se dice bien claro. Como solo hay
    // dos, "any" es exactamente la otra.
    if (!config_.graphics) {
      REXLOG_WARN("La API grafica '{}' no esta compilada en esta copia. Se prueba con la otra.",
                  backend_elegido);
      config_.graphics = rex::system::LoadGpuPlugin(config_.gpu_plugin, "any");
      if (config_.graphics) {
        // Solo hay dos, asi que "any" es exactamente la otra.
        const char* la_otra = (backend_elegido == "vulkan") ? "d3d12" : "vulkan";
        REXLOG_WARN("Arrancando con '{}' en su lugar. Cambia gpu_backend para quitar el aviso.",
                    la_otra);
      }
    }

    // Y aqui se borra la lista de "pendiente de reiniciar", que a estas alturas
    // solo puede tener mentiras.
    //
    // SetFlagFromSource apunta en esa lista cualquier cvar kRequiresRestart que
    // se toque, SIN MIRAR de donde viene el valor. Con lo cual un
    // --gpu_backend=vulkan en la linea de comandos, que se aplica en el
    // arranque y ya esta puesto cuando se lee aqui arriba, entraba igualmente
    // en la lista, y el menu de F4 abria diciendo "Restart needed to apply:
    // gpu_backend" desde el primer segundo. Un aviso que no se puede quitar
    // deja de leerse, y entonces tampoco se lee cuando es de verdad.
    //
    // Todo lo que hay en la lista en este punto viene del toml o de la linea de
    // comandos, o sea que ya esta aplicado por definicion. Lo que se cambie
    // luego desde F4 se vuelve a apuntar y ese aviso si es real.
    rex::cvar::ClearPendingRestartFlags();
"""

BLOQUES = [
    ("el cvar gpu_backend", CVAR_ANCLA, CVAR_NUEVO),
    ("pasarselo al cargador", CARGA_ANCLA, CARGA_NUEVO),
]

# ---------------------------------------------------------------------------
#  Version anterior de ESTE parche, para poder migrar
#
#  La v1 dejaba gpu_backend en kInitOnly -y por eso salia en rojo y no se podia
#  tocar en el menu-, con "any" entre las opciones y sin reserva si la API
#  elegida no estaba compilada. Textos sacados tal cual del fichero ya
#  parcheado, no escritos a mano, para que la sustitucion sea exacta.
# ---------------------------------------------------------------------------

VIEJO_CVAR = 'REXCVAR_DEFINE_STRING(gpu_plugin, "", "GPU",\n                      "GPU emulation plugin to load at startup (e.g. \'xenos\'); empty disables "\n                      "GPU emulation")\n    .lifecycle(rex::cvar::Lifecycle::kInitOnly);\n\n// PARCHE LOCAL - selector de API grafica\n//\n// El plugin ya sabia elegir entre D3D12 y Vulkan por nombre; lo que faltaba\n// era que alguien se lo dijera. Ver plugin_main.cpp:\n//\n//     if (backend == "any" || backend == "d3d12")  -> D3D12GraphicsSystem\n//     if (backend == "any" || backend == "vulkan") -> VulkanGraphicsSystem\n//\n// "any" coge el primero que este compilado, que es D3D12. Con esto se puede\n// forzar uno concreto y comparar.\n//\n// De solo lectura en marcha: el sistema grafico se crea una vez al arrancar y\n// no se puede cambiar con el juego abierto. En F4 se ve, se cambia, y hace\n// falta reiniciar; igual que gpu_plugin, que esta justo encima.\n//\n// El texto va en ingles porque es lo que sale en esa ventana, que es del SDK\n// y esta entera en ingles.\nREXCVAR_DEFINE_STRING(gpu_backend, "any", "GPU",\n                      "Graphics API to use: any (first one available), d3d12 or vulkan. "\n                      "Vulkan only works if the SDK was built with REXGLUE_USE_VULKAN=ON. "\n                      "Takes effect on restart.")\n    .allowed({"any", "d3d12", "vulkan"})\n    .lifecycle(rex::cvar::Lifecycle::kInitOnly);\n'

VIEJA_CARGA = '  if (!config_.graphics && !config_.gpu_plugin.empty()) {\n    // PARCHE LOCAL - selector de API grafica\n    //\n    // Antes se llamaba con un solo argumento, asi que el backend quedaba en\n    // "any" por defecto y siempre salia D3D12 por ser el primero del if. El\n    // segundo parametro ya existia en LoadGpuPlugin; solo faltaba usarlo.\n    const std::string backend_elegido = REXCVAR_GET(gpu_backend);\n    REXLOG_INFO("API grafica pedida: {}", backend_elegido);\n    config_.graphics = rex::system::LoadGpuPlugin(config_.gpu_plugin, backend_elegido);\n'

# La v2 anadia una variable global compartida entre rex_app.cpp y el menu de
# ajustes. NO PODIA FUNCIONAR, y el enlazador lo dijo con todas las letras:
#
#   lld-link: error: undefined symbol: rex::ui::g_gpu_backend_en_uso
#   >>> referenced by settings_overlay.cpp.obj
#
# Yo daba por hecho que los dos ficheros iban a la misma biblioteca. Pues no:
# rex_app.cpp NO se compila dentro del SDK, se INSTALA como fuente en
# share/rexglue/ y lo compila cada aplicacion. O sea que la definicion acababa
# dentro de nfsmw.exe y la referencia dentro de rexruntime.dll. Se ve mirando
# donde deja los .obj el propio error.
VIEJO_CVAR_V2 = 'REXCVAR_DEFINE_STRING(gpu_plugin, "", "GPU",\n                      "GPU emulation plugin to load at startup (e.g. \'xenos\'); empty disables "\n                      "GPU emulation")\n    .lifecycle(rex::cvar::Lifecycle::kInitOnly);\n\n// PARCHE LOCAL - selector de API grafica\n//\n// El plugin ya sabia elegir entre D3D12 y Vulkan por nombre; lo que faltaba\n// era que alguien se lo dijera. Ver plugin_main.cpp:\n//\n//     if (backend == "any" || backend == "d3d12")  -> D3D12GraphicsSystem\n//     if (backend == "any" || backend == "vulkan") -> VulkanGraphicsSystem\n//\n// "any" coge el primero que este compilado, que es D3D12. Con esto se puede\n// forzar uno concreto y comparar.\n//\n// PIDE REINICIO, PERO NO ES DE SOLO LECTURA. La primera version lo puse como\n// kInitOnly, igual que gpu_plugin, y el menu de F4 lo pintaba en rojo y\n// deshabilitado: se veia pero no se podia tocar. Es que kInitOnly significa\n// "no se puede ni guardar el valor nuevo", y aqui si se puede: lo que no se\n// puede es aplicarlo sin reiniciar. Eso es kRequiresRestart, que ademas hace\n// que el SDK lo apunte en su lista de cambios pendientes -y el menu la\n// ensena, con un boton para reiniciar-.\n//\n// Y ya no hay "any". Con any no se sabia cual estaba puesta de verdad, que era\n// justo lo que habia que ensenar. Con dos opciones y ambas explicitas, el\n// ajuste ES la respuesta a "cual se esta usando".\n//\n// El texto va en ingles porque es lo que sale en esa ventana, que es del SDK\n// y esta entera en ingles.\nREXCVAR_DEFINE_STRING(gpu_backend, "d3d12", "GPU",\n                      "Graphics API: d3d12 or vulkan. Takes effect on restart. If the one "\n                      "you pick was not built into this copy, the game falls back to the "\n                      "other one and says so in the log.")\n    .allowed({"d3d12", "vulkan"})\n    .lifecycle(rex::cvar::Lifecycle::kRequiresRestart);\n\n// PARCHE LOCAL - selector de API grafica\n//\n// La API que se acabo usando de verdad, para que el menu de F4 la pueda\n// ensenar. Casi siempre es la que dice el cvar, pero si esa no estaba\n// compilada se arranca con la otra, y entonces el cvar miente.\n//\n// Vive aqui y no en un sitio mas elegante porque rex_app.cpp y el menu de\n// ajustes se compilan en la misma biblioteca; una variable suelta y una\n// declaracion extern bastan, sin cabeceras nuevas ni ABI que mantener.\nnamespace rex::ui {\nstd::string g_gpu_backend_en_uso = "?";\n}  // namespace rex::ui\n'

VIEJA_CARGA_V2 = '  if (!config_.graphics && !config_.gpu_plugin.empty()) {\n    // PARCHE LOCAL - selector de API grafica\n    //\n    // Antes se llamaba con un solo argumento, asi que el backend quedaba en\n    // "any" por defecto y siempre salia D3D12 por ser el primero del if. El\n    // segundo parametro ya existia en LoadGpuPlugin; solo faltaba usarlo.\n    const std::string backend_elegido = REXCVAR_GET(gpu_backend);\n    REXLOG_INFO("API grafica pedida: {}", backend_elegido);\n    config_.graphics = rex::system::LoadGpuPlugin(config_.gpu_plugin, backend_elegido);\n    rex::ui::g_gpu_backend_en_uso = backend_elegido;\n\n    // Si la que se ha pedido no esta compilada en esta copia, el plugin\n    // devuelve nada. Antes de eso significaba pantalla de error y a editar el\n    // toml a mano; ahora se cae a la otra y se dice bien claro. Como solo hay\n    // dos, "any" es exactamente la otra.\n    if (!config_.graphics) {\n      REXLOG_WARN("La API grafica \'{}\' no esta compilada en esta copia. Se prueba con la otra.",\n                  backend_elegido);\n      config_.graphics = rex::system::LoadGpuPlugin(config_.gpu_plugin, "any");\n      if (config_.graphics) {\n        rex::ui::g_gpu_backend_en_uso = (backend_elegido == "vulkan") ? "d3d12" : "vulkan";\n        REXLOG_WARN("Arrancando con \'{}\' en su lugar. Para quitar el aviso, cambia gpu_backend.",\n                    rex::ui::g_gpu_backend_en_uso);\n      }\n    }\n'

# La v3 ya era la buena -sin variable compartida, con reserva-, pero le faltaba
# limpiar la lista de reinicios pendientes, asi que el menu de F4 abria con un
# aviso falso en cuanto el lanzador pasaba --gpu_backend. Es la v4 sin esa
# ultima linea, o sea un PREFIJO EXACTO de la v4: el caso que obligo a cambiar
# la regla de quitar_version_vieja.
#
# Se recorta del bloque de ahora en vez de copiarlo a mano, que es donde se
# cuelan las erratas. El corte va JUSTO ANTES del salto de linea que abre la
# linea en blanco de separacion, asi que lo que queda termina en "    }\n",
# que es exactamente como terminaba la v3. Un "\n" de mas aqui y el bloque no
# se encuentra nunca, porque en el fichero despues de esa llave viene
# directamente "    if (!config_.graphics) {", sin linea en blanco.
VIEJA_CARGA_V3 = CARGA_NUEVO[:CARGA_NUEVO.index(
    "\n\n    // Y aqui se borra la lista") + 1]

# DE MAS NUEVO A MAS VIEJO. La v2 es la v1 con cosas anadidas, asi que mirar
# la v1 primero se llevaria solo su parte y dejaria la cola de la v2 suelta.
VIEJOS = [
    # (nombre, huella que SOLO aparece en esa version, bloque entero, anclaje)
    ("carga de la v3 (sin limpiar los reinicios pendientes)",
     'const char* la_otra = (backend_elegido == "vulkan") ? "d3d12" : "vulkan";',
     VIEJA_CARGA_V3, CARGA_ANCLA),
    ("cvar de la v2 (variable compartida)",
     'std::string g_gpu_backend_en_uso = "?";', VIEJO_CVAR_V2, CVAR_ANCLA),
    ("carga de la v2 (variable compartida)",
     'rex::ui::g_gpu_backend_en_uso = backend_elegido;', VIEJA_CARGA_V2, CARGA_ANCLA),
    ("cvar de la v1 (any / solo lectura)",
     '.allowed({"any", "d3d12", "vulkan"})', VIEJO_CVAR, CVAR_ANCLA),
    ("carga de la v1 (sin reserva)",
     'REXLOG_INFO("API grafica pedida: {}", backend_elegido);', VIEJA_CARGA, CARGA_ANCLA),
]


def localizar_sdk():
    raiz = pathlib.Path(__file__).resolve().parent.parent
    # NFSMW_SDK apunta a otro arbol del SDK (el de Android, por ejemplo). Si
    # esta puesta se usa SOLO esa ruta: caer en silencio en el SDK de Windows
    # parchearia el arbol equivocado.
    otro = os.environ.get("NFSMW_SDK")
    candidatos = [pathlib.Path(otro)] if otro else [raiz.parent / "rexglue-sdk", raiz / "sdk"]
    for cand in candidatos:
        if (cand / "src" / "ui" / "rex_app.cpp").exists():
            return cand
    sys.exit("[ERROR] No encuentro src/ui/rex_app.cpp del SDK.\n"
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

    f = localizar_sdk() / "src" / "ui" / "rex_app.cpp"
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
                     f"        El SDK habra cambiado. No he tocado nada.")

    for nombre, ancla, nuevo in faltan:
        txt = txt.replace(ancla, nuevo)
        print(f"[ok] Aplicado: {nombre}")
    f.write_text(txt, encoding="utf-8")
    print()
    print("  En F4, categoria GPU, ajuste  gpu_backend  (d3d12 / vulkan)")
    print("  Pide reiniciar el juego para que valga.")
    print()
    print("  HAY QUE RECOMPILAR EL SDK, y con Vulkan encendido:")
    print("    cmake --preset win-amd64 -DREXGLUE_USE_VULKAN=ON")
    print("    cmake --build out/build/win-amd64 --config Release --target install")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
