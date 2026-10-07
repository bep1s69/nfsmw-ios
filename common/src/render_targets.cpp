// NFSMW Recompiled - la escena en una pasada, sin tiling ni MSAA, desde el juego
//
// Portado de StevensND/nfsmw-nx (app/src/nfsmw_render_targets.cpp, GPL-3.0),
// que parte de este mismo proyecto. Solo la parte que vale con la emulacion de
// Xenos: su modo de 1080p no cabe en los 10 MB de EDRAM emulada (1920x1088 son
// ~16,7 MB de color y profundidad), y lo de Switch (dock, Reverse-NX) sobra.
//
// ===========================================================================
//  Lo que hace el juego
//
//  Para tener MSAA 4x a 720p con los 10 MB de EDRAM de la Xbox 360, NFSMW no
//  pinta la escena en una superficie de 1280x720: usa el "tiling" del D3D del
//  XDK. BeginTiling graba la escena y EndTiling la reenvia una vez por tira,
//  en superficies de 1280x256 con 4 muestras, resolviendo cada tira a la
//  textura de 1280x720. Tres tiras = la escena se pinta tres veces por
//  fotograma (el censo lo midio: 2.748 dibujos = 3 x 916 en carrera).
//
//  Como elige el juego (codigo recompilado; direcciones de la edicion PAL
//  Espana, la misma que usa nfsmw-nx como referencia)
//    sub_82458310  constructor del renderizador: tabla de 6 modos de AA en
//                  objeto+4 (tiras), +28 (ancho), +52 (alto), +76 (MSAA) y
//                  +100+64*modo (rectangulos de las tiras).
//                    modo 2: 1 tira   1280x736  1x   <- sin antialiasing
//                    modo 3: 2 tiras   640x736  2x
//                    modo 4: 3 tiras  1280x256  4x   <- el que usa a 720p
//                    modo 5: 4 tiras   320x736  4x
//    sub_824402F0  XGetVideoMode: en HD con ancho >= 1280 pone el modo 4.
//    sub_82441990  cambia en marcha entre los modos 2, 3 y 4. El juego de
//                  tienda ya pinta en el modo 2 cuando baja la calidad: no es
//                  un estado inventado.
//    sub_82458850  registra un conjunto de render targets por modo.
//    sub_8245D320  copia el descriptor (128 bytes) a la tabla 0x82A4527C.
//    sub_8245D5F8  enlaza un conjunto; si el byte +41 es 1 -> BeginTiling.
//
//  Lo que se cambia (cvar nfsmw_render_sin_mosaico)
//  1. Antes de registrar los conjuntos, los modos 3, 4 y 5 toman la
//     configuracion del 2 (1 tira de 1280x736 sin MSAA), y el juego usa de
//     verdad su modo 2. La escena se pinta una vez, con sus propios resolves:
//     sin desplazamiento de ventana ni predicacion que tocar, al contrario que
//     tools/parche_una_pasada.py, que lo hace a la fuerza en el procesador de
//     comandos.
//  2. Cualquier conjunto que se registre con MSAA pasa a una muestra (el
//     reflejo de 256x256 con 4x, sub_8243C1C8, y los modos SD).
//  3. Las consultas de oclusion del destello del sol (sub_82225610) cuentan
//     muestras y esperan las del modo que pidio el juego (2048 en el 4, 1024
//     en el 2): mientras corren se le pone ese modo, y el destello se apaga
//     como en la Xbox 360.
//
//  Se pierde el antialiasing del juego: por eso la app solo lo enciende si el
//  suavizado no es MSAA (Ajustes.unaPasada).
// ===========================================================================

#include <array>
#include <atomic>
#include <cstdint>
#include <cstring>

#include "nfsmw_pch.h"

#include <rex/cvar.h>
#include <rex/hook.h>
#include <rex/logging.h>

REXCVAR_DEFINE_BOOL(nfsmw_render_sin_mosaico, false, "Juego",
                    "Pintar la escena una sola vez, sin las 3 tiras ni MSAA: el juego usa su modo "
                    "sin antialiasing (portado de nfsmw-nx)")
    .lifecycle(rex::cvar::Lifecycle::kRequiresRestart);

extern "C" void nfsmw_scene_size_fixup(uint8_t* base) __attribute__((weak));

namespace nfsmw::render_targets {
namespace {

// La tabla de modos dentro del objeto renderizador (ver arriba).
constexpr uint32_t kModos = 6;
constexpr uint32_t kOffTiras = 4;
constexpr uint32_t kOffAncho = 28;
constexpr uint32_t kOffAlto = 52;
constexpr uint32_t kOffMsaa = 76;
constexpr uint32_t kOffRects = 100;
constexpr uint32_t kBytesPorModoRects = 64;  // 4 D3DRECT de 16 bytes
constexpr uint32_t kModoSinAa = 2;

// Puntero global al renderizador (lis r11,-32093 / lwz -11860).
constexpr uint32_t kRenderizadorGlobal = 0x82A2D1AC;

// Descriptor de conjunto que recibe sub_8245D320 en r5.
constexpr uint32_t kDescAncho = 8;
constexpr uint32_t kDescAlto = 12;
constexpr uint32_t kDescMsaa = 36;
constexpr uint32_t kDescTiling = 41;  // byte
constexpr uint32_t kDescTiras = 124;

uint32_t Leer32(const uint8_t* base, uint32_t direccion) {
  uint32_t v = 0;
  std::memcpy(&v, base + direccion, sizeof(v));
  return __builtin_bswap32(v);
}

void Escribir32(uint8_t* base, uint32_t direccion, uint32_t valor) {
  const uint32_t v = __builtin_bswap32(valor);
  std::memcpy(base + direccion, &v, sizeof(v));
}

struct Modo {
  uint32_t tiras, ancho, alto, msaa;
};

// El MSAA original de cada modo; vale cuando g_tabla_igualada es true.
std::array<std::atomic<uint32_t>, kModos> g_msaa_original{};
std::atomic<bool> g_tabla_igualada{false};
// El modo que habia elegido el juego antes de forzarlo al 2 (0 = nunca).
std::atomic<uint32_t> g_modo_pedido{0};
std::atomic<uint32_t> g_avisos_modo{0};
std::atomic<uint32_t> g_conjuntos_sin_msaa{0};

Modo LeerModo(const uint8_t* base, uint32_t obj, uint32_t m) {
  return {Leer32(base, obj + kOffTiras + 4 * m), Leer32(base, obj + kOffAncho + 4 * m),
          Leer32(base, obj + kOffAlto + 4 * m), Leer32(base, obj + kOffMsaa + 4 * m)};
}

bool Activo() { return REXCVAR_GET(nfsmw_render_sin_mosaico); }

void IgualarModosAlModoSinAa(uint8_t* base, uint32_t obj) {
  if (obj == 0) {
    REXLOG_WARN("[render] renderizador nulo al registrar los modos: no se toca nada");
    return;
  }
  for (uint32_t m = 0; m < kModos; ++m) {
    const Modo x = LeerModo(base, obj, m);
    REXLOG_INFO("[render] modo {} del juego: {} tira(s), {}x{}, MSAA {}", m, x.tiras, x.ancho, x.alto,
                x.msaa);
  }

  // Solo si la tabla es la analizada. Con otro ejecutable, mejor no escribir a ciegas.
  const Modo base_2 = LeerModo(base, obj, kModoSinAa);
  const uint32_t rect2 = obj + kOffRects + kBytesPorModoRects * kModoSinAa;
  const uint32_t r2_x1 = Leer32(base, rect2), r2_y1 = Leer32(base, rect2 + 4);
  const uint32_t r2_x2 = Leer32(base, rect2 + 8), r2_y2 = Leer32(base, rect2 + 12);
  const bool tabla_esperada = base_2.tiras == 1 && base_2.msaa == 0 && base_2.ancho == 1280 &&
                              base_2.alto >= 720 && r2_x1 == 0 && r2_y1 == 0 &&
                              r2_x2 == base_2.ancho && r2_y2 >= 720 && r2_y2 <= base_2.alto;
  if (!tabla_esperada) {
    REXLOG_WARN("[render] la tabla de modos no coincide con la analizada "
                "(modo 2: {} tira(s) {}x{} MSAA {}, rect {},{},{},{}): se deja como esta",
                base_2.tiras, base_2.ancho, base_2.alto, base_2.msaa, r2_x1, r2_y1, r2_x2, r2_y2);
    return;
  }

  for (uint32_t m = 0; m < kModos; ++m) {
    g_msaa_original[m].store(LeerModo(base, obj, m).msaa, std::memory_order_relaxed);
  }
  g_tabla_igualada.store(true, std::memory_order_relaxed);

  // Los modos 3-5 con la configuracion del 2. Solo se lee la primera tira
  // (sub_82458850 copia tiras*16 bytes).
  for (uint32_t m = 3; m < kModos; ++m) {
    Escribir32(base, obj + kOffTiras + 4 * m, 1);
    Escribir32(base, obj + kOffAncho + 4 * m, base_2.ancho);
    Escribir32(base, obj + kOffAlto + 4 * m, base_2.alto);
    Escribir32(base, obj + kOffMsaa + 4 * m, 0);
    std::memcpy(base + obj + kOffRects + kBytesPorModoRects * m, base + rect2, 16);
  }
  REXLOG_INFO("[render] modos 3-5 igualados al modo 2: 1 tira {}x{} sin MSAA. La escena ya no "
              "se repite por tira.",
              base_2.ancho, base_2.alto);
}

// Tras cada eleccion de modo del juego: si eligio 3, 4 o 5, se queda en el 2.
void ForzarModoSinAa(uint8_t* base) {
  // iOS: el tamano de la escena en pantallas mas anchas que 16:9
  // (ios/src/game_scene_size.cpp). En Android no existe y no se llama.
  if (nfsmw_scene_size_fixup) {
    nfsmw_scene_size_fixup(base);
  }
  if (!Activo()) {
    return;
  }
  const uint32_t obj = Leer32(base, kRenderizadorGlobal);
  if (obj == 0) {
    return;
  }
  const uint32_t modo = Leer32(base, obj);
  // Solo los modos de varias tiras (3-5). Los 0 y 1 (SD 640x480 y HD estrecho
  // 1024x576) ya son de una tira, y sus texturas tienen su tamano: llevarlos
  // al 2 (1280 de ancho) desordenaba la imagen en 4:3 (iOS). A 720p no cambia
  // nada: el juego solo elige 2, 3 o 4.
  if (modo <= kModoSinAa) {
    return;
  }
  if (modo < kModos) {
    const uint32_t antes = g_modo_pedido.exchange(modo, std::memory_order_relaxed);
    if (antes != modo && g_avisos_modo.fetch_add(1, std::memory_order_relaxed) < 16) {
      REXLOG_INFO("[render] el juego eligio el modo {}: se usa el {}", modo, kModoSinAa);
    }
  }
  Escribir32(base, obj, kModoSinAa);
}

}  // namespace
}  // namespace nfsmw::render_targets

using namespace nfsmw::render_targets;

// Las dos funciones que eligen el modo de AA. Despues del original, 3, 4 o 5 pasa a 2.
REX_EXTERN(__imp__sub_824402F0);
REX_HOOK_RAW(sub_824402F0) {
  __imp__sub_824402F0(ctx, base);
  ForzarModoSinAa(base);
}

REX_EXTERN(__imp__sub_82441990);
REX_HOOK_RAW(sub_82441990) {
  __imp__sub_82441990(ctx, base);
  ForzarModoSinAa(base);
}

// Referencia de muestras de las consultas de oclusion del destello
// (sub_82225610): con el modo 2 forzado se calcula con el modo que habia pedido
// el juego, y el destello se apaga como en la Xbox 360 en ese modo.
REX_EXTERN(__imp__sub_82225610);
REX_HOOK_RAW(sub_82225610) {
  const uint32_t pedido = g_modo_pedido.load(std::memory_order_relaxed);
  const uint32_t obj = Leer32(base, kRenderizadorGlobal);
  if (pedido != 0 && obj != 0 && Activo() && Leer32(base, obj) == kModoSinAa) {
    Escribir32(base, obj, pedido);
    __imp__sub_82225610(ctx, base);
    Escribir32(base, obj, kModoSinAa);
    return;
  }
  __imp__sub_82225610(ctx, base);
}

// Registro de los 6 conjuntos principales de la escena, uno por modo de AA.
// r3 = renderizador. La tabla se arregla antes de que la lea el original.
REX_EXTERN(__imp__sub_82458850);
REX_HOOK_RAW(sub_82458850) {
  if (Activo()) {
    IgualarModosAlModoSinAa(base, ctx.r3.u32);
  }
  __imp__sub_82458850(ctx, base);
}

// Enlace de un conjunto de render targets: el juego lo hace cada fotograma, asi
// que aqui se vuelve a imponer el modo por si lo ha cambiado.
REX_EXTERN(__imp__sub_8245D5F8);
REX_HOOK_RAW(sub_8245D5F8) {
  ForzarModoSinAa(base);
  __imp__sub_8245D5F8(ctx, base);
}

// Registro de un conjunto de render targets. r5 = el descriptor temporal del
// que llama, que el original copia a la tabla global. Se le quita el MSAA; el
// que llama vuelve a escribir ese campo antes de cada registro.
REX_EXTERN(__imp__sub_8245D320);
REX_HOOK_RAW(sub_8245D320) {
  const uint32_t desc = ctx.r5.u32;
  if (Activo() && desc != 0) {
    const uint32_t msaa = Leer32(base, desc + kDescMsaa);
    if (msaa != 0) {
      Escribir32(base, desc + kDescMsaa, 0);
      const uint32_t n = g_conjuntos_sin_msaa.fetch_add(1, std::memory_order_relaxed) + 1;
      REXLOG_INFO("[render] conjunto {}x{} registrado sin MSAA (pedia {}), tiling {} con {} "
                  "tira(s); {} conjunto(s) corregidos",
                  Leer32(base, desc + kDescAncho), Leer32(base, desc + kDescAlto), msaa,
                  base[desc + kDescTiling], Leer32(base, desc + kDescTiras), n);
    }
  }
  __imp__sub_8245D320(ctx, base);
}
