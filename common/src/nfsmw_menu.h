// nfsmw - menu de ajustes ingame (estilo GoldenEye, abierto con ESC)
//
// Se apoya en el dialogo de ImGui del SDK: al construirse se registra solo
// (ImGuiDrawer::AddDialog) y al llamar a Close() se cierra y se borra solo
// (ImGuiDialog::Draw). La app no necesita poseerlo: guarda un puntero puro que
// se anula con on_closed.

#pragma once

#include <rex/ui/imgui_dialog.h>
#include <rex/ui/overlay/debug_overlay.h>

#include <functional>

class NfsmwMenuDialog : public rex::ui::ImGuiDialog {
 public:
  struct Callbacks {
    std::function<void()> persist_config;      // SaveConfig en nfsmw.toml
    std::function<void()> request_restart;     // guardar + relanzar el .exe
    std::function<void()> request_quit;        // cerrar la ventana
    std::function<void()> on_closed;           // avisar a la app (anula su puntero)
    std::function<rex::ui::FrameStats()> sample_fps;  // medidor del overlay F3
  };

  NfsmwMenuDialog(rex::ui::ImGuiDrawer* drawer, Callbacks callbacks);
  ~NfsmwMenuDialog() override;

  void RequestClose();

 protected:
  void OnDraw(ImGuiIO& io) override;
  void OnClose() override;

 private:
  void Persistir();
  static void MarcaVivo(const char* texto);
  static void MarcaReinicio(const char* texto = nullptr);
  static void MarcaReinicioConAviso(const char* texto);
  static bool BotonAplicar();

  Callbacks callbacks_;
  int selected_tab_ = 0;
  bool quit_requested_ = false;

  char gamertag_[16];  // 15 caracteres + nulo, como un gamertag de Xbox Live
  bool gamertag_sync_ = false;
};