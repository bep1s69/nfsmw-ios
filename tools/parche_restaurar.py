#!/usr/bin/env python3
"""
Mejora el menu de ajustes (F4): boton de restaurar, y deslizadores.

    python tools/parche_restaurar.py            aplicar
    python tools/parche_restaurar.py --estado
    python tools/parche_restaurar.py --revertir

Toca un fichero del SDK:  src/ui/overlay/settings_overlay.cpp

No guarda .original y no le hace falta: aplica y deshace por sustitucion de
texto exacta, bloque a bloque. Es a proposito. En este SDK hay ficheros que ya
llevan otro parche encima, y guardar ahi un ".original" a estas alturas
guardaria el fichero YA parcheado como si fuera el limpio; de paso, un
--revertir se llevaria por delante el parche del otro. Asi cada parche quita
lo suyo y solo lo suyo.

Y va bloque a bloque, no con una marca global, POR UN FALLO QUE YA PASO. La
primera version solo traia el boton. Cuando le anadi los deslizadores, el
script miraba si su marca estaba puesta, la encontraba -del boton- y decia "ya
estaba" sin aplicar nada nuevo. Resultado: boton si, deslizador no, y sin un
solo mensaje de error. Ahora cada bloque se comprueba por separado, asi que
anadir uno mas en el futuro lo aplica sin tener que deshacer lo anterior.


EL BOTON DE RESTAURAR
=====================

El menu de F4 ya trae un "Reset" por ajuste, pero solo en los keybinds, y hay
que ir uno por uno. Probando cvars de rendimiento se tocan seis o siete en un
rato y luego no hay forma de saber cuales quedaron movidos: los numeros
siguientes ya no comparan contra nada.

Vuelve a LA CONFIGURACION DE PARTIDA, no a los valores de fabrica del SDK. O
sea: lo que el juego tenia puesto al abrirse, con el nfsmw.toml ya aplicado.
Es lo que se espera de un "reset" aqui: si el toml deja el motor de video en
rtv y el filtrado anisotropico apagado, restaurar tiene que dejarlo asi, no
devolverte a unos valores del SDK que nunca has usado y que ademas van peor.

Se hace con una foto de todos los ajustes tomada la primera vez que se abre
esta ventana. En la practica esa foto ES el arranque, porque nada de aqui
cambia solo; si hubieras tocado algo por la consola antes de abrir F4, esa
seria la foto. Se dice en el aviso para que no sorprenda.

Tres salvedades, y las tres importan:

  - NO toca los de solo lectura. Se fijan al arrancar y la interfaz ya los
    pinta deshabilitados; intentarlo seria mentir.

  - NO escribe el nfsmw.toml. Solo cambia los valores vivos. Si quieres que el
    reinicio quede igual, hay que darle despues a "Save to config". Asi un
    clic sin querer no se lleva por delante la configuracion del disco.

  - Los que piden reinicio se cambian igual, pero no se notan hasta la
    siguiente vez que abras el juego.

Antes de hacer nada pregunta, porque es destructivo y esta pegado al boton de
guardar.


LOS DESLIZADORES
================

Los ajustes decimales se editaban con una caja de texto: escribir el numero y
Enter. Para uno que se busca a tanteo -game_speed, por ejemplo- eso es
incomodo, porque no puedes arrastrar y ver el efecto sobre la marcha.

Cuando el ajuste declara minimo y maximo, ahora sale un deslizador. Cuando no
los declara se queda la caja de siempre, porque sin limites no hay por donde
deslizar. Ctrl+clic sobre el deslizador sigue dejando escribir el valor exacto.

Los decimales que ensenia salen del propio recorrido: si va de 0 a 200 -un
porcentaje- se ve entero, y si va de 0 a 1 se ven tres decimales. Con un
formato fijo, o los porcentajes salian como "100.00" o las barras cortas
parecian rotas.


POR QUE LOS TEXTOS ESTAN EN INGLES
==================================

Los botones de al lado son "Save to config", "Rebind" y "Reset". Esa ventana
es del SDK y esta entera en ingles; meter texto en castellano en medio se ve
como un fallo, no como una traduccion. Los comentarios del codigo si van en
castellano, como en el resto de parches de este proyecto.
"""

import argparse
import os
import pathlib
import sys

# ---------------------------------------------------------------------------
#  1) Cabeceras
# ---------------------------------------------------------------------------

CAB_ANCLA = """#include <rex/ui/keybinds.h>
#include <imgui.h>
"""

CAB_NUEVO = """#include <rex/logging.h>  // PARCHE LOCAL - para dejar constancia del restaurado
#include <rex/ui/keybinds.h>
#include <imgui.h>

#include <cstdlib>  // PARCHE LOCAL - std::_Exit, para el boton de reiniciar
#include <utility>  // PARCHE LOCAL - std::pair, que llegaba de rebote por <map>

// PARCHE LOCAL - para relanzar el juego desde el boton de reiniciar.
//
// Las dos guardas van como en src/ui/windowed_app_main_sdl.cpp, que ya incluye
// windows.h de esta manera. NOMINMAX importa aqui de verdad: sin el, windows.h
// define min y max como macros y este fichero usa std::min y std::max.
#if defined(_WIN32)
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif
"""

# ---------------------------------------------------------------------------
#  2) La foto de la configuracion de partida
# ---------------------------------------------------------------------------

FOTO_ANCLA = """void SettingsDialog::OnDraw(ImGuiIO& /*io*/) {
  auto& registry = rex::cvar::GetRegistry();
"""

FOTO_NUEVO = """void SettingsDialog::OnDraw(ImGuiIO& /*io*/) {
  auto& registry = rex::cvar::GetRegistry();

  // PARCHE LOCAL - foto de la configuracion de partida
  //
  // Es a lo que vuelve el boton "Restore defaults", y no a los valores de
  // fabrica del SDK. La diferencia importa: el nfsmw.toml deja puestas cosas
  // -el motor de video, el filtrado- que son la configuracion buena de este
  // juego. Restaurar a los valores del SDK dejaria una que nunca se ha usado,
  // y encima peor.
  //
  // Se toma la primera vez que se dibuja esta ventana. En la practica eso es
  // el arranque, porque nada de aqui cambia solo. Si alguien hubiera tocado
  // algo por la consola antes de abrir F4, esa seria la foto; el aviso del
  // boton lo dice para que no sorprenda.
  //
  // Los cvars del complemento de GPU se registran al cargar su DLL, que es
  // mucho antes de que nadie pulse F4, asi que entran en la foto igual.
  static std::vector<std::pair<std::string, std::string>> configuracion_de_partida;
  static bool foto_tomada = false;
  if (!foto_tomada) {
    foto_tomada = true;
    configuracion_de_partida.reserve(registry.size());
    for (auto& e : registry) {
      configuracion_de_partida.emplace_back(e.name, e.getter());
    }
    REXLOG_DEBUG("[ajustes] foto de partida: {} valores", configuracion_de_partida.size());
  }
"""

# ---------------------------------------------------------------------------
#  3) Deslizador para los decimales con limites
# ---------------------------------------------------------------------------

DOBLE_ANCLA = """      } else if (entry.type == rex::cvar::FlagType::Double) {
        double v = std::atof(current_val.c_str());
        if (ImGui::InputDouble("##v", &v, 0.0, 0.0, "%.4f")) {
          if (entry.constraints.min)
            v = std::max(v, *entry.constraints.min);
          if (entry.constraints.max)
            v = std::min(v, *entry.constraints.max);
          rex::cvar::SetFlagByName(entry.name, std::to_string(v));
        }
"""

DOBLE_NUEVO = """      } else if (entry.type == rex::cvar::FlagType::Double) {
        // PARCHE LOCAL - deslizador cuando el ajuste trae minimo y maximo.
        //
        // Con la caja de texto hay que escribir el numero y darle a Enter. Para
        // un ajuste que se busca a tanteo -la velocidad del juego, sin ir mas
        // lejos- eso es incomodo: no puedes arrastrar y ver el efecto. Con
        // limites conocidos, un deslizador es lo suyo; sin ellos no hay por
        // donde deslizar, asi que se queda la caja de siempre.
        //
        // Ctrl+clic sobre el deslizador sigue dejando escribir el valor exacto.
        if (entry.constraints.min.has_value() && entry.constraints.max.has_value()) {
          float v = static_cast<float>(std::atof(current_val.c_str()));
          const float vmin = static_cast<float>(*entry.constraints.min);
          const float vmax = static_cast<float>(*entry.constraints.max);
          // Cuantos decimales enseniar. Un recorrido largo -0 a 200, que es un
          // porcentaje- se lee mejor entero; uno corto -0 a 1- necesita
          // decimales o la barra parece que no hace nada.
          const char* formato = (vmax - vmin >= 10.0f) ? "%.0f" : "%.3f";
          if (ImGui::SliderFloat("##v", &v, vmin, vmax, formato)) {
            v = std::clamp(v, vmin, vmax);
            rex::cvar::SetFlagByName(entry.name, std::to_string(v));
          }
        } else {
          double v = std::atof(current_val.c_str());
          if (ImGui::InputDouble("##v", &v, 0.0, 0.0, "%.4f")) {
            if (entry.constraints.min)
              v = std::max(v, *entry.constraints.min);
            if (entry.constraints.max)
              v = std::min(v, *entry.constraints.max);
            rex::cvar::SetFlagByName(entry.name, std::to_string(v));
          }
        }
"""

# ---------------------------------------------------------------------------
#  4) La barra de abajo: el boton y su confirmacion
# ---------------------------------------------------------------------------

BARRA_ANCLA = """  // Bottom bar: Save button.
  ImGui::Separator();
  if (ImGui::Button("Save to config")) {
    rex::cvar::SaveConfig(config_path_);
  }
  ImGui::SameLine();
  ImGui::TextDisabled("(%s)", config_path_.filename().string().c_str());
"""

BARRA_NUEVO = """  // Bottom bar: Save button.
  ImGui::Separator();
  if (ImGui::Button("Save to config")) {
    rex::cvar::SaveConfig(config_path_);
  }
  ImGui::SameLine();

  // PARCHE LOCAL - boton de restaurar la configuracion de partida
  //
  // Va detras de una confirmacion a proposito: esta pegado al de guardar y es
  // destructivo. Un clic de mas no puede costar media tarde de ajustes.
  if (ImGui::Button("Restore defaults")) {
    ImGui::OpenPopup("Restore defaults?##rex_restore");
  }
  ImGui::SameLine();
  ImGui::TextDisabled("(%s)", config_path_.filename().string().c_str());

  if (ImGui::BeginPopupModal("Restore defaults?##rex_restore", nullptr,
                             ImGuiWindowFlags_AlwaysAutoResize)) {
    ImGui::TextUnformatted("Every setting goes back to how it was when the game started,");
    ImGui::TextUnformatted("with your config file already applied.");
    ImGui::Spacing();
    ImGui::BulletText("Read-only settings are left alone: they are fixed when the\\n"
                      "game starts, so changing them now would do nothing.");
    ImGui::BulletText("Settings that need a restart do change, but only take\\n"
                      "effect the next time you start the game.");
    ImGui::BulletText("%s is NOT written. Press \\"Save to config\\"\\n"
                      "afterwards if you want this to survive a restart.",
                      config_path_.filename().string().c_str());
    ImGui::Separator();

    if (ImGui::Button("Restore", ImVec2(120.0f, 0))) {
      // Se recoge la lista ANTES de tocar nada. SetFlagByName escribe en la
      // entrada del registro -al menos su origen-, y no me apetece estar
      // recorriendo el contenedor mientras se modifica.
      std::vector<std::pair<std::string, std::string>> pendientes;
      for (auto& e : registry) {
        // Solo lectura: fijados al arrancar. Entre ellos esta el motor de
        // video, que es justo el que no queremos perder.
        if (e.lifecycle == rex::cvar::Lifecycle::kInitOnly) {
          continue;
        }
        // Los comandos son botones, no tienen valor que restaurar.
        if (e.type == rex::cvar::FlagType::Command) {
          continue;
        }

        // El valor de la foto de partida. Si el ajuste no estaba -se registro
        // despues de abrir esta ventana la primera vez, que es raro pero
        // posible- se cae al valor de fabrica, que es lo unico que se sabe.
        const std::string* objetivo = nullptr;
        for (auto& [nombre, valor] : configuracion_de_partida) {
          if (nombre == e.name) {
            objetivo = &valor;
            break;
          }
        }
        const std::string& valor_bueno = objetivo ? *objetivo : e.default_value;

        if (e.getter() == valor_bueno) {
          continue;
        }
        pendientes.emplace_back(e.name, valor_bueno);
      }

      int restaurados = 0;
      for (auto& [nombre, valor] : pendientes) {
        if (rex::cvar::SetFlagByName(nombre, valor)) {
          ++restaurados;
        }
      }
      REXLOG_INFO("[ajustes] {} de {} valores devueltos a la configuracion de partida",
                  restaurados, pendientes.size());
      ImGui::CloseCurrentPopup();
    }

    ImGui::SameLine();
    if (ImGui::Button("Cancel", ImVec2(120.0f, 0))) {
      ImGui::CloseCurrentPopup();
    }
    ImGui::EndPopup();
  }
"""

# ---------------------------------------------------------------------------
#  Version anterior de ESTE parche, para poder migrar
#
#  La v1 solo traia el boton, y restauraba a los valores de FABRICA del SDK en
#  vez de a la configuracion de partida. Si sigue puesta hay que quitarla
#  antes, o el anclaje del boton no encaja: su sitio esta ocupado.
#
#  Este texto esta sacado tal cual del fichero ya parcheado, no escrito a mano,
#  para que la sustitucion sea exacta.
# ---------------------------------------------------------------------------

VIEJA_BARRA = '  // Bottom bar: Save button.\n  ImGui::Separator();\n  if (ImGui::Button("Save to config")) {\n    rex::cvar::SaveConfig(config_path_);\n  }\n  ImGui::SameLine();\n\n  // PARCHE LOCAL - boton de restaurar valores por defecto\n  //\n  // Va detras de una confirmacion a proposito: esta pegado al de guardar y es\n  // destructivo. Un clic de mas no puede costar media tarde de ajustes.\n  if (ImGui::Button("Restore defaults")) {\n    ImGui::OpenPopup("Restore defaults?##rex_restore");\n  }\n  ImGui::SameLine();\n  ImGui::TextDisabled("(%s)", config_path_.filename().string().c_str());\n\n  if (ImGui::BeginPopupModal("Restore defaults?##rex_restore", nullptr,\n                             ImGuiWindowFlags_AlwaysAutoResize)) {\n    ImGui::TextUnformatted("Every setting goes back to its built-in default.");\n    ImGui::Spacing();\n    ImGui::BulletText("Read-only settings are left alone: they are fixed when the\\n"\n                      "game starts, so changing them now would do nothing.");\n    ImGui::BulletText("Settings that need a restart do change, but only take\\n"\n                      "effect the next time you start the game.");\n    ImGui::BulletText("%s is NOT written. Press \\"Save to config\\"\\n"\n                      "afterwards if you want this to survive a restart.",\n                      config_path_.filename().string().c_str());\n    ImGui::Separator();\n\n    if (ImGui::Button("Restore", ImVec2(120.0f, 0))) {\n      // Los nombres se recogen ANTES de tocar nada. SetFlagByName escribe en\n      // la entrada del registro -al menos su origen- y no me apetece estar\n      // recorriendo el contenedor mientras se modifica.\n      std::vector<std::pair<std::string, std::string>> pendientes;\n      for (auto& e : registry) {\n        // Solo lectura: fijados al arrancar. Entre ellos esta el motor de\n        // video, que es justo el que no queremos perder.\n        if (e.lifecycle == rex::cvar::Lifecycle::kInitOnly) {\n          continue;\n        }\n        // Los comandos son botones, no tienen valor que restaurar.\n        if (e.type == rex::cvar::FlagType::Command) {\n          continue;\n        }\n        if (e.getter() == e.default_value) {\n          continue;\n        }\n        pendientes.emplace_back(e.name, e.default_value);\n      }\n\n      int restaurados = 0;\n      for (auto& [nombre, porDefecto] : pendientes) {\n        if (rex::cvar::SetFlagByName(nombre, porDefecto)) {\n          ++restaurados;\n        }\n      }\n      REXLOG_INFO("[ajustes] {} de {} valores devueltos a su valor por defecto", restaurados,\n                  pendientes.size());\n      ImGui::CloseCurrentPopup();\n    }\n\n    ImGui::SameLine();\n    if (ImGui::Button("Cancel", ImVec2(120.0f, 0))) {\n      ImGui::CloseCurrentPopup();\n    }\n    ImGui::EndPopup();\n  }\n'

VIEJAS_CABECERAS = '#include <rex/logging.h>  // PARCHE LOCAL - para dejar constancia del restaurado\n#include <rex/ui/keybinds.h>\n#include <imgui.h>\n\n#include <utility>  // PARCHE LOCAL - std::pair, que llegaba de rebote por <map>\n'

VIEJO_AVISO_V1 = '  // PARCHE LOCAL - aviso de reinicio pendiente, con boton para reiniciar\n  //\n  // El SDK ya llevaba la cuenta de los ajustes cambiados que piden reinicio\n  // -SetFlagFromSource llama a MarkPendingRestart, y GetPendingRestartFlags los\n  // devuelve-, pero no lo ensenaba en ninguna parte. Sin eso, cambiar la API\n  // grafica o cualquier otro de esos parecia no hacer nada: pones el valor,\n  // vuelves al juego, y todo sigue igual sin una sola pista de por que.\n  //\n  // Sirve para todos, no solo para el de la API.\n  {\n    // La API grafica que se acabo usando. La pone rex_app.cpp al arrancar, y no\n    // siempre coincide con el cvar gpu_backend: si la que pediste no estaba\n    // compilada en esta copia, se arranca con la otra. Por eso se ensena la\n    // real y no el ajuste.\n    //\n    // Un extern a secas, sin cabecera nueva: rex_app.cpp y este fichero se\n    // compilan en la misma biblioteca.\n    extern std::string g_gpu_backend_en_uso;\n    ImGui::Separator();\n    ImGui::Text("Graphics API in use: %s", g_gpu_backend_en_uso.c_str());\n\n    const auto pendientes_reinicio = rex::cvar::GetPendingRestartFlags();\n    if (!pendientes_reinicio.empty()) {\n      std::string lista;\n      for (const auto& n : pendientes_reinicio) {\n        if (!lista.empty()) {\n          lista += ", ";\n        }\n        lista += n;\n      }\n      ImGui::TextColored(imgui_drawer()->style().settings.warning,\n                         "Restart needed to apply: %s", lista.c_str());\n#if defined(_WIN32)\n      // Guarda ANTES de reiniciar, y no es un extra: estos ajustes solo viven\n      // en memoria hasta que se guardan. Reiniciar sin guardar volveria con el\n      // valor viejo y pareceria que el boton no hace nada.\n      if (ImGui::Button("Save and restart")) {\n        rex::cvar::SaveConfig(config_path_);\n\n        // Sin std::size a proposito: sale de <iterator>, que este fichero no\n        // incluye y que llega de rebote segun la implementacion. Una constante\n        // no depende de nada.\n        constexpr DWORD kMaxRuta = 1024;\n        wchar_t ruta[kMaxRuta];\n        const DWORD largo = GetModuleFileNameW(nullptr, ruta, kMaxRuta);\n        bool relanzado = false;\n        if (largo > 0 && largo < kMaxRuta) {\n          // La misma linea de comandos con la que se abrio, para no perder la\n          // ISO ni las opciones que le pasa el lanzador. CreateProcessW puede\n          // escribir en ese buffer, asi que se le da una copia propia.\n          std::wstring linea = GetCommandLineW();\n          std::vector<wchar_t> linea_editable(linea.begin(), linea.end());\n          linea_editable.push_back(L\'\\0\');\n\n          STARTUPINFOW si{};\n          si.cb = sizeof(si);\n          PROCESS_INFORMATION pi{};\n          if (CreateProcessW(ruta, linea_editable.data(), nullptr, nullptr, FALSE, 0, nullptr,\n                             nullptr, &si, &pi)) {\n            CloseHandle(pi.hProcess);\n            CloseHandle(pi.hThread);\n            relanzado = true;\n          }\n        }\n\n        if (relanzado) {\n          REXLOG_INFO("[ajustes] reiniciando para aplicar: {}", lista);\n          // Misma salida que usa la app al cerrar la ventana: vaciar el log y\n          // cortar en seco. El desmontaje ordenado puede quedarse colgado en un\n          // cerrojo que dejo algun hilo del juego, y por eso el SDK tampoco lo\n          // hace ahi.\n          rex::FlushLogging();\n          std::_Exit(0);\n        }\n        REXLOG_ERROR("[ajustes] no se pudo relanzar el juego (error {}). Cierralo y abrelo tu.",\n                     GetLastError());\n      }\n      ImGui::SameLine();\n      ImGui::TextDisabled("(saves first, then opens again with the same options)");\n#else\n      ImGui::TextDisabled("Close the game and open it again to apply.");\n#endif\n    }\n  }\n\n'

AVISO_ANCLA = """  ImGui::EndChild();

  // Bottom bar: Save button.
"""

AVISO_NUEVO = """  ImGui::EndChild();

  // PARCHE LOCAL - aviso de reinicio pendiente, con boton para reiniciar
  //
  // El SDK ya llevaba la cuenta de los ajustes cambiados que piden reinicio
  // -SetFlagFromSource llama a MarkPendingRestart, y GetPendingRestartFlags los
  // devuelve-, pero no lo ensenaba en ninguna parte. Sin eso, cambiar la API
  // grafica o cualquier otro de esos parecia no hacer nada: pones el valor,
  // vuelves al juego, y todo sigue igual sin una sola pista de por que.
  //
  // Sirve para todos, no solo para el de la API.
  {
    // La API grafica, leida del registro de cvars por nombre.
    //
    // La primera version de esto usaba una variable global compartida con
    // rex_app.cpp, y NO ENLAZABA: rex_app.cpp no se compila dentro del SDK,
    // se instala como fuente y lo compila cada aplicacion, asi que la
    // definicion acaba en el .exe y esta referencia en la DLL. El registro de
    // cvars, en cambio, esta hecho justo para hablar entre modulos.
    //
    // Y desde que se quito "any" de las opciones, el ajuste ES la API: el
    // unico caso en que no coincide es que la elegida no este compilada en
    // esta copia, y entonces el arranque lo deja escrito en el log.
    ImGui::Separator();
    ImGui::Text("Graphics API: %s", rex::cvar::GetFlagByName("gpu_backend").c_str());

    const auto pendientes_reinicio = rex::cvar::GetPendingRestartFlags();
    if (!pendientes_reinicio.empty()) {
      std::string lista;
      for (const auto& n : pendientes_reinicio) {
        if (!lista.empty()) {
          lista += ", ";
        }
        lista += n;
      }
      ImGui::TextColored(imgui_drawer()->style().settings.warning,
                         "Restart needed to apply: %s", lista.c_str());
#if defined(_WIN32)
      // Guarda ANTES de reiniciar, y no es un extra: estos ajustes solo viven
      // en memoria hasta que se guardan. Reiniciar sin guardar volveria con el
      // valor viejo y pareceria que el boton no hace nada.
      if (ImGui::Button("Save and restart")) {
        rex::cvar::SaveConfig(config_path_);

        // Sin std::size a proposito: sale de <iterator>, que este fichero no
        // incluye y que llega de rebote segun la implementacion. Una constante
        // no depende de nada.
        constexpr DWORD kMaxRuta = 1024;
        wchar_t ruta[kMaxRuta];
        const DWORD largo = GetModuleFileNameW(nullptr, ruta, kMaxRuta);
        bool relanzado = false;
        if (largo > 0 && largo < kMaxRuta) {
          // La misma linea de comandos con la que se abrio, para no perder la
          // ISO ni las opciones que le pasa el lanzador. CreateProcessW puede
          // escribir en ese buffer, asi que se le da una copia propia.
          std::wstring linea = GetCommandLineW();
          std::vector<wchar_t> linea_editable(linea.begin(), linea.end());
          linea_editable.push_back(L'\\0');

          STARTUPINFOW si{};
          si.cb = sizeof(si);
          PROCESS_INFORMATION pi{};
          if (CreateProcessW(ruta, linea_editable.data(), nullptr, nullptr, FALSE, 0, nullptr,
                             nullptr, &si, &pi)) {
            CloseHandle(pi.hProcess);
            CloseHandle(pi.hThread);
            relanzado = true;
          }
        }

        if (relanzado) {
          REXLOG_INFO("[ajustes] reiniciando para aplicar: {}", lista);
          // Misma salida que usa la app al cerrar la ventana: vaciar el log y
          // cortar en seco. El desmontaje ordenado puede quedarse colgado en un
          // cerrojo que dejo algun hilo del juego, y por eso el SDK tampoco lo
          // hace ahi.
          rex::FlushLogging();
          std::_Exit(0);
        }
        REXLOG_ERROR("[ajustes] no se pudo relanzar el juego (error {}). Cierralo y abrelo tu.",
                     GetLastError());
      }
      ImGui::SameLine();
      ImGui::TextDisabled("(saves first, then opens again with the same options)");
#else
      ImGui::TextDisabled("Close the game and open it again to apply.");
#endif
    }
  }

  // Bottom bar: Save button.
"""

BLOQUES = [
    ("cabeceras", CAB_ANCLA, CAB_NUEVO),
    ("aviso de reinicio pendiente", AVISO_ANCLA, AVISO_NUEVO),
    ("foto de la configuracion de partida", FOTO_ANCLA, FOTO_NUEVO),
    ("deslizador para decimales con limites", DOBLE_ANCLA, DOBLE_NUEVO),
    ("boton de restaurar", BARRA_ANCLA, BARRA_NUEVO),
]

# Va DESPUES de los bloques a proposito: cada entrada necesita su anclaje, y
# los anclajes se definen arriba. La primera version de esta lista estaba antes
# que ellos y la entrada del aviso se quedo con el anclaje a "", que funcionaba
# de casualidad -sustituir por cadena vacia borra el bloque y deja el anclaje
# intacto- hasta que la migracion empezo a mirar que bloque toca en cada
# anclaje y se encontro con una clave que no existia.
#
# DE MAS NUEVO A MAS VIEJO. Ver quitar_version_vieja para por que importa.
VIEJOS = [
    # (nombre, huella para avisar, bloque entero con forma de anclaje, anclaje)
    ("aviso de la v1 (variable compartida)",
     'g_gpu_backend_en_uso',
     '  ImGui::EndChild();\n\n' + VIEJO_AVISO_V1 + '  // Bottom bar: Save button.\n',
     AVISO_ANCLA),
    ("boton de la v1 (restauraba a valores de fabrica)",
     'ImGui::TextUnformatted("Every setting goes back to its built-in default.");',
     VIEJA_BARRA, BARRA_ANCLA),
    ("cabeceras de la v1 (sin windows.h)",
     '#include <rex/logging.h>  // PARCHE LOCAL - para dejar constancia del restaurado\n'
     '#include <rex/ui/keybinds.h>\n#include <imgui.h>\n\n#include <utility>',
     VIEJAS_CABECERAS, CAB_ANCLA),
]



def localizar_sdk():
    raiz = pathlib.Path(__file__).resolve().parent.parent
    # NFSMW_SDK apunta a otro arbol del SDK (el de Android, por ejemplo). Si
    # esta puesta se usa SOLO esa ruta: caer en silencio en el SDK de Windows
    # parchearia el arbol equivocado.
    otro = os.environ.get("NFSMW_SDK")
    candidatos = [pathlib.Path(otro)] if otro else [raiz.parent / "rexglue-sdk", raiz / "sdk"]
    for cand in candidatos:
        if (cand / "src" / "ui" / "overlay" / "settings_overlay.cpp").exists():
            return cand
    sys.exit("[ERROR] No encuentro src/ui/overlay/settings_overlay.cpp del SDK.\n"
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

    f = localizar_sdk() / "src" / "ui" / "overlay" / "settings_overlay.cpp"
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

    # Bloque a bloque: los que ya estan se dejan, los que faltan se aplican.
    # Asi, anadir un bloque nuevo mas adelante no obliga a deshacer lo puesto.
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
    print("  HAY QUE RECOMPILAR EL SDK para que sirva de algo:")
    print("    cmake --build out/build/win-amd64 --config Release --target install")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
