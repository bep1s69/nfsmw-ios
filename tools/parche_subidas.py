#!/usr/bin/env python3
"""
Adelanta las subidas de memoria a antes del pase de render, sin cortarlo.

    python tools/parche_subidas.py            aplicar
    python tools/parche_subidas.py --estado
    python tools/parche_subidas.py --revertir

Toca seis ficheros del SDK (ver BLOQUES). Anade el cvar vulkan_adelantar_subidas
(por defecto true). No guarda .original: sustitucion de texto exacta.


EL FALLO
========

Casi todo lo que dibuja la Xenos lee de la memoria compartida: un buffer de
Vulkan de 512 MB que refleja la memoria fisica del guest. Cuando el juego
escribe con la CPU datos que la GPU va a leer (vertices dinamicos, por
ejemplo), el procesador de comandos los sube a ese buffer con una copia antes
del dibujado que los usa.

Una copia (vkCmdCopyBuffer) no puede ir dentro de un pase de render, asi que
cada subida hacia: cerrar el pase, barrera, copia, barrera, y volver a abrir el
pase con LOAD_OP_LOAD / STORE_OP_STORE. En una GPU de mosaicos como Adreno,
cerrar y reabrir un pase es volcar los render targets de la memoria del chip
(GMEM) a la RAM y volver a cargarlos.

Medido en el menu 3D con el driver de Qualcomm: unas 237 subidas por fotograma,
y la GPU ocupada el 99 % del tiempo (timestamps de Vulkan al principio y al
final de cada envio), unos 100 ms por fotograma que no dependian de ningun
ajuste grafico.


EL ARREGLO
==========

El flujo de comandos se graba en un buffer diferido y se reproduce al final del
envio, asi que se puede insertar algo en un punto ya grabado. Al abrir un pase
se anota donde empieza en el flujo. Si llega una subida con el pase abierto y
NINGUN dibujado de ese pase ha pedido esas paginas (SharedMemory lleva la
cuenta de lo pedido desde que empezo el pase), la barrera, la copia y la
barrera se graban al final y se rotan a justo antes del inicio del pase. El
pase no se corta. Los dibujados anteriores del pase no leian esas paginas, asi
que para ellos no cambia nada; los posteriores las ven ya subidas.

Si el pase ya leyo esas paginas, se hace como antes. Con
vulkan_adelantar_subidas=false, todo como antes.

Medido en el menu 3D: se adelantan ~19 de cada 20 subidas, y el menu pasa de
42-43 a 50-52 fps. La imagen sale igual.
"""

import argparse
import os
import pathlib
import sys


CMDBUF_H = "include/rex/graphics/vulkan/deferred_command_buffer.h"
SHMEM_H = "include/rex/graphics/shared_memory.h"
SHMEM_CPP = "src/graphics/shared_memory.cpp"
CP_H = "include/rex/graphics/vulkan/command_processor.h"
CP_CPP = "src/graphics/vulkan/command_processor.cpp"
VKSHMEM_CPP = "src/graphics/vulkan/shared_memory.cpp"

# (fichero, ancla, nuevo, veces que aparece el ancla)
BLOQUES = [
    (CMDBUF_H,
     '''#include <vector>
''',
     '''#include <algorithm>  // PARCHE LOCAL - subidas adelantadas
#include <vector>
''', 1),
    (CMDBUF_H,
     '''  void Reset();
  void Execute(VkCommandBuffer command_buffer);
''',
     '''  void Reset();
  void Execute(VkCommandBuffer command_buffer);

  // PARCHE LOCAL - subidas adelantadas: tamano del flujo grabado, y mover lo
  // grabado desde 'desde' hasta el final a la posicion 'a' (a <= desde). Los
  // comandos llevan sus argumentos dentro, asi que se pueden mover enteros.
  size_t NfsmwTamano() const { return command_stream_.size(); }
  void NfsmwMoverCola(size_t a, size_t desde) {
    std::rotate(command_stream_.begin() + a, command_stream_.begin() + desde,
                command_stream_.end());
  }
''', 1),
    (SHMEM_H,
     '''  bool RequestRange(uint32_t start, uint32_t length);
''',
     '''  bool RequestRange(uint32_t start, uint32_t length);

  // PARCHE LOCAL - subidas adelantadas: paginas pedidas desde que empezo el
  // pase de render actual. Si hay demasiadas para mirar, se da por leido.
  void NfsmwEmpezarPase() { nfsmw_lecturas_pase_.clear(); }
  bool NfsmwLeidoEnElPase(uint32_t pagina, uint32_t paginas) const {
    if (nfsmw_lecturas_pase_.size() > 4096) {
      return true;
    }
    for (const std::pair<uint32_t, uint32_t>& r : nfsmw_lecturas_pase_) {
      if (pagina < r.first + r.second && r.first < pagina + paginas) {
        return true;
      }
    }
    return false;
  }
''', 1),
    (SHMEM_H,
     '''  std::vector<std::pair<uint32_t, uint32_t>> upload_ranges_;
''',
     '''  std::vector<std::pair<uint32_t, uint32_t>> upload_ranges_;
  // PARCHE LOCAL - subidas adelantadas: (primera pagina, paginas) pedidas en
  // el pase de render actual.
  std::vector<std::pair<uint32_t, uint32_t>> nfsmw_lecturas_pase_;
''', 1),
    (SHMEM_CPP,
     '''  if (upload_ranges_.empty()) {
    return true;
  }

  return UploadRanges(upload_ranges_);
}
''',
     '''  const bool nfsmw_subido = upload_ranges_.empty() || UploadRanges(upload_ranges_);
  // PARCHE LOCAL - subidas adelantadas: lo pedido lo lee lo que viene detras
  // (el dibujado), asi que desde ahora cuenta como leido en este pase. Se
  // apunta despues de subir: su propia subida si se puede adelantar.
  for (const std::pair<uint32_t, uint32_t>& range : merged_ranges) {
    const uint32_t pagina = range.first >> page_size_log2_;
    nfsmw_lecturas_pase_.emplace_back(
        pagina, ((range.first + range.second - 1) >> page_size_log2_) - pagina + 1);
  }
  return nfsmw_subido;
}
''', 1),
    (CP_H,
     '''  DeferredCommandBuffer& deferred_command_buffer() {
    assert_true(submission_open_);
    return deferred_command_buffer_;
  }
''',
     '''  DeferredCommandBuffer& deferred_command_buffer() {
    assert_true(submission_open_);
    return deferred_command_buffer_;
  }

  // PARCHE LOCAL - subidas adelantadas: donde empieza en el flujo diferido el
  // pase de render abierto, o SIZE_MAX si no hay uno de los que admiten
  // adelantar subidas.
  size_t NfsmwInicioPase() const { return in_render_pass_ ? nfsmw_inicio_pase_ : SIZE_MAX; }
  void NfsmwPaseDesplazado(size_t elementos) { nfsmw_inicio_pase_ += elementos; }
''', 1),
    (CP_H,
     '''  bool in_render_pass_ = false;
''',
     '''  bool in_render_pass_ = false;
  size_t nfsmw_inicio_pase_ = SIZE_MAX;  // PARCHE LOCAL - subidas adelantadas
''', 1),
    (CP_CPP,
     '''  current_render_pass_ = use_dynamic_rendering ? VK_NULL_HANDLE : render_pass;
  current_framebuffer_ = framebuffer;
''',
     '''  current_render_pass_ = use_dynamic_rendering ? VK_NULL_HANDLE : render_pass;
  current_framebuffer_ = framebuffer;
  // PARCHE LOCAL - subidas adelantadas: aqui empieza el pase en el flujo.
  nfsmw_inicio_pase_ = deferred_command_buffer_.NfsmwTamano();
  if (shared_memory_) {
    shared_memory_->NfsmwEmpezarPase();
  }
''', 2),
    (CP_CPP,
     '''void VulkanCommandProcessor::EndRenderPass() {
  assert_true(submission_open_);
''',
     '''void VulkanCommandProcessor::EndRenderPass() {
  assert_true(submission_open_);
  nfsmw_inicio_pase_ = SIZE_MAX;  // PARCHE LOCAL - subidas adelantadas
''', 1),
    (VKSHMEM_CPP,
     '''#include <rex/graphics/vulkan/shared_memory.h>
''',
     '''#include <rex/graphics/vulkan/shared_memory.h>

// PARCHE LOCAL - subidas adelantadas: ver tools/parche_subidas.py.
REXCVAR_DEFINE_BOOL(vulkan_adelantar_subidas, true, "GPU/Vulkan",
                    "Grabar las subidas a la memoria compartida antes del pase de render abierto "
                    "(si el pase no ha leido esas paginas) en vez de cortarlo");
''', 1),
    (VKSHMEM_CPP,
     '''  Use(Usage::kTransferDestination,
      std::make_pair(upload_page_ranges.front().first << page_size_log2(),
                     (upload_page_ranges.back().first + upload_page_ranges.back().second -
                      upload_page_ranges.front().first)
                         << page_size_log2()));
  command_processor_.SubmitBarriers(true);
  DeferredCommandBuffer& command_buffer = command_processor_.deferred_command_buffer();
''',
     '''  // PARCHE LOCAL - subidas adelantadas: si hay un pase abierto que no ha
  // leido estas paginas, la barrera, la copia y la barrera se graban al final
  // y luego se mueven a antes del inicio del pase, que asi no se corta.
  DeferredCommandBuffer& command_buffer = command_processor_.deferred_command_buffer();
  const uint32_t nfsmw_pagina = upload_page_ranges.front().first;
  const uint32_t nfsmw_paginas =
      upload_page_ranges.back().first + upload_page_ranges.back().second - nfsmw_pagina;
  const size_t nfsmw_inicio_pase = command_processor_.NfsmwInicioPase();
  const bool nfsmw_adelantar = REXCVAR_GET(vulkan_adelantar_subidas) &&
                               nfsmw_inicio_pase != SIZE_MAX &&
                               !NfsmwLeidoEnElPase(nfsmw_pagina, nfsmw_paginas);
  const size_t nfsmw_cola = command_buffer.NfsmwTamano();
  VkBufferMemoryBarrier nfsmw_barrera = {};
  nfsmw_barrera.sType = VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER;
  nfsmw_barrera.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
  nfsmw_barrera.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
  nfsmw_barrera.buffer = buffer_;
  nfsmw_barrera.offset = VkDeviceSize(nfsmw_pagina) << page_size_log2();
  nfsmw_barrera.size = VkDeviceSize(nfsmw_paginas) << page_size_log2();
  if (nfsmw_adelantar) {
    nfsmw_barrera.srcAccessMask = VK_ACCESS_MEMORY_READ_BIT | VK_ACCESS_MEMORY_WRITE_BIT;
    nfsmw_barrera.dstAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
    command_buffer.CmdVkPipelineBarrier(VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,
                                        VK_PIPELINE_STAGE_TRANSFER_BIT, 0, 0, nullptr, 1,
                                        &nfsmw_barrera, 0, nullptr);
  } else {
  Use(Usage::kTransferDestination,
      std::make_pair(upload_page_ranges.front().first << page_size_log2(),
                     (upload_page_ranges.back().first + upload_page_ranges.back().second -
                      upload_page_ranges.front().first)
                         << page_size_log2()));
  command_processor_.SubmitBarriers(true);
  }
''', 1),
    (VKSHMEM_CPP,
     '''  if (!upload_regions_.empty()) {
    assert_true(upload_buffer_previous != VK_NULL_HANDLE);
    command_buffer.CmdVkCopyBuffer(upload_buffer_previous, buffer_,
                                   uint32_t(upload_regions_.size()), upload_regions_.data());
    upload_regions_.clear();
  }
  return successful;
}
''',
     '''  if (!upload_regions_.empty()) {
    assert_true(upload_buffer_previous != VK_NULL_HANDLE);
    command_buffer.CmdVkCopyBuffer(upload_buffer_previous, buffer_,
                                   uint32_t(upload_regions_.size()), upload_regions_.data());
    upload_regions_.clear();
  }
  // PARCHE LOCAL - subidas adelantadas: cerrar con la barrera de vuelta y
  // mover todo lo grabado desde nfsmw_cola a antes del inicio del pase.
  static uint64_t nfsmw_adelantadas = 0, nfsmw_en_su_sitio = 0;
  if (nfsmw_adelantar) {
    nfsmw_barrera.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
    nfsmw_barrera.dstAccessMask = VK_ACCESS_MEMORY_READ_BIT | VK_ACCESS_MEMORY_WRITE_BIT;
    command_buffer.CmdVkPipelineBarrier(VK_PIPELINE_STAGE_TRANSFER_BIT,
                                        VK_PIPELINE_STAGE_ALL_COMMANDS_BIT, 0, 0, nullptr, 1,
                                        &nfsmw_barrera, 0, nullptr);
    const size_t nfsmw_movido = command_buffer.NfsmwTamano() - nfsmw_cola;
    command_buffer.NfsmwMoverCola(nfsmw_inicio_pase, nfsmw_cola);
    command_processor_.NfsmwPaseDesplazado(nfsmw_movido);
    ++nfsmw_adelantadas;
  } else {
    ++nfsmw_en_su_sitio;
  }
  if (nfsmw_adelantadas + nfsmw_en_su_sitio >= 200000) {
    REXGPU_INFO("subidas a la memoria compartida: {} adelantadas al inicio del pase, {} cortandolo",
                nfsmw_adelantadas, nfsmw_en_su_sitio);
    nfsmw_adelantadas = nfsmw_en_su_sitio = 0;
  }
  return successful;
}
''', 1),
]

FICHEROS = [CMDBUF_H, SHMEM_H, SHMEM_CPP, CP_H, CP_CPP, VKSHMEM_CPP]


def localizar_sdk():
    raiz = pathlib.Path(__file__).resolve().parent.parent
    # NFSMW_SDK apunta a otro arbol del SDK (el de Android, por ejemplo). Si
    # esta puesta se usa SOLO esa ruta: caer en silencio en el SDK de Windows
    # parchearia el arbol equivocado.
    otro = os.environ.get("NFSMW_SDK")
    candidatos = [pathlib.Path(otro)] if otro else [raiz.parent / "rexglue-sdk", raiz / "sdk"]
    for cand in candidatos:
        if all((cand / f).exists() for f in FICHEROS):
            return cand
    sys.exit("[ERROR] No encuentro los ficheros del SDK.\n"
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
    textos = {f: leer(sdk / f) for f in FICHEROS}
    puestos = sum(1 for f, _, nuevo, _ in BLOQUES if nuevo in textos[f][0])

    if args.estado:
        estado = ("aplicado" if puestos == len(BLOQUES)
                  else "sin aplicar" if puestos == 0
                  else f"a medias ({puestos}/{len(BLOQUES)})")
        print(f"  subidas adelantadas        {estado}")
        return 0

    if args.revertir:
        for f, ancla, nuevo, _ in reversed(BLOQUES):
            txt, eol = textos[f]
            textos[f] = (txt.replace(nuevo, ancla), eol)
        for f, (txt, eol) in textos.items():
            escribir(sdk / f, txt, eol)
        print(f"[ok] Quitados {puestos} bloques")
        return 0

    for f, ancla, nuevo, veces in BLOQUES:
        txt = textos[f][0]
        if nuevo not in txt and txt.count(ancla) != veces:
            sys.exit(f"[ERROR] Un anclaje aparece {txt.count(ancla)} veces en {f}, esperaba "
                     f"{veces}.\n        El SDK habra cambiado. No he tocado nada.")
    for f, ancla, nuevo, _ in BLOQUES:
        txt, eol = textos[f]
        if nuevo not in txt:
            textos[f] = (txt.replace(ancla, nuevo), eol)
    for f, (txt, eol) in textos.items():
        escribir(sdk / f, txt, eol)
    print("[ok] Aplicado: subidas adelantadas al inicio del pase (vulkan_adelantar_subidas)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
