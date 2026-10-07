#!/usr/bin/env python3
"""
Anade una cache de pipelines del driver (VkPipelineCache) que se guarda en disco.

    python tools/parche_cache_pipelines.py            aplicar
    python tools/parche_cache_pipelines.py --estado
    python tools/parche_cache_pipelines.py --revertir

Toca tres ficheros del SDK:
    include/rex/ui/vulkan/functions/device_1_0.inc   carga vkCreatePipelineCache y compania
    include/rex/graphics/vulkan/pipeline_cache.h     los miembros nuevos
    src/graphics/vulkan/pipeline_cache.cpp           cargar, usar y guardar la cache
No guarda .original: aplica y deshace por sustitucion de texto exacta.


POR QUE
=======

El SDK ya guarda en disco los shaders que ve (.xsh) y la lista de pipelines
que usa el juego (.xpso), y al arrancar vuelve a crear todos esos pipelines en
varios hilos ("Created N graphics pipelines from Vulkan storage"). Es lo mismo
que hace nfsmw-nx con su "lista de pipelines + precalentado".

Pero cada pipeline se creaba con vkCreateGraphicsPipelines(device,
VK_NULL_HANDLE, ...): sin cache del driver. Asi que en CADA arranque el driver
volvia a compilar cada pipeline desde SPIR-V, y en partida cada pipeline nuevo
costaba la compilacion entera. nfsmw-nx lo midio en Switch: ~59 ms por
pipeline sin cache, y 113 pipelines precalentados en 0,3 s con ella.


Y EL PRECREADO NUNCA HABIA FUNCIONADO EN ANDROID
================================================

El .xsh y el .xpso se abren con "a+b" y se lee la cabecera sin rebobinar. En
PC (glibc) "a+" empieza a leer por el principio; en Android (bionic, que hereda
la stdio de BSD) empieza AL FINAL. La cabecera no se leia, el SDK daba el
fichero por malo y lo vaciaba en cada arranque. Medido en el movil: el .xpso
tenia siempre exactamente los 125 pipelines de la sesion anterior (registros
de 66 bytes) y nunca se precreaba ninguno. Este parche rebobina al abrir.


COMO
====

- Al iniciar la persistencia de shaders (InitializeShaderStorage) se carga
  <titulo>.<fbo|fsi>.<vendor>-<device>-<driverVersion>.vkcache de la misma
  carpeta que el .xpso. Uno por driver: el de Qualcomm y un Turnip no comparten
  binarios, y una actualizacion del driver cambia driverVersion. La cabecera la
  comprueba el driver, y ademas aqui: vendor y device tienen que coincidir.
- Se pasa a vkCreateGraphicsPipelines, tambien en el precalentado.
- Se guarda cuando hay pipelines nuevos: justo despues del precalentado y,
  como mucho cada 10 s, desde el hilo que ya escribe el .xpso (el procesador de
  comandos solo lo pide). En Android el proceso del juego se mata al salir, asi
  que no se puede contar con guardar al cerrar. Se escribe en un .tmp y se
  renombra, para no dejar nunca un fichero a medias.
"""

import argparse
import os
import pathlib
import sys


INC = "include/rex/ui/vulkan/functions/device_1_0.inc"
H = "include/rex/graphics/vulkan/pipeline_cache.h"
CPP = "src/graphics/vulkan/pipeline_cache.cpp"

# (fichero, ancla, lo que la sustituye)
BLOQUES = [
    (
        INC,
        '''XE_UI_VULKAN_FUNCTION(vkCreateGraphicsPipelines)
''',
        '''XE_UI_VULKAN_FUNCTION(vkCreateGraphicsPipelines)
// PARCHE LOCAL - cache de pipelines (tools/parche_cache_pipelines.py).
XE_UI_VULKAN_FUNCTION(vkCreatePipelineCache)
XE_UI_VULKAN_FUNCTION(vkDestroyPipelineCache)
XE_UI_VULKAN_FUNCTION(vkGetPipelineCacheData)
''',
    ),
    (
        H,
        '''  std::filesystem::path shader_storage_cache_root_;
''',
        '''  // PARCHE LOCAL - cache de pipelines del driver, guardada en disco
  // (tools/parche_cache_pipelines.py).
  void NfsmwCargarCacheVulkan(const std::filesystem::path& carpeta, uint32_t title_id, bool fsi);
  void NfsmwGuardarCacheVulkan();
  std::atomic<VkPipelineCache> nfsmw_cache_vulkan_{VK_NULL_HANDLE};
  std::filesystem::path nfsmw_cache_vulkan_ruta_;
  std::mutex nfsmw_cache_vulkan_guardar_;
  // Hay pipelines nuevos que no estan en el fichero.
  std::atomic<bool> nfsmw_cache_vulkan_sucia_{false};
  // Solo el hilo del procesador de comandos: cuando se pidio guardar por ultima vez.
  uint64_t nfsmw_cache_vulkan_pedido_ms_ = 0;

  std::filesystem::path shader_storage_cache_root_;
''',
    ),
    (
        CPP,
        '''#include <array>
''',
        '''#include <array>
#include <chrono>  // PARCHE LOCAL - cache de pipelines
''',
    ),
    (
        CPP,
        '''  bool edram_fragment_shader_interlock =
      render_target_cache_.GetPath() == RenderTargetCache::Path::kPixelShaderInterlock;

  // Initialize the pipeline storage stream - read pipeline descriptions and
''',
        '''  bool edram_fragment_shader_interlock =
      render_target_cache_.GetPath() == RenderTargetCache::Path::kPixelShaderInterlock;

  // PARCHE LOCAL - cache de pipelines: antes del precalentado, que tambien la usa.
  NfsmwCargarCacheVulkan(shader_storage_shareable_root, title_id, edram_fragment_shader_interlock);

  // Initialize the pipeline storage stream - read pipeline descriptions and
''',
    ),
    (
        CPP,
        '''  pipeline_storage_file_ = rex::filesystem::OpenFile(pipeline_storage_file_path, "a+b");
''',
        '''  pipeline_storage_file_ = rex::filesystem::OpenFile(pipeline_storage_file_path, "a+b");
  // PARCHE LOCAL - cache de pipelines: a leer desde el principio. Con "a+" la
  // libc de Android (bionic, heredada de BSD) empieza AL FINAL; la de PC, al
  // principio. Sin esto la cabecera no se leia, el fichero se daba por malo y
  // se vaciaba en cada arranque: el precreado de pipelines nunca funciono en
  // Android. Escribir sigue yendo al final ("a" = O_APPEND).
  if (pipeline_storage_file_) {
    rex::filesystem::Seek(pipeline_storage_file_, 0, SEEK_SET);
  }
''',
    ),
    (
        CPP,
        '''  shader_storage_file_ = rex::filesystem::OpenFile(shader_storage_file_path, "a+b");
''',
        '''  shader_storage_file_ = rex::filesystem::OpenFile(shader_storage_file_path, "a+b");
  // PARCHE LOCAL - cache de pipelines: lo mismo con los shaders (ver arriba).
  if (shader_storage_file_) {
    rex::filesystem::Seek(shader_storage_file_, 0, SEEK_SET);
  }
''',
    ),
    (
        CPP,
        '''    REXGPU_INFO("Created {} graphics pipelines from Vulkan storage ({} requested)",
                created_pipeline_count.load(), pipeline_creations.size());
''',
        '''    REXGPU_INFO("Created {} graphics pipelines from Vulkan storage ({} requested)",
                created_pipeline_count.load(), pipeline_creations.size());
    // PARCHE LOCAL - cache de pipelines: lo recien compilado, al disco ya.
    NfsmwGuardarCacheVulkan();
''',
    ),
    (
        CPP,
        '''      fflush(pipeline_storage_file_);
''',
        '''      fflush(pipeline_storage_file_);
      // PARCHE LOCAL - cache de pipelines: aqui, en este hilo, y no en el del
      // procesador de comandos, que solo lo pide (EndSubmission).
      NfsmwGuardarCacheVulkan();
''',
    ),
    (
        CPP,
        '''void VulkanPipelineCache::ShutdownShaderStorage() {
''',
        '''// PARCHE LOCAL - cache de pipelines del driver (tools/parche_cache_pipelines.py).
namespace {
uint64_t NfsmwAhoraMs() {
  return uint64_t(std::chrono::duration_cast<std::chrono::milliseconds>(
                      std::chrono::steady_clock::now().time_since_epoch())
                      .count());
}
}  // namespace

void VulkanPipelineCache::NfsmwCargarCacheVulkan(const std::filesystem::path& carpeta,
                                                 uint32_t title_id, bool fsi) {
  const ui::vulkan::VulkanDevice* const vulkan_device = command_processor_.GetVulkanDevice();
  const ui::vulkan::VulkanDevice::Functions& dfn = vulkan_device->functions();
  const VkDevice device = vulkan_device->device();
  const auto& propiedades = vulkan_device->properties();
  // Uno por driver: el de Qualcomm y un Turnip no comparten binarios, y una
  // actualizacion del driver cambia driverVersion.
  nfsmw_cache_vulkan_ruta_ =
      carpeta / fmt::format("{:08X}.{}.{:04X}-{:04X}-{:08X}.vkcache", title_id, fsi ? "fsi" : "fbo",
                            propiedades.vendorID, propiedades.deviceID, propiedades.driverVersion);
  if (nfsmw_cache_vulkan_.load(std::memory_order_acquire) != VK_NULL_HANDLE) {
    // Ya hay una: cambiarla con hilos de creacion que puedan estar usandola no
    // es seguro, y es la misma partida.
    return;
  }
  std::vector<uint8_t> datos;
  if (FILE* f = rex::filesystem::OpenFile(nfsmw_cache_vulkan_ruta_, "rb")) {
    fseek(f, 0, SEEK_END);
    const long tamano = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (tamano > 0 && tamano < (long(256) << 20)) {
      datos.resize(size_t(tamano));
      if (fread(datos.data(), 1, datos.size(), f) != datos.size()) {
        datos.clear();
      }
    }
    fclose(f);
  }
  // La cabecera (VkPipelineCacheHeaderVersionOne) la comprueba el driver, pero
  // no todos los de Android son de fiar con datos ajenos: se mira aqui tambien.
  if (datos.size() >= 32) {
    uint32_t cabecera[4];
    std::memcpy(cabecera, datos.data(), sizeof(cabecera));
    if (cabecera[0] < 32 || cabecera[1] != uint32_t(VK_PIPELINE_CACHE_HEADER_VERSION_ONE) ||
        cabecera[2] != propiedades.vendorID || cabecera[3] != propiedades.deviceID) {
      REXGPU_WARN("[cache de pipelines] {} no es de este driver: se empieza vacia",
                  rex::path_to_utf8(nfsmw_cache_vulkan_ruta_.filename()));
      datos.clear();
    }
  } else {
    datos.clear();
  }
  VkPipelineCacheCreateInfo info = {};
  info.sType = VK_STRUCTURE_TYPE_PIPELINE_CACHE_CREATE_INFO;
  info.initialDataSize = datos.size();
  info.pInitialData = datos.empty() ? nullptr : datos.data();
  VkPipelineCache cache = VK_NULL_HANDLE;
  if (dfn.vkCreatePipelineCache(device, &info, nullptr, &cache) != VK_SUCCESS) {
    // Con los datos rechazados, una vacia.
    info.initialDataSize = 0;
    info.pInitialData = nullptr;
    if (dfn.vkCreatePipelineCache(device, &info, nullptr, &cache) != VK_SUCCESS) {
      REXGPU_WARN("[cache de pipelines] no se pudo crear: se sigue sin ella");
      return;
    }
    datos.clear();
  }
  nfsmw_cache_vulkan_.store(cache, std::memory_order_release);
  REXGPU_INFO("[cache de pipelines] {} KB cargados de {}", datos.size() / 1024,
              rex::path_to_utf8(nfsmw_cache_vulkan_ruta_.filename()));
}

void VulkanPipelineCache::NfsmwGuardarCacheVulkan() {
  std::lock_guard<std::mutex> lock(nfsmw_cache_vulkan_guardar_);
  const VkPipelineCache cache = nfsmw_cache_vulkan_.load(std::memory_order_acquire);
  if (cache == VK_NULL_HANDLE || nfsmw_cache_vulkan_ruta_.empty() ||
      !nfsmw_cache_vulkan_sucia_.exchange(false, std::memory_order_acq_rel)) {
    return;
  }
  const ui::vulkan::VulkanDevice* const vulkan_device = command_processor_.GetVulkanDevice();
  const ui::vulkan::VulkanDevice::Functions& dfn = vulkan_device->functions();
  const VkDevice device = vulkan_device->device();
  size_t tamano = 0;
  if (dfn.vkGetPipelineCacheData(device, cache, &tamano, nullptr) != VK_SUCCESS || !tamano) {
    return;
  }
  std::vector<uint8_t> datos(tamano);
  // VK_INCOMPLETE si ha crecido entre las dos llamadas: lo escrito sigue siendo
  // una cache valida, solo que sin lo ultimo.
  const VkResult resultado = dfn.vkGetPipelineCacheData(device, cache, &tamano, datos.data());
  if (resultado != VK_SUCCESS && resultado != VK_INCOMPLETE) {
    return;
  }
  datos.resize(tamano);
  std::filesystem::path temporal = nfsmw_cache_vulkan_ruta_;
  temporal += ".tmp";
  FILE* f = rex::filesystem::OpenFile(temporal, "wb");
  if (!f) {
    return;
  }
  const bool escrito = fwrite(datos.data(), 1, datos.size(), f) == datos.size();
  fclose(f);
  std::error_code error;
  if (escrito) {
    std::filesystem::rename(temporal, nfsmw_cache_vulkan_ruta_, error);
  }
  if (!escrito || error) {
    std::filesystem::remove(temporal, error);
    return;
  }
  REXGPU_INFO("[cache de pipelines] {} KB guardados", datos.size() / 1024);
}

void VulkanPipelineCache::ShutdownShaderStorage() {
  // PARCHE LOCAL - cache de pipelines: lo que quede sin guardar.
  NfsmwGuardarCacheVulkan();
''',
    ),
    (
        CPP,
        '''void VulkanPipelineCache::EndSubmission() {
''',
        '''void VulkanPipelineCache::EndSubmission() {
  // PARCHE LOCAL - cache de pipelines: con pipelines nuevos, pedir que se guarde,
  // como mucho cada 10 s. Lo hace el hilo que escribe el .xpso, al vaciar.
  if (nfsmw_cache_vulkan_sucia_.load(std::memory_order_relaxed) && pipeline_storage_file_) {
    const uint64_t ahora = NfsmwAhoraMs();
    if (ahora - nfsmw_cache_vulkan_pedido_ms_ >= 10000) {
      nfsmw_cache_vulkan_pedido_ms_ = ahora;
      pipeline_storage_file_flush_needed_ = true;
    }
  }
''',
    ),
    (
        CPP,
        '''  ShutdownShaderStorage();

  const ui::vulkan::VulkanDevice* const vulkan_device = command_processor_.GetVulkanDevice();
  const ui::vulkan::VulkanDevice::Functions& dfn = vulkan_device->functions();
  const VkDevice device = vulkan_device->device();
''',
        '''  ShutdownShaderStorage();

  const ui::vulkan::VulkanDevice* const vulkan_device = command_processor_.GetVulkanDevice();
  const ui::vulkan::VulkanDevice::Functions& dfn = vulkan_device->functions();
  const VkDevice device = vulkan_device->device();

  // PARCHE LOCAL - cache de pipelines: ya guardada, y sin hilos que la usen.
  if (const VkPipelineCache cache = nfsmw_cache_vulkan_.exchange(VK_NULL_HANDLE);
      cache != VK_NULL_HANDLE) {
    dfn.vkDestroyPipelineCache(device, cache, nullptr);
  }
''',
    ),
    (
        CPP,
        '''  VkResult create_result = dfn.vkCreateGraphicsPipelines(device, VK_NULL_HANDLE, 1,
                                                         &pipeline_create_info, nullptr, &pipeline);
''',
        '''  // PARCHE LOCAL - cache de pipelines: con la del driver, no VK_NULL_HANDLE.
  VkResult create_result = dfn.vkCreateGraphicsPipelines(
      device, nfsmw_cache_vulkan_.load(std::memory_order_acquire), 1, &pipeline_create_info,
      nullptr, &pipeline);
  if (create_result == VK_SUCCESS) {
    nfsmw_cache_vulkan_sucia_.store(true, std::memory_order_relaxed);
  }
''',
    ),
]


def localizar_sdk():
    raiz = pathlib.Path(__file__).resolve().parent.parent
    otro = os.environ.get("NFSMW_SDK")
    candidatos = [pathlib.Path(otro)] if otro else [raiz.parent / "rexglue-sdk", raiz / "sdk"]
    for cand in candidatos:
        if all((cand / f).exists() for f in (INC, H, CPP)):
            return cand
    sys.exit(f"[ERROR] No encuentro {CPP} y compania del SDK.\n"
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
    textos = {f: leer(sdk / f) for f in (INC, H, CPP)}
    puestos = sum(1 for f, _, nuevo in BLOQUES if nuevo in textos[f][0])

    if args.estado:
        estado = ("aplicado" if puestos == len(BLOQUES) else "sin aplicar" if puestos == 0
                  else f"A MEDIAS ({puestos}/{len(BLOQUES)})")
        print(f"  cache_pipelines            {estado}")
        return 0

    if args.revertir:
        if puestos == 0:
            print("[ok] cache_pipelines: no habia nada puesto")
            return 0
        if puestos != len(BLOQUES):
            sys.exit(f"[ERROR] Solo encuentro {puestos} de {len(BLOQUES)} bloques. No quito nada "
                     "a medias: mira el SDK a mano.")
        for f, ancla, nuevo in BLOQUES:
            txt, eol = textos[f]
            textos[f] = (txt.replace(nuevo, ancla), eol)
        for f, (txt, eol) in textos.items():
            escribir(sdk / f, txt, eol)
        print(f"[ok] Quitados {puestos} bloques")
        return 0

    if puestos == len(BLOQUES):
        print("[ok] cache_pipelines: ya estaba")
        return 0
    if puestos:
        sys.exit(f"[ERROR] cache_pipelines esta a medias ({puestos}/{len(BLOQUES)}). "
                 "Revierte primero con --revertir.")
    for f, ancla, _ in BLOQUES:
        n = textos[f][0].count(ancla)
        if n != 1:
            sys.exit(f"[ERROR] Un anclaje aparece {n} veces en {f}, esperaba 1:\n"
                     f"        {ancla.splitlines()[0].strip()}\n"
                     "        El SDK habra cambiado. No he tocado nada.")
    for f, ancla, nuevo in BLOQUES:
        txt, eol = textos[f]
        textos[f] = (txt.replace(ancla, nuevo, 1), eol)
    for f, (txt, eol) in textos.items():
        escribir(sdk / f, txt, eol)
    print("[ok] Aplicado: cache de pipelines del driver en disco")
    return 0


if __name__ == "__main__":
    sys.exit(main())
