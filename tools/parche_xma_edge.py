#!/usr/bin/env python3
"""
Trae de Xenia Edge tres arreglos del descodificador XMA.

    python tools/parche_xma_edge.py            aplicar
    python tools/parche_xma_edge.py --estado
    python tools/parche_xma_edge.py --revertir

Toca dos ficheros del SDK:
    include/rex/audio/xma/context.h
    src/audio/xma_context.cpp
No guarda .original: aplica y deshace por sustitucion de texto exacta.
Va DESPUES de tools/parche_xma_paquetes.py, sobre los mismos ficheros.


DE DONDE SALE
=============

Portado de has207/xenia-edge (fork de Xenia Canary, BSD-3 como el resto del
SDK), de tres commits sobre src/xenia/apu/xma_context_new.cc:

  052365b  [APU] Drain the current frame before ending the XMA work loop
  adf56b7  [XMA] Count the frame whose header crosses the packet boundary
  5dd1cdb  [XMA] Resolve XMA loop_start to a frame boundary


1. EL FOTOGRAMA A MEDIO ENTREGAR (052365b)
==========================================

Este es el cuelgue de audio que en este juego lleva mucho tiempo dando la
lata, el que tools/parche_desatasco.py rompe desde fuera.

Work() descodifica y entrega en un bucle, y sale en cuanto los dos buffers de
entrada dejan de ser validos. Pero Consume() entrega COMO MUCHO
subframe_decode_count bloques por vuelta, asi que la vuelta que agota la
entrada casi siempre deja la cola del fotograma sin entregar.

Y no hay quien la entregue despues: Work() apaga is_enabled_ al entrar, y solo
XMAEnableContext lo vuelve a encender. El juego, que esta esperando justo esos
bloques, no da el aviso que los sacaria. Se quedan los dos mirandose.

El arreglo: no salir del bucle mientras quede fotograma por entregar.


2. LA TRAMA QUE EMPIEZA AL FINAL DEL PAQUETE (adf56b7)
======================================================

GetPacketInfo recorre las tramas de un paquete. Si una empieza en los ultimos
bits, su cabecera de 15 bits se va al paquete siguiente y no se puede leer, y
el recorrido paraba SIN CONTARLA. Con eso la anterior parecia la ultima del
paquete, y Decode se saltaba la trama entera y ademas descodificaba la
siguiente con la ventana de solape de ffmpeg pasada: dos tramas perdidas cada
vez.

El arreglo: contarla igual, con tamano 0, que es lo que la manda al camino de
"cabecera partida entre paquetes".


3. EL LOOP_START QUE NO CAE EN UNA TRAMA (5dd1cdb)
==================================================

Los juegos pueden escribir loop_start un bit antes del principio de la trama.
Con ese offset torcido GetPacketInfo no encontraba tamano, Decode lo tomaba
por una cabecera partida y resolvia un tamano de basura sacado del payload.
FFmpeg rechazaba el paquete y, sin nadie que lo vaciara, todos los envios
siguientes devolvian EAGAIN: esa voz se quedaba muda para el resto de la
partida.

El arreglo: GetPacketInfo informa ademas de la primera trama que empieza en el
offset pedido o despues, y Decode la adopta al reiniciar un bucle.
"""

import argparse
import os
import pathlib
import sys


FICHERO_H = "include/rex/audio/xma/context.h"
FICHERO_CPP = "src/audio/xma_context.cpp"

# --- 1. context.h: el offset resuelto ---------------------------------------

H_ANCLA = '''struct kPacketInfo {
  uint8_t frame_count_ = 0;
  uint8_t current_frame_ = 0;
  uint32_t current_frame_size_ = 0;
'''

H_NUEVO = '''struct kPacketInfo {
  uint8_t frame_count_ = 0;
  uint8_t current_frame_ = 0;
  uint32_t current_frame_size_ = 0;
  // PARCHE LOCAL - xma edge: la primera trama que empieza en el offset pedido
  // o despues (tools/parche_xma_edge.py).
  uint32_t current_frame_offset_ = 0;
'''

# --- 2. Work(): no dejar el fotograma a medias ------------------------------

WORK_ANCLA = '''    if (!data.IsAnyInputBufferValid() || data.error_status == 4) {
      break;
    }
'''

WORK_NUEVO = '''    // PARCHE LOCAL - xma edge: no abandonar un fotograma a medio entregar.
    // Consume() entrega como mucho subframe_decode_count bloques por vuelta,
    // asi que la vuelta que agota la entrada deja el resto sin entregar; y
    // nadie lo entregara luego, porque Work() ya apago is_enabled_ y el juego
    // esta esperando justo eso para dar el aviso que lo sacaria.
    if ((!data.IsAnyInputBufferValid() || data.error_status == 4) &&
        current_frame_remaining_subframes_ == 0) {
      break;
    }
'''

# --- 3. GetPacketInfo(): contar la trama partida y resolver el offset --------

INFO_ANCLA = '''kPacketInfo XmaContext::GetPacketInfo(uint8_t* packet, uint32_t frame_offset) {
  kPacketInfo packet_info = {};

  const uint32_t first_frame_offset = xma::GetPacketFrameOffset(packet);
  BitStream stream(packet, kBitsPerPacket);
  stream.SetOffset(first_frame_offset);

  if (frame_offset < first_frame_offset) {
    packet_info.current_frame_ = 0;
    packet_info.current_frame_size_ = first_frame_offset - frame_offset;
  }

  while (true) {
    if (stream.BitsRemaining() < kBitsPerFrameHeader) {
      break;
    }

    const uint64_t frame_size = stream.Peek(kBitsPerFrameHeader);
    if (frame_size == 0 || frame_size == xma::kMaxFrameLength) {
      break;
    }

    if (stream.offset_bits() == frame_offset) {
      packet_info.current_frame_ = packet_info.frame_count_;
      packet_info.current_frame_size_ = static_cast<uint32_t>(frame_size);
    }

    packet_info.frame_count_++;
'''

INFO_NUEVO = '''kPacketInfo XmaContext::GetPacketInfo(uint8_t* packet, uint32_t frame_offset) {
  kPacketInfo packet_info = {};
  packet_info.current_frame_offset_ = frame_offset;

  const uint32_t first_frame_offset = xma::GetPacketFrameOffset(packet);
  BitStream stream(packet, kBitsPerPacket);
  stream.SetOffset(first_frame_offset);

  // PARCHE LOCAL - xma edge: ademas de la trama que empieza justo en el offset
  // pedido, apuntar la primera que empieza en ese offset o despues, para poder
  // enderezar un loop_start torcido (tools/parche_xma_edge.py).
  bool resuelto = false;
  auto mirar_trama = [&](uint32_t offset, uint32_t size) {
    if (!resuelto && offset >= frame_offset) {
      resuelto = true;
      packet_info.current_frame_offset_ = offset;
    }
    if (offset != frame_offset) {
      return;
    }
    packet_info.current_frame_ = packet_info.frame_count_;
    packet_info.current_frame_size_ = size;
  };

  if (frame_offset < first_frame_offset) {
    packet_info.current_frame_ = 0;
    packet_info.current_frame_size_ = first_frame_offset - frame_offset;
    resuelto = true;
  }

  while (true) {
    if (stream.BitsRemaining() < kBitsPerFrameHeader) {
      // PARCHE LOCAL - xma edge: esta trama empieza aqui pero su cabecera de
      // 15 bits se va al paquete siguiente, asi que su tamano no se puede leer
      // todavia. Contarla igual: si no, la anterior pasa por ultima del paquete
      // y esta se pierde entera. Tamano 0 la manda al camino de cabecera
      // partida.
      if (stream.BitsRemaining() > 0) {
        mirar_trama(static_cast<uint32_t>(stream.offset_bits()), 0);
        packet_info.frame_count_++;
      }
      break;
    }

    const uint64_t frame_size = stream.Peek(kBitsPerFrameHeader);
    if (frame_size == 0 || frame_size == xma::kMaxFrameLength) {
      break;
    }

    mirar_trama(static_cast<uint32_t>(stream.offset_bits()),
                static_cast<uint32_t>(frame_size));

    packet_info.frame_count_++;
'''

# --- 4. Decode(): adoptar el offset resuelto al reiniciar el bucle ----------

DECODE_ANCLA = '''  kPacketInfo packet_info = GetPacketInfo(packet, relative_offset);
  const uint32_t packet_to_skip = skip_count + 1;
'''

DECODE_NUEVO = '''  kPacketInfo packet_info = GetPacketInfo(packet, relative_offset);

  // PARCHE LOCAL - xma edge: los juegos pueden escribir loop_start un bit antes
  // del principio de la trama; con ese offset torcido el tamano sale de basura
  // y ffmpeg deja la voz muda para siempre (tools/parche_xma_edge.py).
  if (loop_start_skip_pending_ && packet_info.current_frame_offset_ != relative_offset) {
    REXAPU_DEBUG(
        "XmaContext {}: loop_start {} no cae en una trama del paquete {}; se pasa a {}", id(),
        relative_offset, packet_index, packet_info.current_frame_offset_);
    relative_offset = packet_info.current_frame_offset_;
    data->input_buffer_read_offset = (packet_index * kBitsPerPacket) + relative_offset;
    packet_info = GetPacketInfo(packet, relative_offset);
  }

  const uint32_t packet_to_skip = skip_count + 1;
'''

BLOQUES = {
    FICHERO_H: [(H_ANCLA, H_NUEVO)],
    FICHERO_CPP: [(WORK_ANCLA, WORK_NUEVO), (INFO_ANCLA, INFO_NUEVO), (DECODE_ANCLA, DECODE_NUEVO)],
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
        print(f"  xma_edge                   {estado}")
        return 0

    if args.revertir:
        if puestos == 0:
            print("[ok] xma_edge: no habia nada puesto")
            return 0
        for rel, bloques in BLOQUES.items():
            txt, eol = leer(sdk / rel)
            for ancla, nuevo in bloques:
                txt = txt.replace(nuevo, ancla)
            escribir(sdk / rel, txt, eol)
        print(f"[ok] Quitados {puestos} bloques")
        return 0

    if puestos == total:
        print("[ok] xma_edge: ya estaba")
        return 0
    if puestos:
        sys.exit(f"[ERROR] xma_edge esta a medias ({puestos}/{total}). Revierte primero.")
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
    print("[ok] Aplicado: tres arreglos del XMA de Xenia Edge")
    return 0


if __name__ == "__main__":
    sys.exit(main())
