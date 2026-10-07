#!/usr/bin/env python3
"""
Que cada pase de render cargue y guarde solo la zona que pinta.

    python tools/parche_area.py            aplicar
    python tools/parche_area.py --estado
    python tools/parche_area.py --revertir

Toca un fichero del SDK:  src/graphics/vulkan/deferred_command_buffer.cpp
No guarda .original: aplica y deshace por sustitucion de texto exacta.


EL FALLO
========

Medido con timestamps de Vulkan en el menu 3D (Adreno 830, ~44 fps): la GPU
esta ocupada el 95 % del tiempo, y la mitad se va en UNA clase de pase, la de
la escena principal: profundidad y color con MSAA 4x sobre un render target
de 1280x512. 11 pases por fotograma, 9,8 ms.

El juego pinta la escena en franjas (el "predicated tiling" de Xbox 360: la
EDRAM no da para 1280x720 con MSAA 4x), cada una de 1280x256. Pero el SDK
abre cada pase con el area de render del render target ENTERO y con
LOAD/STORE en todos los adjuntos. En una GPU de mosaicos eso significa leer y
escribir en memoria el render target completo -1280x512, 4 muestras, color y
profundidad: unos 42 MB- en cada pase, pinte lo que pinte. El de color 1x de
1280x2048 igual: se usa como mucho un tercio.


EL ARREGLO
==========

Al reproducir el bufer de comandos (se graba diferido, asi que ya esta todo
escrito cuando se abre el pase), antes de abrir cada pase se recorren sus
comandos hasta el final del pase y se une lo que pinta: la tijera vigente en
cada dibujo y los rectangulos de cada clear. El pase se abre con esa union,
redondeada a 32 px y nunca mas grande que el area original.

Vulkan garantiza que fuera del area de render los adjuntos no se tocan: las
operaciones de carga y guardado se limitan al area. Y todos los pipelines
graficos del SDK llevan la tijera como estado dinamico, asi que la union de
tijeras cubre todo lo que se dibuja. Si aparece un dibujo sin tijera conocida,
o un pase sin nada, se deja el area original.

Cvar vulkan_recortar_area, APAGADO por defecto: medido en el movil con el
driver de Qualcomm no cambia nada (el driver ya se saltaba lo que no se toca),
y el recuento previo recorre los comandos de cada pase, o sea que cuesta CPU en
el hilo del procesador de comandos. Queda por si con otro driver -Turnip- si
aporta.
"""

import argparse
import os
import pathlib
import sys


FICHERO = "src/graphics/vulkan/deferred_command_buffer.cpp"

BLOQUES = [
    (
        '''#include <rex/math.h>
''',
        '''#include <rex/math.h>

// PARCHE LOCAL - area recortada (tools/parche_area.py).
#include <algorithm>
#include <rex/cvar.h>
REXCVAR_DEFINE_BOOL(vulkan_recortar_area, false, "GPU/Vulkan",
                    "Abrir cada pase de render solo sobre la zona que pinta (la union de "
                    "tijeras y clears), en vez de cargar y guardar el render target entero");
''',
    ),
    (
        '''void DeferredCommandBuffer::Execute(VkCommandBuffer command_buffer) {
''',
        '''void DeferredCommandBuffer::Execute(VkCommandBuffer command_buffer) {
  // PARCHE LOCAL - area recortada: la tijera vigente al reproducir, y la
  // cuenta de lo que pinta cada pase antes de abrirlo (tools/parche_area.py).
  const bool nfsmw_recortar = REXCVAR_GET(vulkan_recortar_area);
  VkRect2D nfsmw_tijera = {};
  bool nfsmw_tijera_valida = false;
  auto nfsmw_area_del_pase = [&](const uintmax_t* p, size_t restante,
                                 const VkRect2D& original) -> VkRect2D {
    int64_t x0 = INT64_MAX, y0 = INT64_MAX, x1 = INT64_MIN, y1 = INT64_MIN;
    auto unir = [&](const VkRect2D& r) {
      x0 = std::min<int64_t>(x0, r.offset.x);
      y0 = std::min<int64_t>(y0, r.offset.y);
      x1 = std::max<int64_t>(x1, int64_t(r.offset.x) + r.extent.width);
      y1 = std::max<int64_t>(y1, int64_t(r.offset.y) + r.extent.height);
    };
    VkRect2D tijera = nfsmw_tijera;
    bool tijera_valida = nfsmw_tijera_valida;
    while (restante) {
      const CommandHeader& h = *reinterpret_cast<const CommandHeader*>(p);
      p += kCommandHeaderSizeElements;
      restante -= kCommandHeaderSizeElements;
      const uint8_t* a = reinterpret_cast<const uint8_t*>(p);
      if (h.command == Command::kVkEndRendering || h.command == Command::kVkEndRenderPass) {
        break;
      }
      switch (h.command) {
        case Command::kVkBeginRendering:
        case Command::kVkBeginRenderPass:
          return original;
        case Command::kVkSetScissor: {
          const auto& s = *reinterpret_cast<const ArgsVkSetScissor*>(a);
          if (s.first_scissor == 0 && s.scissor_count) {
            tijera = *reinterpret_cast<const VkRect2D*>(
                a + rex::align(sizeof(ArgsVkSetScissor), alignof(VkRect2D)));
            tijera_valida = true;
          }
        } break;
        case Command::kVkDraw:
        case Command::kVkDrawIndexed:
          if (!tijera_valida) {
            return original;
          }
          unir(tijera);
          break;
        case Command::kVkClearAttachments: {
          const auto& c = *reinterpret_cast<const ArgsVkClearAttachments*>(a);
          size_t o = rex::align(sizeof(ArgsVkClearAttachments), alignof(VkClearAttachment));
          o = rex::align(o + sizeof(VkClearAttachment) * c.attachment_count, alignof(VkClearRect));
          const auto* r = reinterpret_cast<const VkClearRect*>(a + o);
          for (uint32_t i = 0; i < c.rect_count; ++i) {
            unir(r[i].rect);
          }
        } break;
        default:
          break;
      }
      p += h.arguments_size_elements;
      restante -= h.arguments_size_elements;
    }
    if (x0 >= x1 || y0 >= y1) {
      return original;
    }
    // En multiplos de 32 px, y nunca fuera del area original.
    x0 = std::max<int64_t>(x0 & ~int64_t(31), original.offset.x);
    y0 = std::max<int64_t>(y0 & ~int64_t(31), original.offset.y);
    x1 = std::min<int64_t>((x1 + 31) & ~int64_t(31),
                           int64_t(original.offset.x) + original.extent.width);
    y1 = std::min<int64_t>((y1 + 31) & ~int64_t(31),
                           int64_t(original.offset.y) + original.extent.height);
    if (x0 >= x1 || y0 >= y1) {
      return original;
    }
    VkRect2D r;
    r.offset.x = int32_t(x0);
    r.offset.y = int32_t(y0);
    r.extent.width = uint32_t(x1 - x0);
    r.extent.height = uint32_t(y1 - y0);
    return r;
  };
''',
    ),
    (
        '''        rendering_info.renderArea = args.render_area;
''',
        '''        // PARCHE LOCAL - area recortada (tools/parche_area.py).
        rendering_info.renderArea =
            nfsmw_recortar ? nfsmw_area_del_pase(stream + header.arguments_size_elements,
                                                 stream_remaining - header.arguments_size_elements,
                                                 args.render_area)
                           : args.render_area;
''',
    ),
    (
        '''        auto& args = *reinterpret_cast<const ArgsVkSetScissor*>(stream);
        dfn.vkCmdSetScissor(command_buffer, args.first_scissor, args.scissor_count,
                            reinterpret_cast<const VkRect2D*>(
                                reinterpret_cast<const uint8_t*>(stream) +
                                rex::align(sizeof(ArgsVkSetScissor), alignof(VkRect2D))));
''',
        '''        auto& args = *reinterpret_cast<const ArgsVkSetScissor*>(stream);
        dfn.vkCmdSetScissor(command_buffer, args.first_scissor, args.scissor_count,
                            reinterpret_cast<const VkRect2D*>(
                                reinterpret_cast<const uint8_t*>(stream) +
                                rex::align(sizeof(ArgsVkSetScissor), alignof(VkRect2D))));
        if (args.first_scissor == 0 && args.scissor_count) {  // PARCHE LOCAL - area recortada
          nfsmw_tijera = *reinterpret_cast<const VkRect2D*>(
              reinterpret_cast<const uint8_t*>(stream) +
              rex::align(sizeof(ArgsVkSetScissor), alignof(VkRect2D)));
          nfsmw_tijera_valida = true;
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
                  else f"A MEDIAS ({puestos}/{len(BLOQUES)})")
        print(f"  area                       {estado}")
        return 0

    if args.revertir:
        if puestos == 0:
            print("[ok] area: no habia nada puesto")
            return 0
        for ancla, nuevo in BLOQUES:
            txt = txt.replace(nuevo, ancla)
        escribir(f, txt, eol)
        print(f"[ok] Quitados {puestos} bloques")
        return 0

    if puestos == len(BLOQUES):
        print("[ok] area: ya estaba")
        return 0
    if puestos:
        sys.exit(f"[ERROR] area esta a medias ({puestos}/{len(BLOQUES)}). "
                 "Revierte primero con --revertir.")
    for ancla, _ in BLOQUES:
        n = txt.count(ancla)
        if n != 1:
            sys.exit(f"[ERROR] Un anclaje aparece {n} veces en {FICHERO}, esperaba 1:\n"
                     f"        {ancla.splitlines()[0].strip()}\n"
                     "        El SDK habra cambiado. No he tocado nada.")
    for ancla, nuevo in BLOQUES:
        txt = txt.replace(ancla, nuevo)
    escribir(f, txt, eol)
    print("[ok] Aplicado: cada pase de render carga y guarda solo la zona que pinta")
    return 0


if __name__ == "__main__":
    sys.exit(main())
