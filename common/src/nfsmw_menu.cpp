// nfsmw - menu de ajustes ingame (estilo GoldenEye, abierto con ESC)
//
// Manejado por cvars del recomp. Hay dos grupos, y cada control avisa de cual
// es:
//   * "se aplica al instante"  -> el SDK o un parche del proyecto refresca el
//                                 valor en vivo (fullscreen, vsync, max_fps,
//                                 anisotropic_override, game_speed).
//   * "se aplica al reiniciar" -> el SDK los marca como pendientes de reinicio
//                                 (lifecycle kRequiresRestart), asi que el
//                                 menu muestra el boton "Aplicar y reiniciar",
//                                 que guarda el toml y relanza el .exe.

#include "nfsmw_menu.h"

#include <rex/cvar.h>

#include <imgui.h>

#include <algorithm>
#include <cfloat>
#include <cmath>
#include <cstring>
#include <cstdlib>
#include <functional>
#include <string>
#include <vector>

// ---------------------------------------------------------------------------
//  Cvar del proyecto: contenido Black Edition.
//
//  El parche se aplica al cargar el XEX (OnPostLoadXexImage en nfsmw_app.h),
//  por eso este flag exige reinicio para activarse o desactivarse.
// ---------------------------------------------------------------------------
REXCVAR_DEFINE_BOOL(black_edition, true, "Contenido",
                    "Contenido Black Edition: coches de pago como descargables (requiere reinicio)")
    .lifecycle(rex::cvar::Lifecycle::kRequiresRestart);

namespace {

// Paleta del menu: inspirada en la interfaz del juego (fondo oscuro, acento
// naranja).
constexpr ImU32 kBg = IM_COL32(22, 26, 32, 252);
constexpr ImU32 kBorde = IM_COL32(232, 161, 60, 255);
constexpr ImU32 kMarco = IM_COL32(64, 72, 84, 255);
constexpr ImU32 kTexto = IM_COL32(220, 226, 232, 255);
constexpr ImU32 kTextoAtenuado = IM_COL32(148, 156, 168, 255);
constexpr ImU32 kAcento = IM_COL32(232, 161, 60, 255);
constexpr ImU32 kTabSel = IM_COL32(58, 66, 78, 255);
constexpr ImU32 kFondoWidget = IM_COL32(38, 44, 52, 255);
constexpr ImU32 kVivo = IM_COL32(96, 200, 86, 255);
constexpr ImU32 kAviso = IM_COL32(232, 161, 60, 255);

const char* kTitulosPestana[] = {"VÍDEO", "OTROS", "SISTEMA", "DEBUG"};
constexpr int kNumPestanas = 4;

// Acceso a cvars como strings (como hace el menu de GoldenEye).
bool CvarB(const char* nombre) { return rex::cvar::GetFlagByName(nombre) == "true"; }
void SetCvarB(const char* nombre, bool valor) {
  rex::cvar::SetFlagByName(nombre, valor ? "true" : "false");
}
std::string CvarS(const char* nombre) { return rex::cvar::GetFlagByName(nombre); }
void SetCvarS(const char* nombre, const std::string& valor) {
  rex::cvar::SetFlagByName(nombre, valor);
}
float CvarF(const char* nombre) { return static_cast<float>(std::atof(CvarS(nombre).c_str())); }
void SetCvarF(const char* nombre, float valor) {
  rex::cvar::SetFlagByName(nombre, std::to_string(valor));
}
bool ExisteCvar(const char* nombre) { return rex::cvar::GetFlagInfo(nombre) != nullptr; }

struct Opcion {
  const char* etiqueta;
  const char* valor;
};

// Fila nombre/valor para la pestana DEBUG. "-" cuando el cvar no existe o esta
// vacio.
void FilaDebug(const char* nombre, const std::string& valor) {
  const char* texto = valor.empty() ? "—" : valor.c_str();
  ImGui::Text("  %-26s %s", nombre, texto);
}

std::string JuntarLista(const std::vector<std::string>& items) {
  std::string lista;
  for (const auto& item : items) {
    if (!lista.empty()) lista += ", ";
    lista += item;
  }
  return lista;
}

// Combo con opciones fijas. Si el valor actual no esta en la lista (lo puso la
// linea de comandos, o el toml), muestra "texto_si_otro" o el valor crudo.
void ComboSimple(const char* etiqueta, const std::string& actual, const Opcion* opciones, int cuenta,
                 const char* texto_si_otro, const std::function<void(const char*)>& al_cambiar) {
  int idx = 0;
  for (int i = 0; i < cuenta; ++i) {
    if (opciones[i].valor == actual) {
      idx = i;
      break;
    }
  }
  const char* mostrar = opciones[idx].etiqueta;
  if (actual != opciones[idx].valor) {
    mostrar = (texto_si_otro && *texto_si_otro) ? texto_si_otro : actual.c_str();
  }
  ImGui::PushID(etiqueta);
  ImGui::SetNextWindowSizeConstraints(ImVec2(0.0f, 0.0f),
                                      ImVec2(FLT_MAX, ImGui::GetFrameHeightWithSpacing() * 7.0f));
  if (ImGui::BeginCombo("##combo", mostrar)) {
    for (int i = 0; i < cuenta; ++i) {
      const bool sel = (i == idx);
      if (ImGui::Selectable(opciones[i].etiqueta, sel)) {
        al_cambiar(opciones[i].valor);
      }
      if (sel) {
        ImGui::SetItemDefaultFocus();
      }
    }
    ImGui::EndCombo();
  }
  ImGui::PopID();
  ImGui::SameLine();
  ImGui::TextUnformatted(etiqueta);
}

}  // namespace

NfsmwMenuDialog::NfsmwMenuDialog(rex::ui::ImGuiDrawer* drawer, Callbacks callbacks)
    : rex::ui::ImGuiDialog(drawer), callbacks_(std::move(callbacks)) {}

NfsmwMenuDialog::~NfsmwMenuDialog() = default;

void NfsmwMenuDialog::RequestClose() { Close(); }

void NfsmwMenuDialog::Persistir() {
  if (callbacks_.persist_config) {
    callbacks_.persist_config();
  }
}

void NfsmwMenuDialog::OnClose() {
  if (callbacks_.on_closed) {
    callbacks_.on_closed();
  }
  if (quit_requested_ && callbacks_.request_quit) {
    callbacks_.request_quit();
  }
}

void NfsmwMenuDialog::OnDraw(ImGuiIO& io) {
  if (ImGui::IsKeyPressed(ImGuiKey_UpArrow)) {
    selected_tab_ = (selected_tab_ + kNumPestanas - 1) % kNumPestanas;
  }
  if (ImGui::IsKeyPressed(ImGuiKey_DownArrow)) {
    selected_tab_ = (selected_tab_ + 1) % kNumPestanas;
  }

  const ImVec2 pantalla = io.DisplaySize;
  const float ancho = std::floor(std::min(pantalla.x * 0.90f, 800.0f));
  const float alto = std::floor(std::min(pantalla.y * 0.88f, 600.0f));
  const ImVec2 origen((pantalla.x - ancho) * 0.5f, (pantalla.y - alto) * 0.5f);

  ImGui::PushStyleVar(ImGuiStyleVar_WindowPadding, ImVec2(0.0f, 0.0f));
  ImGui::PushStyleVar(ImGuiStyleVar_WindowRounding, 0.0f);
  const ImGuiWindowFlags flags =
      ImGuiWindowFlags_NoTitleBar | ImGuiWindowFlags_NoResize | ImGuiWindowFlags_NoMove |
      ImGuiWindowFlags_NoScrollbar | ImGuiWindowFlags_NoScrollWithMouse |
      ImGuiWindowFlags_NoBackground | ImGuiWindowFlags_NoBringToFrontOnFocus |
      ImGuiWindowFlags_NoNav;
  ImGui::SetNextWindowPos(origen);
  ImGui::SetNextWindowSize(ImVec2(ancho, alto));
  if (!ImGui::Begin("##nfsmw_menu", nullptr, flags)) {
    ImGui::End();
    ImGui::PopStyleVar(2);
    return;
  }

  const float pad = 18.0f;
  const float borde = 2.0f;
  const float cabecera = 56.0f;
  const float pie = 30.0f;
  const float carril = 130.0f;

  ImDrawList* dl = ImGui::GetWindowDrawList();
  const ImVec2 x0 = origen;
  const ImVec2 x1(origen.x + ancho, origen.y + alto);

  // Fondo y marco.
  dl->AddRectFilled(x0, x1, kBg, 8.0f);
  dl->AddRect(x0, x1, kBorde, 8.0f, 0, borde);
  dl->AddRectFilled(ImVec2(x0.x + borde, x0.y + borde),
                    ImVec2(x1.x - borde, x0.y + cabecera), IM_COL32(26, 30, 37, 255));

  // Cabecera.
  dl->AddText(ImGui::GetFont(), 26.0f,
              ImVec2(x0.x + pad, x0.y + pad - 6.0f), kTexto, "AJUSTES");
  dl->AddText(ImGui::GetFont(), 26.0f,
              ImVec2(x1.x - pad - std::min(ancho * 0.42f, 360.0f), x0.y + pad - 6.0f), kAcento,
              "NFS MOST WANTED");
  dl->AddLine(ImVec2(x0.x + pad, x0.y + cabecera), ImVec2(x1.x - pad, x0.y + cabecera), kMarco,
              borde);

  // Pie: accesos rapidos, por si los botones de la pestana SISTEMA no se ven.
  const float y_pie = x1.y - pie;
  dl->AddLine(ImVec2(x0.x + pad, y_pie), ImVec2(x1.x - pad, y_pie), kMarco, borde);
  dl->AddText(ImGui::GetFont(), 14.0f, ImVec2(x0.x + pad, y_pie + 6.0f), kTextoAtenuado,
              "Flechas +/ - cambian de sección   |   ESC cierra");

  // Carril de pestanas a la izquierda.
  const float y_carril = x0.y + cabecera;
  for (int i = 0; i < kNumPestanas; ++i) {
    const float y_i = y_carril + static_cast<float>(i) * 46.0f;
    const bool sel = (i == selected_tab_);
    if (sel) {
      dl->AddRectFilled(ImVec2(x0.x + borde, y_i), ImVec2(x0.x + carril, y_i + 40.0f), kTabSel);
      dl->AddRectFilled(ImVec2(x0.x + borde, y_i), ImVec2(x0.x + 6.0f, y_i + 40.0f), kAcento);
    }
    dl->AddText(ImGui::GetFont(), 20.0f,
                ImVec2(x0.x + 16.0f, y_i + 8.0f), sel ? kTexto : kTextoAtenuado,
                kTitulosPestana[i]);
    ImGui::SetCursorScreenPos(ImVec2(x0.x + borde, y_i));
    if (ImGui::InvisibleButton(
            (std::string("##pestana") + std::to_string(i)).c_str(),
            ImVec2(carril - borde, 40.0f))) {
      selected_tab_ = i;
    }
  }

  // Contenido, a la derecha del carril.
  ImGui::SetCursorScreenPos(ImVec2(x0.x + carril + pad, y_carril + 8.0f));
  const ImVec2 tam_contenido(ancho - carril - 2.0f * pad, alto - cabecera - pie - 16.0f);
  ImGui::BeginChild("##nfsmw_contenido", tam_contenido, false, ImGuiWindowFlags_NoBackground);

  ImGui::PushStyleVar(ImGuiStyleVar_FrameRounding, 4.0f);
  ImGui::PushStyleVar(ImGuiStyleVar_FramePadding, ImVec2(8.0f, 6.0f));
  ImGui::PushStyleColor(ImGuiCol_FrameBg, kFondoWidget);
  ImGui::PushStyleColor(ImGuiCol_FrameBgHovered, IM_COL32(48, 56, 66, 255));
  ImGui::PushStyleColor(ImGuiCol_Text, kTexto);
  ImGui::PushStyleColor(ImGuiCol_TextDisabled, kTextoAtenuado);
  ImGui::PushStyleColor(ImGuiCol_CheckMark, kAcento);
  ImGui::PushStyleColor(ImGuiCol_Header, IM_COL32(48, 56, 66, 255));
  ImGui::PushStyleColor(ImGuiCol_HeaderHovered, IM_COL32(58, 66, 78, 255));
  ImGui::PushStyleColor(ImGuiCol_SliderGrab, kAcento);
  ImGui::PushStyleColor(ImGuiCol_SliderGrabActive, kAcento);

  if (selected_tab_ == 0) {
    ImGui::TextUnformatted("PANTALLA");
    ImGui::Spacing();

    // Pantalla completa: en vivo (callback de ReXApp::SetupPresentation).
    bool completo = CvarB("fullscreen");
    if (ImGui::Checkbox("Pantalla completa", &completo)) {
      SetCvarB("fullscreen", completo);
      Persistir();
    }
    MarcaVivo("se aplica al instante");

    // V-Sync: el parche del presentador lo lee en cada fotograma.
    bool vsync = CvarB("vsync");
    if (ImGui::Checkbox("V-Sync", &vsync)) {
      SetCvarB("vsync", vsync);
      Persistir();
    }
    MarcaVivo("se aplica al instante");

    if (ExisteCvar("max_fps")) {
      static const Opcion kFps[] = {
          {"30 FPS", "30"}, {"60 FPS", "60"}, {"120 FPS", "120"},
          {"144 FPS", "144"}, {"180 FPS", "180"}, {"Sin límite", "0"}};
      ComboSimple("Límite de fotogramas por segundo", CvarS("max_fps"), kFps, 6, nullptr,
                  [this](const char* v) {
                    SetCvarS("max_fps", v);
                    Persistir();
                  });
      MarcaVivo("se aplica al instante");
    }

    ImGui::Spacing();
    ImGui::Separator();
    ImGui::Spacing();

    ImGui::TextUnformatted("RESOLUCIÓN Y NITIDEZ");
    ImGui::Spacing();

    static const Opcion kRes[] = {
        {"720p", "720p"}, {"900p", "900p"}, {"1080p", "1080p"},
        {"1440p", "1440p"}, {"1800p", "1800p"}, {"4K (2160p)", "4k"}};
    ComboSimple("Resolución de ventana y modo de vídeo", CvarS("resolution"), kRes, 6,
                "Personalizada", [this](const char* v) {
                  SetCvarS("resolution", v);
                  Persistir();
                });
    MarcaReinicio();

    static const Opcion kIRes[] = {
        {"1x - 720p (nativo)", "1"},
        {"2x - 1440p (4 veces los píxeles)", "2"},
        {"3x - 2160p 4K (9 veces los píxeles)", "3"},
        {"4x - 2880p (16 veces los píxeles)", "4"}};
    static const char kEtiquetaIRes[] = "Resolución interna (supersampling real del motor)";
    const std::string escala = CvarS("resolution_scale");
    ComboSimple(kEtiquetaIRes, escala, kIRes, 4, nullptr, [this](const char* v) {
      SetCvarS("resolution_scale", v);
      Persistir();
    });
    MarcaReinicioConAviso(
        "Escala entera de los render targets del juego: más píxeles cada fotograma, "
        "no un estirado. Con 2x y el foco desactivado se ve nítido sin coste de nitidez.");

    ImGui::Spacing();
    ImGui::Separator();
    ImGui::Spacing();

    ImGui::TextUnformatted("CALIDAD DE IMAGEN");
    ImGui::Spacing();

    if (ExisteCvar("anisotropic_override")) {
      static const Opcion kAniso[] = {{"Off (bilinear)", "0"}, {"1x", "1"}, {"2x", "2"},
                                      {"4x", "3"}, {"8x", "4"}, {"16x", "5"}};
      ComboSimple("Filtrado anisotrópico", CvarS("anisotropic_override"), kAniso, 6, nullptr,
                  [this](const char* v) {
                    SetCvarS("anisotropic_override", v);
                    Persistir();
                  });
      MarcaVivo("se aplica al instante");
    }

    if (ExisteCvar("swap_post_effect")) {
      static const Opcion kAA[] = {{"Off", "none"}, {"FXAA", "fxaa"}, {"FXAA Extreme", "fxaa_extreme"}};
      ComboSimple("Anti-aliasing", CvarS("swap_post_effect"), kAA, 3, nullptr, [this](const char* v) {
        SetCvarS("swap_post_effect", v);
        Persistir();
      });
      MarcaReinicio();
    }

    if (ExisteCvar("gpu_backend")) {
      static const Opcion kApi[] = {{"Direct3D 12", "d3d12"}, {"Vulkan", "vulkan"}};
      ComboSimple("API gráfica", CvarS("gpu_backend"), kApi, 2, nullptr, [this](const char* v) {
        SetCvarS("gpu_backend", v);
        Persistir();
      });
      MarcaReinicio();
    }

    const auto pendientes = rex::cvar::GetPendingRestartFlags();
    const bool hay_pendientes = !pendientes.empty();
    if (hay_pendientes) {
      ImGui::Spacing();
      ImGui::Separator();
      ImGui::Spacing();
      ImGui::TextColored(ImColor(kAviso),
                         "Los cambios de esta sección se aplican al reiniciar");
      if (BotonAplicar()) {
        Persistir();
        if (callbacks_.request_restart) {
          callbacks_.request_restart();
        }
      }
    }

  } else if (selected_tab_ == 1) {
    ImGui::TextUnformatted("CONTENIDO");
    ImGui::Spacing();

    bool black = CvarB("black_edition");
    if (ImGui::Checkbox("Contenido Black Edition", &black)) {
      SetCvarB("black_edition", black);
      Persistir();
    }
    MarcaReinicioConAviso(
        "Desbloquea los coches de pago (edición Black) como descargables en el "
        "concesionario del garaje.");

    if (ExisteCvar("grant_user_privileges")) {
      bool gp = CvarB("grant_user_privileges");
      if (ImGui::Checkbox("Privilegios de usuario (acceso online)", &gp)) {
        SetCvarB("grant_user_privileges", gp);
        Persistir();
      }
      MarcaReinicio();
    }

    ImGui::Spacing();
    ImGui::Separator();
    ImGui::Spacing();

    ImGui::TextUnformatted("XBOX LIVE (SIMULADO)");
    ImGui::Spacing();

    if (!gamertag_sync_) {
      const auto actual = CvarS("user_profile_name");
      std::memset(gamertag_, 0, sizeof(gamertag_));
      const size_t copia = std::min<size_t>(actual.size(), sizeof(gamertag_) - 1);
      std::copy(actual.begin(), actual.begin() + copia, gamertag_);
      gamertag_sync_ = true;
    }
    ImGui::SetNextItemWidth(340.0f);
    if (ImGui::InputText("Gamertag del perfil", gamertag_, sizeof(gamertag_))) {
      rex::cvar::SetFlagByName("user_profile_name", gamertag_);
    }
    if (ImGui::IsItemDeactivatedAfterEdit()) {
      Persistir();
    }
    MarcaVivo("en vivo: el juego lo lee cada vez que pide el perfil");

    ImGui::TextColored(
        ImColor(kTextoAtenuado),
        "Sesion simulada: usuario 0 firmado, membresia Gold, XUID 0x00B13EBABEBABEBE, "
        "perfil local y online.");
    ImGui::TextColored(
        ImColor(kTextoAtenuado),
        "Cuando el juego pida escribir algo (un nombre, un perfil nuevo), el recomp "
        "abre su propio teclado en pantalla: escribe y pulsa OK. La guia de Xbox "
        "siempre se considera cerrada, asi que ninguna pantalla se queda esperandola.");
    ImGui::TextColored(ImColor(kTextoAtenuado),
                       "Multijugador online: servidores de EA apagados; la unica vía "
                       "que queda es System Link, y no esta implementado aun.");
    ImGui::Spacing();

    ImGui::Separator();
    ImGui::Spacing();

    ImGui::TextUnformatted("JUEGO");
    ImGui::Spacing();

    if (ExisteCvar("game_speed")) {
      float velocidad = CvarF("game_speed");
      if (ImGui::SliderFloat("Velocidad del juego", &velocidad, 20.0f, 200.0f, "%.0f%%")) {
        velocidad = std::clamp(velocidad, 20.0f, 200.0f);
        SetCvarF("game_speed", velocidad);
      }
      if (ImGui::IsItemDeactivatedAfterEdit()) {
        Persistir();
      }
      MarcaVivo("en vivo: también con el menú cerrado, hasta que se vuelva a tocar o se cierre el juego");
    }

    ImGui::Spacing();
    ImGui::Separator();
    ImGui::Spacing();

    ImGui::TextColored(ImColor(kTextoAtenuado),
                       "Tip: el menú de ajustes del recomp (F3 y F4) tiene todas las "
                       "opciones técnicas; este menú es el resumen que se usa a diario.");

  } else if (selected_tab_ == 2) {
    ImGui::TextUnformatted("APLICACIÓN");
    ImGui::Spacing();

    const auto pendientes = rex::cvar::GetPendingRestartFlags();
    if (pendientes.empty()) {
      ImGui::TextColored(ImColor(kVivo), "No hay cambios pendientes de reinicio.");
    } else {
      ImGui::TextColored(ImColor(kAviso), "Cambios pendientes de reinicio:");
      ImGui::TextWrapped("%s", JuntarLista(pendientes).c_str());
    }

    ImGui::Spacing();
    ImGui::Separator();
    ImGui::Spacing();

    if (ImGui::Button("REANUDAR", ImVec2(240.0f, 0.0f))) {
      Close();
    }
    if (ImGui::Button("GUARDAR CONFIGURACIÓN", ImVec2(240.0f, 0.0f))) {
      Persistir();
    }
    if (ImGui::Button("RESTAURAR VALORES POR DEFECTO", ImVec2(240.0f, 0.0f))) {
      rex::cvar::ResetAllToDefaults();
      Persistir();
    }
    if (BotonAplicar()) {
      Persistir();
      if (callbacks_.request_restart) {
        callbacks_.request_restart();
      }
    }
    if (ImGui::Button("SALIR AL ESCRITORIO", ImVec2(240.0f, 0.0f))) {
      quit_requested_ = true;
      Persistir();
      Close();
    }
  } else {
    // DEBUG -----------------------------------------------------------------
    ImGui::TextUnformatted("RENDIMIENTO");
    ImGui::Spacing();

    if (callbacks_.sample_fps) {
      const auto stats = callbacks_.sample_fps();
      ImGui::Text("  FPS del juego: %.1f", stats.fps);
      ImGui::Text("  Tiempo de fotograma: %.2f ms", stats.frame_time_ms);
      ImGui::TextColored(
          ImColor(kTextoAtenuado),
          "El medidor avanza mientras este menu esta abierto: deja un momento.");
    }

    ImGui::Spacing();
    ImGui::Separator();
    ImGui::Spacing();

    ImGui::TextUnformatted("GRÁFICAS");
    ImGui::Spacing();
    FilaDebug("Backend gráfico", CvarS("gpu_backend"));
    FilaDebug("Plugin GPU", CvarS("gpu_plugin"));
    FilaDebug("Camino EDRAM", CvarS("render_target_path_d3d12"));
    FilaDebug("Anti-aliasing", CvarS("swap_post_effect"));
    FilaDebug("Lectura de exposición", CvarS("readback_resolve"));

    ImGui::Spacing();
    ImGui::Separator();
    ImGui::Spacing();

    ImGui::TextUnformatted("VÍDEO");
    ImGui::Spacing();
    FilaDebug("Modo de vídeo", CvarS("video_mode_width") + "x" + CvarS("video_mode_height"));
    FilaDebug("Escala interna", CvarS("resolution_scale"));
    FilaDebug("Ventana", CvarS("window_width") + "x" + CvarS("window_height"));
    FilaDebug("Pantalla completa", CvarS("fullscreen"));
    FilaDebug("Anisotropía", CvarS("anisotropic_override"));

    ImGui::Spacing();
    ImGui::Separator();
    ImGui::Spacing();

    ImGui::TextUnformatted("SISTEMA");
    ImGui::Spacing();
    FilaDebug("V-Sync", CvarS("vsync"));
    if (ExisteCvar("max_fps")) {
      FilaDebug("Límite de FPS", CvarS("max_fps"));
    }
    if (ExisteCvar("game_speed")) {
      FilaDebug("Velocidad del juego", CvarS("game_speed"));
    }
    FilaDebug("Gamertag", CvarS("user_profile_name"));
    FilaDebug("Black Edition", CvarS("black_edition"));
    if (ExisteCvar("grant_user_privileges")) {
      FilaDebug("Privilegios online", CvarS("grant_user_privileges"));
    }

    ImGui::Spacing();
    ImGui::Separator();
    ImGui::Spacing();

    const auto pendientes = rex::cvar::GetPendingRestartFlags();
    if (pendientes.empty()) {
      ImGui::TextColored(ImColor(kVivo), "Sin cambios pendientes de reinicio.");
    } else {
      ImGui::TextColored(ImColor(kAviso), "Reinicio pendiente para:");
      ImGui::TextWrapped("%s", JuntarLista(pendientes).c_str());
    }

    ImGui::Spacing();
    ImGui::Separator();
    ImGui::Spacing();

    ImGui::TextColored(
        ImColor(kTextoAtenuado),
        "F3 abre el panel de depuracion del runtime y F4 todos los ajustes tecnicos "
        "(cvars). Este menu es el resumen de lo que se usa a diario.");
  }

  ImGui::PopStyleColor(9);
  ImGui::PopStyleVar(2);
  ImGui::EndChild();

  ImGui::End();
  ImGui::PopStyleVar(2);
}

// ---------------------------------------------------------------------------
//  Helpers de dibujo (deben verse llamados dentro de OnDraw).
// ---------------------------------------------------------------------------
void NfsmwMenuDialog::MarcaVivo(const char* texto) {
  // "%s" y no el texto como formato: un "%" en el texto lo romperia, y el NDK
  // de Android lo trata como error (-Werror=format-security).
  ImGui::TextColored(ImColor(kVivo), "%s", texto);
  ImGui::Spacing();
}

void NfsmwMenuDialog::MarcaReinicio(const char* texto) {
  ImGui::TextColored(ImColor(kAviso), "%s", (texto && *texto) ? texto : "(se aplica al reiniciar)");
  ImGui::Spacing();
}

void NfsmwMenuDialog::MarcaReinicioConAviso(const char* texto) {
  ImGui::TextColored(ImColor(kAviso), "Reinicia para que tenga efecto.");
  ImGui::TextColored(ImColor(kTextoAtenuado), "%s", texto);
  ImGui::Spacing();
}

bool NfsmwMenuDialog::BotonAplicar() {
  return ImGui::Button("APLICAR Y REINICIAR", ImVec2(240.0f, 0.0f));
}