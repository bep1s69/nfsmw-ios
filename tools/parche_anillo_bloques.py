#!/usr/bin/env python3
"""
Publicar el puntero de lectura del anillo mientras se vacia, no al terminar.

    python tools/parche_anillo_bloques.py            aplicar
    python tools/parche_anillo_bloques.py --estado
    python tools/parche_anillo_bloques.py --revertir

Toca un fichero del SDK:  src/graphics/command_processor.cpp
Va DESPUES de tools/parche_espera_anillo.py, sobre el mismo fichero.
No guarda .original: aplica y deshace por sustitucion de texto exacta.


DE DONDE SALE
=============

Portado de has207/xenia-edge (BSD-3, como el resto del SDK), commit 29fcaeac:
"[GPU/PM4] Publish ring read pointer every RB_BLKSZ dwords not per burst".


EL FALLO
========

El juego mira la copia en memoria del puntero de lectura del anillo para saber
cuanto sitio le queda para escribir mas comandos. En la consola ese puntero
avanza de forma continua segun el hardware consume.

Aqui se escribia UNA vez, al terminar de ejecutar toda la rafaga
(ExecutePrimaryBuffer). O sea que el juego se quedaba esperando sitio que ya
estaba libre desde hacia rato. Y peor: si a mitad de rafaga habia un
WAIT_REG_MEM esperando algo que tenia que hacer el juego, se bloqueaban el uno
al otro, porque el juego esperaba sitio en el anillo y el procesador de
comandos esperaba al juego.

En este port eso se notaba el doble: el D3D del juego GIRA releyendo ese
puntero (por eso existe el gancho de android/.../ganchos.cpp), y el puntero
solo se publicaba dos veces por fotograma.


EL ARREGLO
==========

Publicarlo cada RB_BLKSZ dwords consumidos, que es lo que el propio juego pidio
al armar la escritura (CP_RB_CNTL). Y de paso avisar por el futex del gancho en
cada publicacion, no solo al final de la rafaga.

Tambien se corrige la conversion de RB_BLKSZ: el SDK lo pasaba a "quadwords /
4", cuando read_ptr_index_ y la escritura van en DWORDS; son quadwords por dos.
"""

import argparse
import os
import pathlib
import sys


FICHERO = "src/graphics/command_processor.cpp"

BLOQUES = [
    (
        '''  // CP_RB_CNTL Ring Buffer Control 0x704
  // block_size = RB_BLKSZ, log2 of number of quadwords read between updates of
  //              the read pointer.
  read_ptr_update_freq_ = uint32_t(1) << block_size_log2 >> 2;
''',
        '''  // CP_RB_CNTL Ring Buffer Control 0x704
  // block_size = RB_BLKSZ, log2 of number of quadwords read between updates of
  //              the read pointer.
  // PARCHE LOCAL - anillo por bloques (tools/parche_anillo_bloques.py): en
  // DWORDS, que es la unidad de read_ptr_index_ y de la escritura; un quadword
  // son dos. Suele venir 6, o sea 128 dwords.
  read_ptr_update_freq_ = (uint32_t(1) << std::min(block_size_log2, uint32_t(19))) * 2;
''',
    ),
    (
        '''  reader.set_read_offset(read_index * sizeof(uint32_t));
  reader.set_write_offset(write_index * sizeof(uint32_t));
  do {
    if (!ExecutePacket(&reader)) {
      // This probably should be fatal - but we're going to continue anyways.
      REXGPU_ERROR("**** PRIMARY RINGBUFFER: Failed to execute packet.");
      assert_always();
      break;
    }
  } while (reader.read_count());
''',
        '''  reader.set_read_offset(read_index * sizeof(uint32_t));
  reader.set_write_offset(write_index * sizeof(uint32_t));
  // PARCHE LOCAL - anillo por bloques (tools/parche_anillo_bloques.py): el
  // juego mira este puntero para saber cuanto sitio le queda, asi que se
  // publica segun se vacia y no solo al final de la rafaga.
  const size_t nfsmw_paso = size_t(read_ptr_update_freq_) * sizeof(uint32_t);
  size_t nfsmw_restante = reader.read_count();
  do {
    if (!ExecutePacket(&reader)) {
      // This probably should be fatal - but we're going to continue anyways.
      REXGPU_ERROR("**** PRIMARY RINGBUFFER: Failed to execute packet.");
      assert_always();
      break;
    }
    const size_t nfsmw_queda = reader.read_count();
    // Solo crece si un paquete mal formado se paso del final de la rafaga, y
    // entonces no hay nada honesto que publicar.
    if (nfsmw_paso && nfsmw_queda <= nfsmw_restante && nfsmw_restante - nfsmw_queda >= nfsmw_paso) {
      // Se relee: el juego puede mover o quitar la escritura desde su hilo
      // mientras esto vacia.
      const uint32_t nfsmw_destino = read_ptr_writeback_ptr_;
      if (nfsmw_destino) {
        // Publicar el puntero devuelve ese sitio del anillo, asi que tiene que
        // caer despues de haberlo leido.
        std::atomic_thread_fence(std::memory_order_release);
        memory::store_and_swap<uint32_t>(memory_->TranslatePhysical(nfsmw_destino),
                                         uint32_t(reader.read_offset() / sizeof(uint32_t)));
        // El gancho de ganchos.cpp duerme en este contador.
        nfsmw_cp_rptr_seq.fetch_add(1, std::memory_order_release);
#if defined(__linux__)
        syscall(SYS_futex, &nfsmw_cp_rptr_seq, FUTEX_WAKE_PRIVATE, INT_MAX, nullptr, nullptr, 0);
#endif
      }
      nfsmw_restante = nfsmw_queda;
    }
  } while (reader.read_count());
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
        estado = ("aplicado" if puestos == len(BLOQUES) else "sin aplicar" if puestos == 0
                  else f"A MEDIAS ({puestos}/{len(BLOQUES)})")
        print(f"  anillo_bloques             {estado}")
        return 0

    if args.revertir:
        if puestos == 0:
            print("[ok] anillo_bloques: no habia nada puesto")
            return 0
        for ancla, nuevo in BLOQUES:
            txt = txt.replace(nuevo, ancla)
        escribir(f, txt, eol)
        print(f"[ok] Quitados {puestos} bloques")
        return 0

    if puestos == len(BLOQUES):
        print("[ok] anillo_bloques: ya estaba")
        return 0
    if puestos:
        sys.exit(f"[ERROR] anillo_bloques esta a medias ({puestos}/{len(BLOQUES)}). "
                 "Revierte primero con --revertir.")
    for ancla, _ in BLOQUES:
        n = txt.count(ancla)
        if n != 1:
            sys.exit(f"[ERROR] Un anclaje aparece {n} veces en {FICHERO}, esperaba 1:\n"
                     f"        {ancla.splitlines()[0].strip()}\n"
                     "        El SDK habra cambiado. No he tocado nada.")
    for ancla, nuevo in BLOQUES:
        txt = txt.replace(ancla, nuevo, 1)
    escribir(f, txt, eol)
    print("[ok] Aplicado: el puntero de lectura del anillo se publica cada bloque")
    return 0


if __name__ == "__main__":
    sys.exit(main())
