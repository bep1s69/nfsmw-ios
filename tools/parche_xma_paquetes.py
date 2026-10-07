#!/usr/bin/env python3
"""
Trae de Xenia Canary el manejo de paquetes XMA que cruzan de buffer de entrada.

    python tools/parche_xma_paquetes.py            aplicar
    python tools/parche_xma_paquetes.py --estado
    python tools/parche_xma_paquetes.py --revertir

Toca dos ficheros del SDK:
    include/rex/audio/xma/context.h
    src/audio/xma_context.cpp
No guarda .original: aplica y deshace por sustitucion de texto exacta.


DE DONDE SALE
=============

El SDK ya lleva el descodificador XMA nuevo de Xenia (el de xma_context_new),
pero de una version anterior a la actual de Canary. Lo que falta es justo la
parte que Canary reescribio despues: como se localiza el paquete siguiente
cuando la cuenta de saltos se sale del buffer de entrada actual.

Portado de xenia-canary, src/xenia/apu/xma_context_new.cc (BSD-3, como el resto
del SDK): kPacketHandle, GetPacketHandle, las dos versiones de
GetNextPacketReadOffset y los dos sitios de Decode que las usan.


EL FALLO
========

Cada contexto XMA tiene DOS buffers de entrada y el juego los va alternando.
Un paquete dice cuantos paquetes hay que saltarse para llegar al siguiente con
una trama nueva, y esa cuenta puede pasarse del final del buffer actual: el
paquete que toca esta en el otro buffer, a N paquetes de su principio.

El SDK devolvia, en ese caso, el PRIMER paquete del otro buffer, sin restar los
que quedaban en el actual:

    if (next_packet_index < current_input_packet_count) { ...paquete normal... }
    ...
    return memory()->TranslatePhysical(next_buffer_address);   // siempre el 0

Asi que en cada cruce de buffer con salto se descodificaba el paquete
equivocado. Y ademas GetNextPacketReadOffset, al buscar donde empieza la
siguiente trama, avanzaba de uno en uno en vez de seguir la cadena de saltos, y
no sabia mirar en el otro buffer: devolvia "no hay nada" y forzaba un cambio de
buffer aunque el paquete estuviera ahi.

Sintoma: audio entrecortado, y de vez en cuando una voz que se queda sin
producir nada. En el juego eso se ve como un corte de varios segundos, hasta
que tools/parche_desatasco.py rompe la espera desde fuera.


EL ARREGLO
==========

kPacketHandle resuelve el par (buffer, indice) de verdad: si el indice se pasa
del buffer actual, cambia de buffer y RESTA los paquetes que quedaban, y
comprueba que ese buffer este marcado valido, tenga puntero y sea bastante
largo. Con eso:

  - GetNextPacket devuelve el paquete correcto, este donde este.
  - GetNextPacketReadOffset sigue la cadena de saltos (skip + 1, y corta en
    0xFF) y puede buscar en el otro buffer.
  - Decode usa esa version en el salto de paquete completo (0xFF) y al pasar de
    paquete, y cambia de buffer cuando el indice se sale de verdad.
"""

import argparse
import os
import pathlib
import sys


FICHERO_H = "include/rex/audio/xma/context.h"
FICHERO_CPP = "src/audio/xma_context.cpp"

# --- context.h -------------------------------------------------------------

H_STRUCT_ANCLA = '''static constexpr int kIdToSampleRate[4] = {24000, 32000, 44100, 48000};
'''

H_STRUCT_NUEVO = '''// PARCHE LOCAL - paquetes XMA (tools/parche_xma_paquetes.py): el par
// (buffer, indice) de un paquete ya resuelto, que puede estar en el otro
// buffer de entrada. Portado de Xenia Canary.
struct kPacketHandle {
  uint8_t buffer_index_ = 0;
  uint32_t packet_index_ = 0;
  bool is_valid_ = false;
};

static constexpr int kIdToSampleRate[4] = {24000, 32000, 44100, 48000};
'''

H_DECL_ANCLA = '''  const uint8_t* GetNextPacket(XMA_CONTEXT_DATA* data, uint32_t next_packet_index,
                               uint32_t current_input_packet_count);
  uint32_t GetNextPacketReadOffset(uint8_t* buffer, uint32_t next_packet_index,
                                   uint32_t current_input_packet_count);
'''

H_DECL_NUEVO = '''  // PARCHE LOCAL - paquetes XMA (tools/parche_xma_paquetes.py).
  kPacketHandle GetPacketHandle(XMA_CONTEXT_DATA* data, uint32_t buffer_index,
                                uint32_t packet_index, uint32_t current_input_packet_count);
  const uint8_t* GetNextPacket(XMA_CONTEXT_DATA* data, uint32_t next_packet_index,
                               uint32_t current_input_packet_count);
  uint32_t GetNextPacketReadOffset(uint8_t* buffer, uint32_t next_packet_index,
                                   uint32_t current_input_packet_count);
  // PARCHE LOCAL - paquetes XMA: la que sabe cruzar al otro buffer.
  uint32_t GetNextPacketReadOffset(XMA_CONTEXT_DATA* data, uint32_t next_packet_index,
                                   uint32_t current_input_packet_count);
'''

# --- xma_context.cpp -------------------------------------------------------

CPP_GETNEXT_ANCLA = '''const uint8_t* XmaContext::GetNextPacket(XMA_CONTEXT_DATA* data, uint32_t next_packet_index,
                                         uint32_t current_input_packet_count) {
  if (next_packet_index < current_input_packet_count) {
    return memory()->TranslatePhysical(data->GetCurrentInputBufferAddress()) +
           next_packet_index * kBytesPerPacket;
  }

  const uint8_t next_buffer_index = data->current_buffer ^ 1;
  if (!data->IsInputBufferValid(next_buffer_index)) {
    return nullptr;
  }

  const uint32_t next_buffer_address = data->GetInputBufferAddress(next_buffer_index);
  if (!next_buffer_address) {
    REXAPU_ERROR("XmaContext {}: Buffer marked valid but has null pointer!", id());
    return nullptr;
  }

  return memory()->TranslatePhysical(next_buffer_address);
}
'''

CPP_GETNEXT_NUEVO = '''// PARCHE LOCAL - paquetes XMA (tools/parche_xma_paquetes.py): resuelve en que
// buffer y en que posicion esta un paquete cuyo indice puede pasarse del buffer
// actual. Portado de Xenia Canary (xma_context_new.cc).
kPacketHandle XmaContext::GetPacketHandle(XMA_CONTEXT_DATA* data, uint32_t buffer_index,
                                          uint32_t packet_index,
                                          uint32_t current_input_packet_count) {
  kPacketHandle resultado{};
  const bool esta_en_el_otro = packet_index >= current_input_packet_count;
  if (esta_en_el_otro) {
    buffer_index = buffer_index ^ 1;
    packet_index = packet_index - current_input_packet_count;
  }

  if (!data->IsInputBufferValid(static_cast<uint8_t>(buffer_index))) {
    return resultado;
  }

  const uint32_t direccion = data->GetInputBufferAddress(static_cast<uint8_t>(buffer_index));
  if (!direccion) {
    REXAPU_ERROR(
        "XmaContext {}: el paquete deberia estar en el buffer {}, pero el buffer marcado "
        "como valido tiene puntero nulo",
        id(), esta_en_el_otro ? "siguiente" : "actual");
    return resultado;
  }

  const uint32_t paquetes = data->GetInputBufferPacketCount(static_cast<uint8_t>(buffer_index));
  if (packet_index >= paquetes) {
    REXAPU_ERROR(
        "XmaContext {}: el paquete deberia estar en el buffer {}, pero ese buffer es "
        "demasiado corto para contenerlo",
        id(), esta_en_el_otro ? "siguiente" : "actual");
    return resultado;
  }

  resultado.buffer_index_ = static_cast<uint8_t>(buffer_index);
  resultado.packet_index_ = packet_index;
  resultado.is_valid_ = true;
  return resultado;
}

const uint8_t* XmaContext::GetNextPacket(XMA_CONTEXT_DATA* data, uint32_t next_packet_index,
                                         uint32_t current_input_packet_count) {
  // PARCHE LOCAL - paquetes XMA: antes, si el indice se pasaba del buffer
  // actual, se devolvia el PRIMER paquete del otro sin restar los que quedaban.
  const kPacketHandle paquete =
      GetPacketHandle(data, data->current_buffer, next_packet_index, current_input_packet_count);
  if (!paquete.is_valid_) {
    return nullptr;
  }

  const uint32_t direccion = data->GetInputBufferAddress(paquete.buffer_index_);
  return memory()->TranslatePhysical(direccion) + paquete.packet_index_ * kBytesPerPacket;
}
'''

CPP_OFFSET_ANCLA = '''uint32_t XmaContext::GetNextPacketReadOffset(uint8_t* buffer, uint32_t next_packet_index,
                                             uint32_t current_input_packet_count) {
  while (next_packet_index < current_input_packet_count) {
    uint8_t* next_packet = buffer + (next_packet_index * kBytesPerPacket);
    const uint32_t packet_frame_offset = xma::GetPacketFrameOffset(next_packet);

    if (packet_frame_offset <= kMaxFrameSizeinBits) {
      return (next_packet_index * kBitsPerPacket) + packet_frame_offset;
    }
    next_packet_index++;
  }

  return kBitsPerPacketHeader;
}
'''

CPP_OFFSET_NUEVO = '''uint32_t XmaContext::GetNextPacketReadOffset(uint8_t* buffer, uint32_t next_packet_index,
                                             uint32_t current_input_packet_count) {
  while (next_packet_index < current_input_packet_count) {
    uint8_t* next_packet = buffer + (next_packet_index * kBytesPerPacket);
    const uint32_t packet_frame_offset = xma::GetPacketFrameOffset(next_packet);

    if (packet_frame_offset <= kMaxFrameSizeinBits) {
      return (next_packet_index * kBitsPerPacket) + packet_frame_offset;
    }
    // PARCHE LOCAL - paquetes XMA: seguir la cadena de saltos, no ir de uno en
    // uno; 0xFF significa que no hay siguiente.
    const uint8_t salto = xma::GetPacketSkipCount(next_packet);
    if (salto == 0xFF) {
      break;
    }
    next_packet_index += salto + 1;
  }

  return kBitsPerPacketHeader;
}

// PARCHE LOCAL - paquetes XMA (tools/parche_xma_paquetes.py): igual, pero
// sabiendo cruzar al otro buffer de entrada. Portado de Xenia Canary.
uint32_t XmaContext::GetNextPacketReadOffset(XMA_CONTEXT_DATA* data, uint32_t next_packet_index,
                                             uint32_t current_input_packet_count) {
  const kPacketHandle paquete =
      GetPacketHandle(data, data->current_buffer, next_packet_index, current_input_packet_count);
  if (!paquete.is_valid_) {
    return kBitsPerPacketHeader;
  }

  const uint32_t direccion = data->GetInputBufferAddress(paquete.buffer_index_);
  return GetNextPacketReadOffset(memory()->TranslatePhysical(direccion), paquete.packet_index_,
                                 data->GetInputBufferPacketCount(paquete.buffer_index_));
}
'''

CPP_SALTO_ANCLA = '''  // Full packet skip (0xFF) -- no new frames begin in this packet.
  if (skip_count == 0xFF) {
    uint32_t next_input_offset =
        GetNextPacketReadOffset(current_input_buffer, packet_index + 1, current_input_packet_count);
    if (next_input_offset == kBitsPerPacketHeader) {
      SwapInputBuffer(data);
    }
    data->input_buffer_read_offset = next_input_offset;
    return;
  }
'''

CPP_SALTO_NUEVO = '''  // Full packet skip (0xFF) -- no new frames begin in this packet.
  if (skip_count == 0xFF) {
    // PARCHE LOCAL - paquetes XMA: buscar tambien en el otro buffer, y cambiar
    // de buffer si el indice se sale del actual.
    const uint32_t siguiente = packet_index + 1;
    uint32_t next_input_offset =
        GetNextPacketReadOffset(data, siguiente, current_input_packet_count);
    if (siguiente >= current_input_packet_count || next_input_offset == kBitsPerPacketHeader) {
      SwapInputBuffer(data);
    }
    data->input_buffer_read_offset = next_input_offset;
    return;
  }
'''

CPP_COLA_ANCLA = '''  uint32_t next_input_offset =
      GetNextPacketReadOffset(current_input_buffer, next_packet_index, current_input_packet_count);

  if (next_input_offset == kBitsPerPacketHeader) {
    SwapInputBuffer(data);
    if (data->IsAnyInputBufferValid()) {
'''

CPP_COLA_NUEVO = '''  // PARCHE LOCAL - paquetes XMA: la version que cruza de buffer, y cambio de
  // buffer tambien cuando el indice se sale del actual.
  uint32_t next_input_offset =
      GetNextPacketReadOffset(data, next_packet_index, current_input_packet_count);

  if (next_packet_index >= current_input_packet_count ||
      next_input_offset == kBitsPerPacketHeader) {
    SwapInputBuffer(data);
  }

  if (next_input_offset == kBitsPerPacketHeader) {
    if (data->IsAnyInputBufferValid()) {
'''

BLOQUES = {
    FICHERO_H: [(H_STRUCT_ANCLA, H_STRUCT_NUEVO), (H_DECL_ANCLA, H_DECL_NUEVO)],
    FICHERO_CPP: [(CPP_GETNEXT_ANCLA, CPP_GETNEXT_NUEVO), (CPP_OFFSET_ANCLA, CPP_OFFSET_NUEVO),
                  (CPP_SALTO_ANCLA, CPP_SALTO_NUEVO), (CPP_COLA_ANCLA, CPP_COLA_NUEVO)],
}


def localizar_sdk():
    raiz = pathlib.Path(__file__).resolve().parent.parent
    # NFSMW_SDK apunta a otro arbol del SDK (el de Android, por ejemplo). Si
    # esta puesta se usa SOLO esa ruta: caer en silencio en el SDK de Windows
    # parchearia el arbol equivocado.
    otro = os.environ.get("NFSMW_SDK")
    candidatos = [pathlib.Path(otro)] if otro else [raiz.parent / "rexglue-sdk", raiz / "sdk"]
    for cand in candidatos:
        if (cand / FICHERO_CPP).exists():
            return cand
    sys.exit(f"[ERROR] No encuentro {FICHERO_CPP} del SDK.\n"
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
    total = sum(len(v) for v in BLOQUES.values())
    puestos = 0
    for rel, bloques in BLOQUES.items():
        txt, _ = leer(sdk / rel)
        puestos += sum(1 for _, nuevo in bloques if nuevo in txt)

    if args.estado:
        estado = ("aplicado" if puestos == total else "sin aplicar" if puestos == 0
                  else f"A MEDIAS ({puestos}/{total})")
        print(f"  xma_paquetes               {estado}")
        return 0

    if args.revertir:
        if puestos == 0:
            print("[ok] xma_paquetes: no habia nada puesto")
            return 0
        for rel, bloques in BLOQUES.items():
            txt, eol = leer(sdk / rel)
            for ancla, nuevo in bloques:
                txt = txt.replace(nuevo, ancla)
            escribir(sdk / rel, txt, eol)
        print(f"[ok] Quitados {puestos} bloques")
        return 0

    if puestos == total:
        print("[ok] xma_paquetes: ya estaba")
        return 0
    if puestos:
        sys.exit(f"[ERROR] xma_paquetes esta a medias ({puestos}/{total}). Revierte primero.")
    for rel, bloques in BLOQUES.items():
        txt, _ = leer(sdk / rel)
        for ancla, _nuevo in bloques:
            n = txt.count(ancla)
            if n != 1:
                sys.exit(f"[ERROR] Un anclaje aparece {n} veces en {rel}, esperaba 1:\n"
                         f"        {ancla.splitlines()[0].strip()}\n"
                         "        El SDK habra cambiado. No he tocado nada.")
    for rel, bloques in BLOQUES.items():
        txt, eol = leer(sdk / rel)
        for ancla, nuevo in bloques:
            txt = txt.replace(ancla, nuevo, 1)
        escribir(sdk / rel, txt, eol)
    print("[ok] Aplicado: los paquetes XMA que cruzan de buffer se resuelven bien")
    return 0


if __name__ == "__main__":
    sys.exit(main())
