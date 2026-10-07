#!/usr/bin/env python3
"""
Que el procesador de comandos no pregunte al driver por los envios acabados.

    python tools/parche_fences.py            aplicar
    python tools/parche_fences.py --estado
    python tools/parche_fences.py --revertir

Toca un fichero del SDK:  src/graphics/vulkan/command_processor.cpp
No guarda .original: aplica y deshace por sustitucion de texto exacta.


EL FALLO
========

Al abrir cada envio (tres por fotograma), el procesador de comandos mira que
envios anteriores ha terminado ya la GPU, para reciclar sus recursos. Lo hacia
con vkWaitForFences(..., timeout 0): "espera, pero sin esperar".

Con el driver de Qualcomm eso es instantaneo. Con Turnip V36 (Mesa, backend
KGSL) cada una de esas llamadas tardaba de media 7,7 ms: medido en el menu 3D,
231 llamadas y 1776 ms de cada 5 s. Casi todo en un bucle de `dc civac`
(limpiar e invalidar la cache de la CPU linea a linea) dentro del driver: el
31 % de todo el hilo. Era la mayor parte de los ~65 ms que costaba cada
fotograma con Turnip.


EL ARREGLO
==========

Tres cosas:

1. vkGetFenceStatus en vez de vkWaitForFences(timeout 0): es la llamada hecha
   para eso. En Turnip V36 cuesta lo mismo (el driver sincroniza la cache de un
   buffer entero al consultar), pero es la forma correcta.
2. Consultar solo al abrir fotograma, que es cuando hace falta (para no tener
   mas de kMaxFramesInFlight en vuelo). Los otros dos envios del fotograma solo
   consultaban para reciclar recursos un poco antes; ahora se reciclan en la
   consulta siguiente. Un tercio de las consultas.
3. El vigia (cvar vulkan_vigia_fences, por defecto true): un hilo aparte,
   "GPU fences", espera en orden a los fences de los envios con
   vkWaitForFences bloqueante y publica cuantos han acabado. El procesador de
   comandos solo lee ese numero; si tiene que esperar a un envio, espera al
   vigia. El coste del driver se paga en otro nucleo. Los fences solo se
   reciclan despues de que el vigia los de por acabados, asi que no se
   reinicia ninguno mientras se espera.
"""

import argparse
import os
import pathlib
import sys


FICHERO = "src/graphics/vulkan/command_processor.cpp"

BLOQUES = [
    (
        '''    VkResult fence_status =
        dfn.vkWaitForFences(device, 1, &submissions_in_flight_fences_[fences_awaited], VK_TRUE, 0);
''',
        '''    // PARCHE LOCAL - fences: vkGetFenceStatus en vez de vkWaitForFences con
    // tiempo 0 (tools/parche_fences.py).
    VkResult fence_status =
        dfn.vkGetFenceStatus(device, submissions_in_flight_fences_[fences_awaited]);
''',
    ),
    (
        '''  CheckSubmissionFenceAndDeviceLoss(await_submission);
  if (device_lost_ || submission_completed_ < await_submission) {
    return false;
  }
''',
        '''  // PARCHE LOCAL - fences: consultar solo al abrir fotograma o si hay algo
  // que esperar; en Turnip cada consulta cuesta ~8 ms (tools/parche_fences.py).
  if (is_opening_frame || await_submission) {
    CheckSubmissionFenceAndDeviceLoss(await_submission);
  }
  if (device_lost_ || submission_completed_ < await_submission) {
    return false;
  }
''',
    ),
    (
        '''#include <rex/ui/vulkan/util.h>
''',
        '''#include <rex/ui/vulkan/util.h>

// PARCHE LOCAL - fences: el vigia (ver tools/parche_fences.py).
#include <condition_variable>
#include <deque>
#include <mutex>
#include <thread>
#if defined(__linux__)
#include <pthread.h>
#endif
REXCVAR_DEFINE_BOOL(vulkan_vigia_fences, true, "GPU/Vulkan",
                    "Un hilo aparte espera a los fences de los envios, para que el procesador "
                    "de comandos no tenga que consultarlos")
    .lifecycle(rex::cvar::Lifecycle::kInitOnly);
namespace {
// Espera en orden a los fences de los envios y publica cuantos han acabado.
// El procesador de comandos solo reciclaba un fence despues de que este hilo
// lo diera por senalado, asi que nunca se reinicia uno que se este esperando.
class NfsmwVigiaFences {
 public:
  ~NfsmwVigiaFences() { Parar(); }
  bool activo() const { return hilo_.joinable(); }
  void Iniciar(VkDevice device, PFN_vkWaitForFences esperar) {
    if (hilo_.joinable()) {
      return;
    }
    device_ = device;
    esperar_ = esperar;
    {
      std::lock_guard<std::mutex> l(m_);
      parar_ = false;
      perdido_ = false;
      cola_.clear();
      completados_ = 0;
    }
    completados_publicados_.store(0, std::memory_order_release);
    perdido_publicado_.store(false, std::memory_order_release);
    hilo_ = std::thread([this] { Bucle(); });
  }
  void Parar() {
    if (!hilo_.joinable()) {
      return;
    }
    {
      std::lock_guard<std::mutex> l(m_);
      parar_ = true;
    }
    cv_nuevo_.notify_all();
    hilo_.join();
    cola_.clear();
  }
  void Encolar(VkFence fence) {
    {
      std::lock_guard<std::mutex> l(m_);
      cola_.push_back(fence);
    }
    cv_nuevo_.notify_one();
  }
  // Fences senalados desde Iniciar, en el orden en que se encolaron.
  uint64_t Completados() const { return completados_publicados_.load(std::memory_order_acquire); }
  bool Perdido() const { return perdido_publicado_.load(std::memory_order_acquire); }
  void EsperarHasta(uint64_t n) {
    std::unique_lock<std::mutex> l(m_);
    cv_hecho_.wait(l, [&] { return completados_ >= n || perdido_ || !hilo_.joinable(); });
  }

 private:
  void Bucle() {
#if defined(__linux__)
    pthread_setname_np(pthread_self(), "GPU fences");
#endif
    std::unique_lock<std::mutex> l(m_);
    for (;;) {
      cv_nuevo_.wait(l, [&] { return parar_ || !cola_.empty(); });
      if (cola_.empty()) {
        break;
      }
      VkFence fence = cola_.front();
      l.unlock();
      const VkResult resultado = esperar_(device_, 1, &fence, VK_TRUE, UINT64_MAX);
      l.lock();
      if (resultado != VK_SUCCESS) {
        perdido_ = true;
        perdido_publicado_.store(true, std::memory_order_release);
        cv_hecho_.notify_all();
        break;
      }
      cola_.pop_front();
      ++completados_;
      completados_publicados_.store(completados_, std::memory_order_release);
      cv_hecho_.notify_all();
    }
  }

  VkDevice device_ = VK_NULL_HANDLE;
  PFN_vkWaitForFences esperar_ = nullptr;
  std::mutex m_;
  std::condition_variable cv_nuevo_;
  std::condition_variable cv_hecho_;
  std::deque<VkFence> cola_;
  uint64_t completados_ = 0;
  bool parar_ = false;
  bool perdido_ = false;
  std::atomic<uint64_t> completados_publicados_{0};
  std::atomic<bool> perdido_publicado_{false};
  std::thread hilo_;
};
NfsmwVigiaFences nfsmw_vigia;
// submission_completed_ cuando arranco el vigia: sus cuentas van desde ahi.
uint64_t nfsmw_vigia_base = 0;
}  // namespace
''',
    ),
    (
        '''    submissions_in_flight_fences_.push_back(fence);
    fences_free_.pop_back();
''',
        '''    submissions_in_flight_fences_.push_back(fence);
    fences_free_.pop_back();
    // PARCHE LOCAL - fences: el vigia espera a este fence. Arranca en el primer
    // envio y se lleva todos los que haya en vuelo, en orden.
    if (REXCVAR_GET(vulkan_vigia_fences)) {
      if (!nfsmw_vigia.activo()) {
        nfsmw_vigia_base = submission_completed_;
        nfsmw_vigia.Iniciar(device, dfn.vkWaitForFences);
        for (VkFence en_vuelo : submissions_in_flight_fences_) {
          nfsmw_vigia.Encolar(en_vuelo);
        }
      } else {
        nfsmw_vigia.Encolar(fence);
      }
    }
''',
    ),
    (
        '''  size_t fences_total = submissions_in_flight_fences_.size();
  size_t fences_awaited = 0;
''',
        '''  size_t fences_total = submissions_in_flight_fences_.size();
  size_t fences_awaited = 0;
  // PARCHE LOCAL - fences: con el vigia no se pregunta al driver (en Turnip
  // cada consulta costaba ~8-12 ms); se lee lo que el vigia ha visto acabar.
  if (nfsmw_vigia.activo()) {
    if (await_submission > submission_completed_) {
      const auto nfsmw_gpu_desde = std::chrono::steady_clock::now();
      nfsmw_vigia.EsperarHasta(await_submission - nfsmw_vigia_base);
      nfsmw_cp_gpu_ns.fetch_add(
          uint64_t(std::chrono::duration_cast<std::chrono::nanoseconds>(
                       std::chrono::steady_clock::now() - nfsmw_gpu_desde)
                       .count()),
          std::memory_order_relaxed);
      nfsmw_cp_gpu_esperas.fetch_add(1, std::memory_order_relaxed);
    }
    if (nfsmw_vigia.Perdido()) {
      device_lost_ = true;
    }
    const uint64_t nfsmw_hechos = nfsmw_vigia.Completados() + nfsmw_vigia_base;
    if (nfsmw_hechos > submission_completed_) {
      fences_awaited =
          size_t(std::min<uint64_t>(nfsmw_hechos - submission_completed_, fences_total));
    }
    goto nfsmw_tras_consultar_fences;
  }
''',
    ),
    (
        '''    ++fences_awaited;
  }
  if (device_lost_) {
''',
        '''    ++fences_awaited;
  }
nfsmw_tras_consultar_fences:  // PARCHE LOCAL - fences
  if (device_lost_) {
''',
    ),
    (
        '''  for (VkFence& fence : submissions_in_flight_fences_) {
    dfn.vkDestroyFence(device, fence, nullptr);
  }
''',
        '''  nfsmw_vigia.Parar();  // PARCHE LOCAL - fences: antes de destruir los fences
  for (VkFence& fence : submissions_in_flight_fences_) {
    dfn.vkDestroyFence(device, fence, nullptr);
  }
''',
    ),
]


def localizar_sdk():
    raiz = pathlib.Path(__file__).resolve().parent.parent
    # NFSMW_SDK apunta a otro arbol del SDK (el de Android, por ejemplo). Si
    # esta puesta se usa SOLO esa ruta: caer en silencio en el SDK de Windows
    # parchearia el arbol equivocado.
    otro = os.environ.get("NFSMW_SDK")
    candidatos = [pathlib.Path(otro)] if otro else [raiz.parent / "rexglue-sdk", raiz / "sdk"]
    for cand in candidatos:
        if (cand / FICHERO).exists():
            return cand
    sys.exit(f"[ERROR] No encuentro {FICHERO} del SDK.\n"
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

    f = localizar_sdk() / FICHERO
    txt, eol = leer(f)
    puestos = sum(1 for _, nuevo in BLOQUES if nuevo in txt)

    if args.estado:
        estado = ("aplicado" if puestos == len(BLOQUES)
                  else "sin aplicar" if puestos == 0
                  else f"a medias ({puestos}/{len(BLOQUES)})")
        print(f"  fences                     {estado}")
        return 0

    if args.revertir:
        for ancla, nuevo in BLOQUES:
            txt = txt.replace(nuevo, ancla)
        escribir(f, txt, eol)
        print(f"[ok] Quitados {puestos} bloques")
        return 0

    for ancla, nuevo in BLOQUES:
        if nuevo not in txt and txt.count(ancla) != 1:
            sys.exit(f"[ERROR] Un anclaje no aparece exactamente una vez en {FICHERO}.\n"
                     "        El SDK habra cambiado. No he tocado nada.")
    for ancla, nuevo in BLOQUES:
        if nuevo not in txt:
            txt = txt.replace(ancla, nuevo)
    escribir(f, txt, eol)
    print("[ok] Aplicado: menos consultas de fences, y con vkGetFenceStatus")
    return 0


if __name__ == "__main__":
    sys.exit(main())
