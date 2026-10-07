// nfsmw - ReXGlue Recompiled Project
//
// Customize your app by overriding virtual hooks from rex::ReXApp.

#pragma once

// Windows primero y reducido a proposito: las cabeceras de rex no esperan que
// windows.h haya dejado macros por medio.
#if defined(_WIN32)
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <shellapi.h>
#endif

#include "nfsmw_menu.h"

#include <rex/cvar.h>
#include <rex/filesystem.h>
#include <rex/logging.h>
#include <rex/rex_app.h>
#include <rex/ui/overlay/debug_overlay.h>
#include <rex/ui/keybinds.h>  // RegisterBind/UnregisterBind (tecla ESC del menu)
#include <rex/system/kernel_state.h>       // VIGILANTE DE CUELGUES
#include <rex/system/util/object_table.h>  // VIGILANTE DE CUELGUES - que espera cada hilo
#include <rex/system/xmemory.h>            // TranslateVirtual (parche Black Edition)
#include <rex/system/xobject.h>            // VIGILANTE DE CUELGUES - que espera cada hilo
#include <rex/system/xthread.h>            // VIGILANTE DE CUELGUES

#include <algorithm>
#include <atomic>
#include <chrono>
#include <filesystem>
#include <map>  // VIGILANTE DE CUELGUES - la firma se ordena por id de hilo
#include <string>
#include <thread>
#include <vector>

// Cvar "Contenido > black_edition", definido en nfsmw_menu.cpp.
REXCVAR_DECLARE(bool, black_edition);

class NfsmwApp : public rex::ReXApp {
 public:
  using rex::ReXApp::ReXApp;

  static std::unique_ptr<rex::ui::WindowedApp> Create(
      rex::ui::WindowedAppContext& ctx) {
    return std::unique_ptr<NfsmwApp>(new NfsmwApp(ctx, "nfsmw",
        PPCImageConfig));
  }

  // Ganchos disponibles y sin usar:
  //   void OnPreSetup(rex::RuntimeConfig& config) override {}
  //   void OnLoadXexImage(std::string& xex_image) override {}
  //
  // Los ganchos usados: rutas portables, ajustes obligatorios, contador de fps,
  // el parche Black Edition (OnPostLoadXexImage) y el menu de ajustes con ESC
  // (OnCreateDialogs).

 protected:
  // ==========================================================================
  //  1. RUTAS PORTABLES: encontrar la ISO al lado del .exe
  //
  //  Sin esto, arrancar sin --game_data_root muere con
  //      "--game_data_root was not provided."
  //  porque SetupEnvironment solo mira el cvar y, si esta vacio,
  //  ConstructRuntime aborta.
  //
  //  OnConfigurePaths se llama justo despues de construir el PathConfig y
  //  antes de que nadie lo use, asi que es el sitio para rellenar el hueco.
  //
  //  ORDEN, QUE IMPORTA: esto corre ANTES de que se cargue nfsmw.toml -el SDK
  //  lo lee unas lineas mas abajo, en SetupEnvironment-. Asi que la prioridad
  //  real es: --game_data_root de la linea de comandos, y si no, lo que se
  //  encuentre aqui al lado. Poner game_data_root en el toml NO funciona, y
  //  no es cosa nuestra: es como esta ordenado el SDK.
  //
  //  Se busca, en este orden:
  //    1. un .iso cuyo nombre coincida con el del ejecutable
  //    2. cualquier otro .iso de la carpeta, por orden alfabetico
  //    3. una carpeta game_root\, por si alguien prefiere extraerla
  //
  //  El (1) existe para que una carpeta con NFS_Most_Wanted.exe y
  //  NFS_Most_Wanted.iso funcione sin ambiguedad aunque haya mas imagenes.
  // ==========================================================================
  void OnConfigurePaths(rex::PathConfig& paths) override {
    if (!paths.game_data_root.empty()) {
      return;  // el usuario lo dijo por linea de comandos; manda el.
    }

    std::error_code ec;
    const auto carpeta = rex::filesystem::GetExecutableFolder();
    if (carpeta.empty() || !std::filesystem::is_directory(carpeta, ec)) {
      return;
    }

    // El nombre del ejecutable, para el caso preferente.
    std::filesystem::path preferida;
    std::vector<std::filesystem::path> otras;

    std::string yo;
    {
      const auto exe = rex::filesystem::GetExecutablePath();
      if (!exe.empty()) {
        yo = exe.stem().string();
        std::transform(yo.begin(), yo.end(), yo.begin(),
                       [](unsigned char c) { return char(std::tolower(c)); });
      }
    }

    for (const auto& e : std::filesystem::directory_iterator(carpeta, ec)) {
      if (ec) break;
      if (!e.is_regular_file(ec)) continue;

      std::string ext = e.path().extension().string();
      std::transform(ext.begin(), ext.end(), ext.begin(),
                     [](unsigned char c) { return char(std::tolower(c)); });
      if (ext != ".iso") continue;

      std::string base = e.path().stem().string();
      std::transform(base.begin(), base.end(), base.begin(),
                     [](unsigned char c) { return char(std::tolower(c)); });

      if (!yo.empty() && base == yo) {
        preferida = e.path();
      } else {
        otras.push_back(e.path());
      }
    }

    if (!preferida.empty()) {
      paths.game_data_root = preferida;
    } else if (!otras.empty()) {
      std::sort(otras.begin(), otras.end());
      paths.game_data_root = otras.front();
    } else {
      // Sin ISO: una carpeta extraida al lado tambien vale. El parche de la
      // ISO dejo --game_data_root aceptando las dos cosas.
      const auto extraida = carpeta / "game_root";
      if (std::filesystem::is_directory(extraida, ec)) {
        paths.game_data_root = extraida;
      }
    }
    // Si no se encuentra nada, se deja vacio a proposito: el SDK dara su
    // propio mensaje, que es mas claro que cualquiera que pusieramos aqui.
  }

  // ==========================================================================
  //  2. AJUSTES OBLIGATORIOS
  //
  //  Para que "NFS_Most_Wanted.exe" a secas, sin un solo argumento, arranque
  //  igual de bien que con la linea de comandos larga de siempre.
  //
  //  Solo se tocan los que el usuario NO haya puesto: HasNonDefaultValue
  //  distingue "esto viene de fabrica" de "esto lo pidio alguien". Asi la
  //  linea de comandos y nfsmw.toml siguen mandando.
  //
  //  POR QUE EN DOS SITIOS DISTINTOS
  //  El cvar readback_resolve no existe todavia cuando arranca el logging: lo
  //  registra el plugin de GPU (rexgpu-xenos.dll), que se carga despues, en
  //  SetupPresentation. Ponerlo antes seria escribir sobre un flag que aun no
  //  existe. Por eso:
  //
  //    OnPostInitLogging  -> gpu_plugin y mnk_mode, que son del runtime y ya
  //                          estan registrados. Y tiene que ser AQUI, porque
  //                          SetupPresentation lee gpu_plugin justo despues.
  //    OnPostSetup        -> readback_resolve, cuando el plugin ya cargo y
  //                          todavia no se ha dibujado ni un fotograma.
  // ==========================================================================
  void OnPostInitLogging() override {
    // Sin plugin de GPU la pantalla se queda negra: el juego corre, pero el
    // runtime descarta sus llamadas graficas con "no GPU emulation loaded".
    PonerSiNadieLoPidio("gpu_plugin", "xenos");
    // Teclado y raton ademas del mando.
    PonerSiNadieLoPidio("mnk_mode", "true");
  }

  void OnPostSetup() override {
    // NO ES UNA PREFERENCIA, ES UN ARREGLO. El juego calcula su exposicion
    // midiendo el brillo medio de la escena y leyendo ese valor de vuelta en
    // la CPU. Esa lectura viene desactivada de fabrica ("none"), asi que el
    // juego recibe basura, deduce que la escena esta oscurisima y sube la
    // exposicion al maximo: imagen lavada y sol reventado.
    PonerSiNadieLoPidio("readback_resolve", "fast");

    // Contador de fps del overlay de F3, ver mas abajo.
    SetGuestFrameStats([this] { return MuestreaFotograma(); });

    // Vigilante de cuelgues, ver mas abajo.
    ArrancarVigilante();
  }

  // ==========================================================================
  //  2b. PARCHE BLACK EDITION (NATIVO)
  //
  //  En la edicion PAL (454107D9) hay una bandera en 0x82A2CE04 que decide si
  //  vender los coches de pago (edicion Black) como descargables o no. Xenia
  //  la activaba con  data_write(be32, 0x82a2ce04, 0x00000100); aqui se pisa
  //  directamente la memoria del guest.
  //
  //  La memoria gestionada por memoria::Memory se expone en big-endian: el
  //  offset 0 es el byte mas significativo. Por eso basta escribir el valor
  //  tal cual (0x00000100), sin endian-swap: es lo mismo que hacia la patch
  //  .toml con el archivo del XEX parcheado.
  //
  //  Se puede apagar desde el menu (Contenido > Black Edition), pero solo se
  //  aplica en la carga siguiente: esta funcion corre cada vez que se carga
  //  el XEX, sea al arrancar o al releer la imagen.
  // ==========================================================================
  void OnPostLoadXexImage() override { AplicarParcheBlackEdition(); }

  // ==========================================================================
  //  2c. MENU DE AJUSTES CON ESC
  //
  //  Al igual que F3 (depuracion) y F4 (ajustes tecnicos), se registra una
  //  tecla y el dialogo se crea y se destruye con ella (los dialogos de ImGui
  //  del SDK se registran solos en el drawer al construirse y se borran solos
  //  al cerrarse; solo hay que guardar el puntero y anularlo con on_closed).
  //
  //  La tecla quedo asignada a Escape. Se puede volver a ligar desde F4
  //  (Seccion "Keybinds").
  // ==========================================================================
  void OnCreateDialogs(rex::ui::ImGuiDrawer* drawer) override {
    rex::ui::RegisterBind("bind_nfsmw_menu", "Escape",
                          "Abrir/cerrar menu de ajustes del juego",
                          [this] { AlternarMenu(); });
  }

  void OnShutdown() override {
    PararVigilante();
    rex::ui::UnregisterBind("bind_nfsmw_menu");
    if (menu_ != nullptr) {
      menu_->RequestClose();
      menu_ = nullptr;
    }
  }

 private:
  static void PonerSiNadieLoPidio(const char* nombre, const char* valor) {
    if (rex::cvar::GetFlagInfo(nombre) == nullptr) {
      REXLOG_DEBUG("Ajuste '{}' no registrado todavia; no lo toco.", nombre);
      return;
    }
    if (rex::cvar::HasNonDefaultValue(nombre)) {
      return;  // lo puso el usuario: no se le lleva la contraria.
    }
    if (rex::cvar::SetFlagByName(nombre, valor)) {
      REXLOG_DEBUG("Ajuste por defecto de la build portable: {} = {}", nombre, valor);
    }
  }

  // ==========================================================================
  //  3. CONTADOR DE FPS PARA EL OVERLAY DE F3
  //
  //  En una build RELEASE, F3 abre una caja vacia que solo pone "Debug". Son
  //  dos cosas distintas y las dos estaban cerradas:
  //
  //    1. Casi todo el panel vive dentro de #ifdef REXGLUE_ENABLE_PERF_COUNTERS,
  //       y el CMakeLists del SDK dice
  //         add_compile_definitions($<$<NOT:$<CONFIG:Release>>:REXGLUE_ENABLE_PERF_COUNTERS>)
  //       o sea que en Release el define no se aplica. Es a proposito:
  //       "compiled out in Release", dice su comentario.
  //
  //    2. La linea "Guest: X FPS" NO esta dentro de ese #ifdef. Solo pide que
  //       alguien registre un proveedor con SetGuestFrameStats, y en el SDK no
  //       lo llama nadie: es una API que la app tiene que usar.
  //
  //  El (2) es la puerta que si se puede abrir sin tocar el SDK.
  //
  //  El proveedor lo llama OnDraw del overlay una vez por fotograma mientras
  //  este abierto, asi que no hace falta ningun gancho de frame: basta con
  //  mirar el reloj cada vez que preguntan. Media movil exponencial, porque el
  //  valor instantaneo salta tanto que no se puede leer ni comparar.
  //
  //  Mide los fotogramas que presenta la ventana. Solo cuenta con el overlay
  //  abierto: al cerrarlo deja de haber llamadas y la media se congela.
  // ==========================================================================
  rex::ui::FrameStats MuestreaFotograma() {
    using Reloj = std::chrono::steady_clock;
    const auto ahora = Reloj::now();

    const double dt_ms =
        std::chrono::duration<double, std::milli>(ahora - ultimo_).count();
    // Se descarta el primer intervalo y cualquiera absurdo: al reabrir el
    // overlay, el "anterior" abarca todo el rato que estuvo cerrado.
    const bool valido = tiene_anterior_ && dt_ms > 0.0 && dt_ms < 1000.0;

    ultimo_ = ahora;
    tiene_anterior_ = true;
    if (!valido) {
      return stats_;
    }

    suave_ms_ = (suave_ms_ <= 0.0) ? dt_ms : (suave_ms_ * 0.9 + dt_ms * 0.1);
    stats_.frame_time_ms = suave_ms_;
    stats_.fps = (suave_ms_ > 0.0) ? (1000.0 / suave_ms_) : 0.0;
    stats_.frame_count = ++fotogramas_;  // el overlay no dibuja si esto es 0
    return stats_;
  }

  // ==========================================================================
  //  4. VIGILANTE DE CUELGUES
  //
  //  EL PROBLEMA QUE RESUELVE
  //  Al volver al menu el juego se queda congelado, y en el log no aparece
  //  absolutamente nada: ni un error, ni una llamada al kernel, ni un comando
  //  grafico. Silencio total hasta que uno cierra la ventana. Eso descarta una
  //  excepcion o una funcion sin registrar -esas se ven- y deja una sola
  //  explicacion: TODOS los hilos del juego estan parados a la vez, esperando
  //  algo que no llega.
  //
  //  Y de un interbloqueo no se sale mirando el log, porque justamente lo que
  //  lo define es que ya no se escribe nada. Hay que ir a preguntarle a los
  //  hilos.
  //
  //  COMO FUNCIONA, Y POR QUE NO NECESITA QUE NADIE LE AVISE
  //  Un hilo aparte mira una vez por segundo TODOS los hilos del guest y anota
  //  dos registros de cada uno:
  //
  //    lr  a donde volveria la funcion en la que esta. Cambia constantemente
  //        en codigo que avanza.
  //    r1  el puntero de pila. Igual.
  //
  //  Si en varios segundos seguidos NINGUN hilo ha movido ninguno de los dos,
  //  el juego no esta lento: esta parado. Entonces se vuelca la tabla.
  //
  //  Lo bueno de medirlo asi es que no depende de nada: ni del contador de
  //  fotogramas -que solo corre con el overlay abierto-, ni de que el juego
  //  llame al kernel, ni de que el hilo grafico siga vivo. Si todo se para, se
  //  nota justo porque todo se para.
  //
  //  QUE SE SACA DEL VOLCADO
  //  Por cada hilo: su direccion de entrada -que dice QUE hilo es-, lr, r1 y
  //  r13. Con eso se distingue el que espera -lr clavado en una funcion de
  //  espera del kernel- del que da vueltas -lr saltando entre dos o tres
  //  direcciones-. Y como se vuelca cada 15 segundos mientras dure, se ve si
  //  algo se mueve muy despacio o no se mueve en absoluto.
  //
  //  COSTE CUANDO NO PASA NADA
  //  Una pasada por segundo leyendo dos enteros por hilo. Nada.
  //
  //  Vive en la app y no en el SDK a proposito: asi se toca sin recompilar el
  //  SDK entero, y no le impone a nadie mas un hilo de vigilancia.
  // ==========================================================================

  void ArrancarVigilante() {
    vigilante_activo_ = true;
    vigilante_ = std::thread([this] { VigilanteMain(); });
  }

  void PararVigilante() {
    vigilante_activo_ = false;
    if (vigilante_.joinable()) {
      vigilante_.join();
    }
  }

  // Que hay detras del r3 de un hilo parado. En las funciones de espera del
  // kernel r3 es o un handle -NtWaitForSingleObjectEx- o el puntero al objeto
  // del guest -KeWaitForSingleObject-, asi que se prueban los dos. Saber si un
  // hilo espera un evento, un semaforo o un mutex es lo que distingue "el
  // juego espera al disco" de "nadie va a despertar a nadie".
  static std::string DescribirEspera(uint32_t valor) {
    auto* kernel = rex::system::kernel_state();
    if (!kernel || !valor) {
      return {};
    }
    auto nombre_tipo = [](rex::system::XObject::Type t) {
      using Tipo = rex::system::XObject::Type;
      switch (t) {
        case Tipo::Event: return "evento";
        case Tipo::Semaphore: return "semaforo";
        case Tipo::Mutant: return "mutex";
        case Tipo::Timer: return "temporizador";
        case Tipo::Thread: return "hilo";
        case Tipo::File: return "fichero";
        case Tipo::IOCompletion: return "io";
        case Tipo::NotifyListener: return "notificacion";
        default: return "objeto";
      }
    };
    auto describir = [&](const rex::system::XObject& o, const char* como) {
      return fmt::format(" espera {} {}{}{} ({})", nombre_tipo(o.type()),
                         o.name().empty() ? "" : "'", o.name(), o.name().empty() ? "" : "'", como);
    };
    if (auto objeto = kernel->object_table()->LookupObject<rex::system::XObject>(valor)) {
      return describir(*objeto, "handle");
    }
    // Por puntero del guest: no hay indice inverso, pero esto se recorre solo
    // cuando algo ya esta parado.
    using Tipo = rex::system::XObject::Type;
    for (Tipo tipo : {Tipo::Event, Tipo::Semaphore, Tipo::Mutant, Tipo::Timer, Tipo::Thread}) {
      for (auto& objeto : kernel->object_table()->GetObjectsByType<rex::system::XObject>(tipo)) {
        if (objeto->guest_object() == valor) {
          return describir(*objeto, "puntero");
        }
      }
    }
    return {};
  }

  // Volcado de la tabla de hilos. 'grave' decide si sale como error -cuando
  // es una alarma de verdad- o como debug -las instantaneas de rutina-.
  template <typename Lista>
  static void VolcarHilos(const Lista& hilos, bool grave) {
    for (auto& h : hilos) {
      const auto* cp = h->creation_params();
      auto* estado = h->thread_state();
      if (estado && estado->context()) {
        const auto& c = *estado->context();
        if (grave) {
          REXLOG_ERROR("[vigilante]   hilo id=0x{:X} entrada=0x{:08X} principal={} corriendo={} | "
                       "lr=0x{:08X} r1=0x{:08X} r13=0x{:08X} r3=0x{:08X} ctr=0x{:08X} "
                       "ultimo_indirecto=0x{:08X}{}",
                       h->thread_id(), cp->start_address, h->main_thread(), h->is_running(),
                       static_cast<uint32_t>(c.lr), c.r1.u32, c.r13.u32, c.r3.u32, c.ctr.u32,
                       c.last_indirect_target, DescribirEspera(c.r3.u32));
        } else {
          REXLOG_DEBUG("[vigilante]   hilo id=0x{:X} entrada=0x{:08X} principal={} corriendo={} | "
                       "lr=0x{:08X} r1=0x{:08X} r13=0x{:08X} r3=0x{:08X} ctr=0x{:08X} "
                       "ultimo_indirecto=0x{:08X}",
                       h->thread_id(), cp->start_address, h->main_thread(), h->is_running(),
                       static_cast<uint32_t>(c.lr), c.r1.u32, c.r13.u32, c.r3.u32, c.ctr.u32,
                       c.last_indirect_target);
        }
      } else {
        REXLOG_DEBUG("[vigilante]   hilo id=0x{:X} entrada=0x{:08X} sin contexto", h->thread_id(),
                     cp->start_address);
      }
    }
  }

  void VigilanteMain() {
    using Reloj = std::chrono::steady_clock;

    // Cuantos segundos seguidos sin que se mueva NADA antes de dar la voz de
    // alarma. Cinco es holgado: este juego a 10 fps sigue moviendo registros
    // cien veces por segundo, asi que cinco segundos quietos no son lentitud.
    constexpr int kSegundosParaSospechar = 5;
    constexpr int kSegundosEntreVolcados = 15;

    uint64_t firma_anterior = 0;
    int quietos = 0;
    int desde_ultimo_volcado = 0;
    int desde_instantanea = 0;
    bool avisado = false;

    while (vigilante_activo_) {
      std::this_thread::sleep_for(std::chrono::seconds(1));
      if (!vigilante_activo_) break;

      auto* kernel = rex::system::kernel_state();
      if (!kernel) continue;

      auto hilos = kernel->object_table()->GetObjectsByType<rex::system::XThread>();
      if (hilos.empty()) continue;

      // Una firma de "por donde va todo el mundo". No hace falta que sea
      // buena como hash: solo tiene que cambiar si cambia algun registro.
      //
      // OJO CON EL ORDEN. La primera version de esto multiplicaba y mezclaba
      // sobre la marcha, recorriendo la lista tal cual venia. Y GetObjectsByType
      // NO garantiza el orden: en los volcados reales los hilos salian barajados
      // de una vuelta a otra, y hasta repetidos -el 0x6 aparecia dos veces-. O
      // sea que la firma cambiaba sola aunque no se moviera nada, y la alarma
      // no salto NUNCA en el cuelgue de verdad. Lo unico que sirvio de algo
      // fueron las instantaneas periodicas de mas abajo.
      //
      // Se arregla metiendo cada hilo en un mapa por su id: el mapa ordena
      // solo, asi que el barajado deja de importar, y un id repetido se
      // machaca en vez de contarse dos veces. Recien entonces se mezcla.
      std::map<uint32_t, uint64_t> por_hilo;
      for (auto& h : hilos) {
        auto* estado = h->thread_state();
        if (!estado || !estado->context()) continue;
        const auto& c = *estado->context();
        por_hilo[h->thread_id()] =
            static_cast<uint64_t>(c.lr) ^ (static_cast<uint64_t>(c.r1.u32) << 20) ^
            (static_cast<uint64_t>(c.r3.u32) << 40);
      }

      uint64_t firma = 1469598103934665603ull;
      for (const auto& [id_hilo, huella] : por_hilo) {
        firma = (firma ^ id_hilo) * 1099511628211ull;
        firma = (firma ^ huella) * 1099511628211ull;
      }

      // INSTANTANEA PERIODICA, PASE LO QUE PASE.
      //
      // La alarma de arriba solo salta si NADA se mueve, y resulto que el
      // cuelgue que perseguimos no es de ese tipo: los registros seguian
      // cambiando, o sea que el juego ejecuta codigo pero no avanza. Un bucle
      // cerrado esperando algo que no llega se ve igual de parado por fuera y
      // sin embargo la alarma no lo pilla.
      //
      // Para eso esta esto: cada diez segundos se apunta por donde va cada
      // hilo, haya o no problema. Cuando el juego se congela, quedan dos o
      // tres instantaneas del rato malo, y si lr da vueltas entre las mismas
      // dos o tres direcciones, ahi esta el bucle.
      //
      // Va a nivel debug -no molesta en uso normal- y son unas pocas lineas
      // cada diez segundos.
      if (++desde_instantanea >= 10) {
        desde_instantanea = 0;
        REXLOG_DEBUG("[vigilante] instantanea: {} hilos del juego", hilos.size());
        VolcarHilos(hilos, false);
      }

      if (firma != firma_anterior) {
        if (avisado) {
          REXLOG_WARN("[vigilante] el juego ha vuelto a moverse despues de {} s parado.", quietos);
          avisado = false;
        }
        firma_anterior = firma;
        quietos = 0;
        desde_ultimo_volcado = 0;
        continue;
      }

      ++quietos;
      ++desde_ultimo_volcado;
      if (quietos < kSegundosParaSospechar) continue;
      if (avisado && desde_ultimo_volcado < kSegundosEntreVolcados) continue;
      desde_ultimo_volcado = 0;

      REXLOG_ERROR("[vigilante] {} s sin que se mueva ni un registro en ninguno de los {} hilos "
                   "del juego. Esto no es lentitud: esta parado.",
                   quietos, hilos.size());
      VolcarHilos(hilos, true);
      avisado = true;
    }
  }

  // ==========================================================================
  //  5. PARCHE BLACK EDITION + EL MENU DE AJUSTES (ESC)
  // ==========================================================================

  void AplicarParcheBlackEdition() {
    constexpr uint32_t kBlackEditionAddr = 0x82A2CE04u;  // edicion PAL (454107D9)
    auto* kernel = rex::system::kernel_state();
    if (kernel == nullptr || kernel->memory() == nullptr) {
      REXLOG_WARN("[black-edition] sin kernel de memoria; no se puede parchear.");
      return;
    }
    if (!REXCVAR_GET(black_edition)) {
      REXLOG_INFO("[black-edition] desactivado (black_edition=false).");
      return;
    }
    auto* bandera = kernel->memory()->TranslateVirtual<uint32_t*>(kBlackEditionAddr);
    if (bandera == nullptr) {
      REXLOG_WARN("[black-edition] no se pudo traducir 0x{:08X}; el contenido "
                  "Black Edition seguira oculto.", kBlackEditionAddr);
      return;
    }
    // La memoria del guest se expone en big-endian: el valor se escribe tal cual.
    *bandera = 0x00000100u;
    REXLOG_INFO("[black-edition] bandera 0x{:08X} = 0x{:08X} (contenido desbloqueado).",
                kBlackEditionAddr, *bandera);
  }

  void AlternarMenu() {
    if (menu_ == nullptr) {
      auto* drawer = imgui_drawer();
      if (drawer == nullptr) {
        return;  // pulsacion prematura: todavia no hay UI
      }
      menu_ = new NfsmwMenuDialog(drawer, NfsmwMenuDialog::Callbacks{
          [this] { GuardarConfigDetras(); },
          [this] { RelanzarJuego(); },
          [this] {
            if (window() != nullptr) {
              window()->RequestClose();
            }
          },
          [this] { menu_ = nullptr; },
          [this] { return MuestreaFotograma(); },
      });
    } else {
      menu_->RequestClose();  // el dialogo se cierra y se borra solo
    }
  }

  void GuardarConfigDetras() {
    auto carpeta = rex::filesystem::GetExecutableFolder();
    if (carpeta.empty()) {
      carpeta = std::filesystem::current_path();
    }
    rex::cvar::SaveConfig(carpeta / "nfsmw.toml");
  }

  void RelanzarJuego() {
    GuardarConfigDetras();
#if defined(_WIN32)
    const auto exe = rex::filesystem::GetExecutablePath();
    if (!exe.empty()) {
      const std::wstring ruta = exe.wstring();
      const std::wstring carpeta = exe.parent_path().wstring();
      const INT_PTR resultado = reinterpret_cast<INT_PTR>(ShellExecuteW(
          nullptr, L"open", ruta.c_str(), nullptr, carpeta.c_str(), SW_SHOWNORMAL));
      if (resultado > 32) {
        // El proceso nuevo arranca con el toml recien guardado; este se cierra.
        if (window() != nullptr) {
          window()->RequestClose();
        }
        return;
      }
      REXLOG_ERROR("[menu] no se pudo relanzar el juego (ShellExecuteW = {}); sigue con "
                   "lo aplicado y reinicia a mano.", int32_t(resultado));
    } else {
      REXLOG_ERROR("[menu] sin ruta del ejecutable; reinicia el juego a mano.");
    }
#else
    REXLOG_WARN("[menu] reinicia el juego a mano para aplicar los cambios.");
#endif
  }

  rex::ui::FrameStats stats_{};
  std::chrono::steady_clock::time_point ultimo_{};
  double suave_ms_ = 0.0;
  uint64_t fotogramas_ = 0;
  bool tiene_anterior_ = false;

  std::thread vigilante_;
  std::atomic<bool> vigilante_activo_{false};

  NfsmwMenuDialog* menu_ = nullptr;  // los dialogos ImGui se borran solos al cerrarse
};
