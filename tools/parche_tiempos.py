#!/usr/bin/env python3
"""
Reparte el tiempo del procesador de comandos de la GPU: en que se le va.

    python tools/parche_tiempos.py            aplicar
    python tools/parche_tiempos.py --estado
    python tools/parche_tiempos.py --revertir

Toca dos ficheros del SDK:
    src/graphics/command_processor.cpp          (el CP generico)
    src/graphics/vulkan/command_processor.cpp   (el CP de Vulkan)

Va DESPUES de tools/parche_fps.py (su informe sale justo detras de la linea "fps:").
No guarda .original: aplica y deshace por sustitucion de texto exacta.


PARA QUE
========

En el movil el menu principal (un garaje en 3D) va a 15,0 fps clavados, y da
igual lo que se toque: resolucion de pantalla, filtro anisotropo, consultas de
oclusion, lectura de exposicion, vsync. Si la GPU fuera el cuello, bajar la
resolucion o quitar trabajo moveria algo. No mueve nada.

simpleperf dice que el hilo de render del juego se pasa el 99 % girando en
sub_82597690: espera a que el puntero de lectura del anillo de comandos pase
de cierto punto. O sea, espera al procesador de comandos (CP). Y el CP solo
usa el 11 % de la CPU: esta dormido casi todo el rato. Pero simpleperf solo
ve el tiempo EN CPU; donde duerme no lo dice.

Este parche lo dice. Cada cinco segundos, detras de la linea "fps:", sale:

    tiempos por fotograma: 19.2 ms = registro 7.0 + ocioso 0.0 + dibujos 5.7 (830)
      + swap 2.9 + resto 3.7 | de ello: GPU 0.0 (0.0 esperas), vkQueueSubmit 0.1 (3.0)
    bucle del CP por fotograma: ExecutePrimaryBuffer 19.1 ms (2.0 veces), ...

    registro  en WAIT_REG_MEM: el flujo de comandos del juego le pide esperar
              hasta que un registro o una posicion de memoria valga algo.
    ocioso    sin comandos que ejecutar: el anillo esta vacio.
    dibujos   IssueDraw, entero (entre parentesis, cuantos).
    swap      IssueSwap desde que se entrega la imagen al presentador.
    resto     todo lo demas: otros paquetes, EndSubmission...
    GPU       de lo anterior, dormido en vkWaitForFences esperando a la GPU.

Con --medir_paquetes=true sale ademas el tiempo exclusivo por tipo de paquete
PM4 (los ocho que mas), que es lo que usa el banco de pruebas para saber en que
pantalla esta el juego. Eso cuesta cuatro lecturas del reloj por paquete, 1-2 ms
por fotograma en el menu 3D; lo demas, unas pocas por fotograma.
"""

import argparse
import os
import pathlib
import sys


CP = "src/graphics/command_processor.cpp"
VK = "src/graphics/vulkan/command_processor.cpp"

BLOQUES = [
    # 1. CP generico: contadores (definidos en el de Vulkan, mismo plugin).
    (CP,
     '''#include <rex/system/user_module.h>
''',
     '''#include <rex/system/user_module.h>

// PARCHE LOCAL - tiempos: lo que el CP pasa esperando, en nanosegundos. Los
// define src/graphics/vulkan/command_processor.cpp, que es quien los escribe
// junto a la linea de fps.
#include <atomic>
#include <chrono>
extern "C" std::atomic<uint64_t> nfsmw_cp_ocioso_ns;
extern "C" std::atomic<uint64_t> nfsmw_cp_registro_ns;
extern "C" std::atomic<uint32_t> nfsmw_cp_registro_esperas;
extern "C" std::atomic<uint64_t> nfsmw_cp_primario_ns;
extern "C" std::atomic<uint64_t> nfsmw_cp_rptr_ns;
extern "C" std::atomic<uint32_t> nfsmw_cp_primarios;
// Tiempo exclusivo por tipo de paquete: 0-127 los PM4 de tipo 3 por opcode,
// 128 los de tipo 0 (escrituras de registros), 129 los de tipo 1 y 2. Solo
// los toca el hilo del CP (tambien quien los imprime). Cuesta cuatro lecturas
// del reloj por paquete (~14000 paquetes por fotograma en el menu 3D, 1-2 ms),
// asi que va aparte y apagado por defecto.
REXCVAR_DEFINE_BOOL(medir_paquetes, false, "GPU",
                    "Medir el tiempo del procesador de comandos por tipo de paquete PM4 (log)");
extern "C" {
uint64_t nfsmw_cp_paquete_ns[130] = {};
uint32_t nfsmw_cp_paquete_n[130] = {};
}
'''),

    # 1b. CP generico: tiempo por paquete, sin contar lo anidado.
    (CP,
     '''  switch (packet_type) {
    case 0x00:
      return ExecutePacketType0(reader, packet);
    case 0x01:
      return ExecutePacketType1(reader, packet);
    case 0x02:
      return ExecutePacketType2(reader, packet);
    case 0x03:
      return ExecutePacketType3(reader, packet);
    default:
      assert_unhandled_case(packet_type);
      return false;
  }
}
''',
     '''  // PARCHE LOCAL - tiempos: tiempo EXCLUSIVO por tipo de paquete. Un
  // INDIRECT_BUFFER ejecuta paquetes dentro; mientras tanto su reloj se para,
  // para no contar dos veces.
  using NfsmwReloj = std::chrono::steady_clock;
  static int nfsmw_pila_clave[32];
  static NfsmwReloj::time_point nfsmw_pila_desde[32];
  static int nfsmw_prof = 0;
  auto nfsmw_ns = [](NfsmwReloj::duration d) {
    return uint64_t(std::chrono::duration_cast<std::chrono::nanoseconds>(d).count());
  };
  const int nfsmw_clave =
      packet_type == 3 ? int((packet >> 8) & 0x7F) : 128 + int(packet_type != 0);
  const bool nfsmw_medir = nfsmw_prof < 32 && REXCVAR_GET(medir_paquetes);
  if (nfsmw_medir) {
    const auto ahora = NfsmwReloj::now();
    if (nfsmw_prof > 0) {
      nfsmw_cp_paquete_ns[nfsmw_pila_clave[nfsmw_prof - 1]] +=
          nfsmw_ns(ahora - nfsmw_pila_desde[nfsmw_prof - 1]);
    }
    nfsmw_pila_clave[nfsmw_prof] = nfsmw_clave;
    nfsmw_pila_desde[nfsmw_prof] = ahora;
    ++nfsmw_prof;
  }
  bool nfsmw_resultado;
  switch (packet_type) {
    case 0x00:
      nfsmw_resultado = ExecutePacketType0(reader, packet);
      break;
    case 0x01:
      nfsmw_resultado = ExecutePacketType1(reader, packet);
      break;
    case 0x02:
      nfsmw_resultado = ExecutePacketType2(reader, packet);
      break;
    case 0x03:
      nfsmw_resultado = ExecutePacketType3(reader, packet);
      break;
    default:
      assert_unhandled_case(packet_type);
      nfsmw_resultado = false;
      break;
  }
  if (nfsmw_medir) {
    const auto fin = NfsmwReloj::now();
    --nfsmw_prof;
    nfsmw_cp_paquete_ns[nfsmw_clave] += nfsmw_ns(fin - nfsmw_pila_desde[nfsmw_prof]);
    ++nfsmw_cp_paquete_n[nfsmw_clave];
    if (nfsmw_prof > 0) {
      nfsmw_pila_desde[nfsmw_prof - 1] = fin;
    }
  }
  return nfsmw_resultado;
}
'''),

    # 2. CP generico: sin comandos que ejecutar.
    (CP,
     '''      PrepareForWait();
      uint32_t loop_count = 0;
''',
     '''      PrepareForWait();
      const auto nfsmw_ocioso_desde = std::chrono::steady_clock::now();  // PARCHE LOCAL - tiempos
      uint32_t loop_count = 0;
'''),
    (CP,
     '''               (write_ptr_index == 0xBAADF00D || read_ptr_index_ == write_ptr_index));
      ReturnFromWait();
''',
     '''               (write_ptr_index == 0xBAADF00D || read_ptr_index_ == write_ptr_index));
      nfsmw_cp_ocioso_ns.fetch_add(  // PARCHE LOCAL - tiempos
          uint64_t(std::chrono::duration_cast<std::chrono::nanoseconds>(
                       std::chrono::steady_clock::now() - nfsmw_ocioso_desde)
                       .count()),
          std::memory_order_relaxed);
      ReturnFromWait();
'''),

    # 2b. CP generico: el bucle principal, trozo a trozo.
    (CP,
     '''    // Execute. Note that we handle wraparound transparently.
    read_ptr_index_ = ExecutePrimaryBuffer(read_ptr_index_, write_ptr_index);

    // TODO(benvanik): use reader->Read_update_freq_ and only issue after moving
    //     that many indices.
    if (read_ptr_writeback_ptr_) {
      memory::store_and_swap<uint32_t>(memory_->TranslatePhysical(read_ptr_writeback_ptr_),
                                       read_ptr_index_);
    }
''',
     '''    // Execute. Note that we handle wraparound transparently.
    const auto nfsmw_primario_desde = std::chrono::steady_clock::now();  // PARCHE LOCAL - tiempos
    read_ptr_index_ = ExecutePrimaryBuffer(read_ptr_index_, write_ptr_index);
    const auto nfsmw_primario_hasta = std::chrono::steady_clock::now();

    // TODO(benvanik): use reader->Read_update_freq_ and only issue after moving
    //     that many indices.
    if (read_ptr_writeback_ptr_) {
      memory::store_and_swap<uint32_t>(memory_->TranslatePhysical(read_ptr_writeback_ptr_),
                                       read_ptr_index_);
    }
    nfsmw_cp_primario_ns.fetch_add(
        uint64_t(std::chrono::duration_cast<std::chrono::nanoseconds>(nfsmw_primario_hasta -
                                                                      nfsmw_primario_desde)
                     .count()),
        std::memory_order_relaxed);
    nfsmw_cp_rptr_ns.fetch_add(
        uint64_t(std::chrono::duration_cast<std::chrono::nanoseconds>(
                     std::chrono::steady_clock::now() - nfsmw_primario_hasta)
                     .count()),
        std::memory_order_relaxed);
    nfsmw_cp_primarios.fetch_add(1, std::memory_order_relaxed);
'''),

    # 3. CP generico: WAIT_REG_MEM sin cumplir.
    (CP,
     '''  bool matched = false;
  do {
    uint32_t value = 0;
    if (is_memory) {
''',
     '''  bool matched = false;
  // PARCHE LOCAL - tiempos: cuanto se espera aqui, contando desde la primera
  // comprobacion que falla.
  std::chrono::steady_clock::time_point nfsmw_registro_desde{};
  do {
    uint32_t value = 0;
    if (is_memory) {
'''),
    (CP,
     '''    if (!matched) {
      // Wait.
      if (wait >= 0x100) {
''',
     '''    if (!matched && nfsmw_registro_desde == std::chrono::steady_clock::time_point{}) {
      nfsmw_registro_desde = std::chrono::steady_clock::now();  // PARCHE LOCAL - tiempos
      nfsmw_cp_registro_esperas.fetch_add(1, std::memory_order_relaxed);
    }
    if (!matched) {
      // Wait.
      if (wait >= 0x100) {
'''),
    (CP,
     '''  } while (!matched);

  return true;
}
''',
     '''  } while (!matched);

  if (nfsmw_registro_desde != std::chrono::steady_clock::time_point{}) {
    nfsmw_cp_registro_ns.fetch_add(  // PARCHE LOCAL - tiempos
        uint64_t(std::chrono::duration_cast<std::chrono::nanoseconds>(
                     std::chrono::steady_clock::now() - nfsmw_registro_desde)
                     .count()),
        std::memory_order_relaxed);
  }
  return true;
}
'''),

    # 4. CP de Vulkan: definiciones, junto al contador de fps.
    (VK,
     '''extern "C" __attribute__((visibility("default"))) std::atomic<float> nfsmw_fps_invitado{0.0f};
''',
     '''extern "C" __attribute__((visibility("default"))) std::atomic<float> nfsmw_fps_invitado{0.0f};
// PARCHE LOCAL - tiempos: ver tools/parche_tiempos.py.
extern "C" std::atomic<uint64_t> nfsmw_cp_ocioso_ns{0};
extern "C" std::atomic<uint64_t> nfsmw_cp_registro_ns{0};
extern "C" std::atomic<uint32_t> nfsmw_cp_registro_esperas{0};
extern "C" std::atomic<uint64_t> nfsmw_cp_primario_ns{0};
extern "C" std::atomic<uint64_t> nfsmw_cp_rptr_ns{0};
extern "C" std::atomic<uint32_t> nfsmw_cp_primarios{0};
static std::atomic<uint64_t> nfsmw_cp_gpu_ns{0};
static std::atomic<uint32_t> nfsmw_cp_gpu_esperas{0};
static std::atomic<uint64_t> nfsmw_cp_envio_ns{0};
static std::atomic<uint32_t> nfsmw_cp_envios{0};
static std::atomic<uint64_t> nfsmw_cp_dibujo_ns{0};
static std::atomic<uint32_t> nfsmw_cp_dibujos{0};
static std::atomic<uint64_t> nfsmw_cp_swap_ns{0};
extern "C" uint64_t nfsmw_cp_paquete_ns[130];  // src/graphics/command_processor.cpp
extern "C" uint32_t nfsmw_cp_paquete_n[130];
REXCVAR_DECLARE(bool, medir_paquetes);  // idem
// Suma a 'destino' el tiempo que vive.
struct NfsmwCrono {
  std::atomic<uint64_t>& destino;
  std::chrono::steady_clock::time_point desde = std::chrono::steady_clock::now();
  explicit NfsmwCrono(std::atomic<uint64_t>& d) : destino(d) {}
  ~NfsmwCrono() {
    destino.fetch_add(uint64_t(std::chrono::duration_cast<std::chrono::nanoseconds>(
                                   std::chrono::steady_clock::now() - desde)
                                   .count()),
                      std::memory_order_relaxed);
  }
};
'''),

    # 5. CP de Vulkan: esperar a la GPU.
    (VK,
     '''    VkResult wait_result =
        dfn.vkWaitForFences(device, uint32_t(await_submission - submission_completed_),
                            submissions_in_flight_fences_.data(), VK_TRUE, UINT64_MAX);
''',
     '''    const auto nfsmw_gpu_desde = std::chrono::steady_clock::now();  // PARCHE LOCAL - tiempos
    VkResult wait_result =
        dfn.vkWaitForFences(device, uint32_t(await_submission - submission_completed_),
                            submissions_in_flight_fences_.data(), VK_TRUE, UINT64_MAX);
    nfsmw_cp_gpu_ns.fetch_add(
        uint64_t(std::chrono::duration_cast<std::chrono::nanoseconds>(
                     std::chrono::steady_clock::now() - nfsmw_gpu_desde)
                     .count()),
        std::memory_order_relaxed);
    nfsmw_cp_gpu_esperas.fetch_add(1, std::memory_order_relaxed);
'''),

    # 6. CP de Vulkan: envios.
    (VK,
     '''      submit_result = dfn.vkQueueSubmit(queue_acquisition.queue(), 1, &submit_info, fence);
''',
     '''      {
        NfsmwCrono nfsmw_crono_envio(nfsmw_cp_envio_ns);  // PARCHE LOCAL - tiempos
        submit_result = dfn.vkQueueSubmit(queue_acquisition.queue(), 1, &submit_info, fence);
      }
      nfsmw_cp_envios.fetch_add(1, std::memory_order_relaxed);
'''),

    # 6b. CP de Vulkan: cada dibujado, entero.
    (VK,
     '''bool VulkanCommandProcessor::IssueDraw(xenos::PrimitiveType prim_type, uint32_t index_count,
                                       IndexBufferInfo* index_buffer_info,
                                       bool major_mode_explicit) {
''',
     '''bool VulkanCommandProcessor::IssueDraw(xenos::PrimitiveType prim_type, uint32_t index_count,
                                       IndexBufferInfo* index_buffer_info,
                                       bool major_mode_explicit) {
  NfsmwCrono nfsmw_crono_dibujo(nfsmw_cp_dibujo_ns);  // PARCHE LOCAL - tiempos
  nfsmw_cp_dibujos.fetch_add(1, std::memory_order_relaxed);
'''),

    # 6c. CP de Vulkan: el swap, desde que se entrega la imagen al presentador.
    (VK,
     '''  presenter->RefreshGuestOutput(
      guest_output_width, guest_output_height, display_width, display_height,
''',
     '''  NfsmwCrono nfsmw_crono_swap(nfsmw_cp_swap_ns);  // PARCHE LOCAL - tiempos
  presenter->RefreshGuestOutput(
      guest_output_width, guest_output_height, display_width, display_height,
'''),

    # 7. CP de Vulkan: el reparto, cada 5 s, detras del contador de parche_fps.py
    #    (fuera de su bloque, para no pisarlo).
    (VK,
     '''  system::X_VIDEO_MODE video_mode;
''',
     '''  // PARCHE LOCAL - tiempos: el reparto del tiempo del CP por fotograma, cada
  // 5 s. Lleva su propia cuenta de fotogramas.
  {
    using RelojTiempos = std::chrono::steady_clock;
    static RelojTiempos::time_point desde{};
    static uint32_t fotogramas = 0;
    const auto ahora = RelojTiempos::now();
    if (desde == RelojTiempos::time_point{}) {
      desde = ahora;
    } else if (++fotogramas,
               std::chrono::duration<double>(ahora - desde).count() >= 5.0) {
      const double segundos = std::chrono::duration<double>(ahora - desde).count();
      const double f = 1.0 / fotogramas;
      auto ms = [f](std::atomic<uint64_t>& ns) {
        return double(ns.exchange(0, std::memory_order_relaxed)) / 1e6 * f;
      };
      auto por = [f](std::atomic<uint32_t>& n) {
        return double(n.exchange(0, std::memory_order_relaxed)) * f;
      };
      // registro, ocioso, dibujos y swap no se solapan (son paquetes o tramos
      // distintos del bucle). GPU y vkQueueSubmit caen DENTRO de ellos: se dan
      // aparte, como "de ello".
      const double total = segundos * 1000.0 * f;
      const double registro = ms(nfsmw_cp_registro_ns);
      const double ocioso = ms(nfsmw_cp_ocioso_ns);
      const double dibujos = ms(nfsmw_cp_dibujo_ns);
      const double swap = ms(nfsmw_cp_swap_ns);
      const double gpu = ms(nfsmw_cp_gpu_ns);
      const double envio = ms(nfsmw_cp_envio_ns);
      const double n_dibujos = por(nfsmw_cp_dibujos);
      const double esperas_gpu = por(nfsmw_cp_gpu_esperas);
      const double esperas_registro = por(nfsmw_cp_registro_esperas);
      const double envios = por(nfsmw_cp_envios);
      REXGPU_INFO(
          "tiempos por fotograma: {:.1f} ms = registro {:.1f} + ocioso {:.1f} + dibujos "
          "{:.1f} ({:.0f}) + swap {:.1f} + resto {:.1f} | de ello: GPU {:.1f} ({:.1f} "
          "esperas), vkQueueSubmit {:.1f} ({:.1f}), {:.1f} esperas registro",
          total, registro, ocioso, dibujos, n_dibujos, swap,
          total - registro - ocioso - dibujos - swap, gpu, esperas_gpu, envio, envios,
          esperas_registro);
      if (REXCVAR_GET(medir_paquetes)) {
        // Los paquetes que mas tiempo exclusivo se llevan.
        int orden[130];
        for (int i = 0; i < 130; ++i) {
          orden[i] = i;
        }
        std::sort(std::begin(orden), std::end(orden), [](int a, int b) {
          return nfsmw_cp_paquete_ns[a] > nfsmw_cp_paquete_ns[b];
        });
        std::string paquetes;
        for (int k = 0; k < 8 && nfsmw_cp_paquete_ns[orden[k]]; ++k) {
          const int i = orden[k];
          paquetes += fmt::format(
              "  {}{:02X} {:.2f} ms ({:.0f})", i < 128 ? "op" : "tipo",
              i < 128 ? i : (i == 128 ? 0 : 1), double(nfsmw_cp_paquete_ns[i]) / 1e6 * f,
              double(nfsmw_cp_paquete_n[i]) * f);
        }
        REXGPU_INFO("paquetes por fotograma:{}", paquetes);
        std::fill(std::begin(nfsmw_cp_paquete_ns), std::end(nfsmw_cp_paquete_ns), 0);
        std::fill(std::begin(nfsmw_cp_paquete_n), std::end(nfsmw_cp_paquete_n), 0);
      }
      const double primarios = por(nfsmw_cp_primarios);
      const double primario = ms(nfsmw_cp_primario_ns);
      const double rptr = ms(nfsmw_cp_rptr_ns);
      REXGPU_INFO(
          "bucle del CP por fotograma: ExecutePrimaryBuffer {:.1f} ms ({:.1f} veces), "
          "escribir RPTR {:.2f} ms, fuera de ambos {:.1f} ms",
          primario, primarios, rptr, total - primario - rptr);
      fotogramas = 0;
      desde = ahora;
    }
  }
  system::X_VIDEO_MODE video_mode;
'''),
]


def localizar_sdk():
    raiz = pathlib.Path(__file__).resolve().parent.parent
    # NFSMW_SDK apunta a otro arbol del SDK (el de Android, por ejemplo). Si
    # esta puesta se usa SOLO esa ruta: caer en silencio en el SDK de Windows
    # parchearia el arbol equivocado.
    otro = os.environ.get("NFSMW_SDK")
    candidatos = [pathlib.Path(otro)] if otro else [raiz.parent / "rexglue-sdk", raiz / "sdk"]
    for cand in candidatos:
        if (cand / CP).exists() and (cand / VK).exists():
            return cand
    sys.exit(f"[ERROR] No encuentro {CP} y {VK} del SDK.\n"
             "        Se busca en NFSMW_SDK, o en ..\\rexglue-sdk y .\\sdk")


def leer(f):
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
    textos = {}
    for fichero in (CP, VK):
        textos[fichero] = leer(sdk / fichero)

    puestos = sum(1 for f, _, nuevo in BLOQUES if nuevo in textos[f][0])

    if args.estado:
        estado = ("aplicado" if puestos == len(BLOQUES)
                  else "sin aplicar" if puestos == 0
                  else f"a medias ({puestos}/{len(BLOQUES)})")
        print(f"  tiempos                    {estado}")
        return 0

    if args.revertir:
        for f, ancla, nuevo in BLOQUES:
            txt, eol = textos[f]
            if nuevo in txt:
                textos[f] = (txt.replace(nuevo, ancla), eol)
        for f, (txt, eol) in textos.items():
            escribir(sdk / f, txt, eol)
        print(f"[ok] Quitados {puestos} bloques")
        return 0

    # Comprobar todo antes de tocar nada.
    for f, ancla, nuevo in BLOQUES:
        txt = textos[f][0]
        if nuevo in txt:
            continue
        n = txt.count(ancla)
        if n != 1:
            sys.exit(f"[ERROR] Un anclaje aparece {n} veces en {f}, esperaba 1.\n"
                     "        El SDK habra cambiado, o falta tools/parche_fps.py.\n"
                     "        No he tocado nada.")
    for f, ancla, nuevo in BLOQUES:
        txt, eol = textos[f]
        if nuevo not in txt:
            textos[f] = (txt.replace(ancla, nuevo), eol)
    for f, (txt, eol) in textos.items():
        escribir(sdk / f, txt, eol)
    print(f"[ok] Aplicado ({len(BLOQUES) - puestos} bloques nuevos): reparto del tiempo del CP "
          "junto a la linea de fps")
    return 0


if __name__ == "__main__":
    sys.exit(main())
