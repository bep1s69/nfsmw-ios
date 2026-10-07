#!/usr/bin/env python3
"""
Anade el ajuste "una pasada": pintar la escena una vez en vez de tres.

    python tools/parche_una_pasada.py            aplicar
    python tools/parche_una_pasada.py --estado
    python tools/parche_una_pasada.py --revertir

Toca dos ficheros del SDK:
    src/graphics/command_processor.cpp   el desplazamiento, el recorte y los dibujos
    src/graphics/util/draw.cpp           a donde escribe el resolve
No guarda .original: aplica y deshace por sustitucion de texto exacta.

Es la primera pieza de docs/pipeline-nativo.md fase 2 (dejar de pintar la
escena tres veces), que es la que mas CPU ahorra.


POR QUE
=======

Medido con tools/diagnostico/censo_pipeline.py en una carrera de verdad: de los
4.570 dibujos de un fotograma, 2.748 son el pase de la escena, y ese pase son
TRES BLOQUES IDENTICOS de 916 dibujos. 1.832 dibujos -el 40 % del fotograma-
son repeticiones puras. A los ~7,4 us que cuesta cada dibujo, unos 13,6 ms de
CPU por fotograma, sobre los 32,5 que tarda ahora.

Vienen de la EDRAM: 1280x720 con MSAA 4x no cabe en los 10 MB de la Xbox 360,
asi que el juego parte la pantalla en tres franjas y manda la MISMA lista de
dibujos una vez por franja.


COMO LO HACE EL JUEGO
=====================

Graba la lista en buffers indirectos y los reenvia. Medido, el ciclo es:

    09F260C0 (1654 bytes)     <- monta la franja: mueve la ventana y resuelve
    nueve buffers de dibujos  <- franja 1
    09F260C0                  <- monta la franja 2
    los MISMOS nueve buffers  <- franja 2
    09F260C0                  <- monta la franja 3
    los MISMOS nueve buffers  <- franja 3

Entre una vuelta y otra cambian dos registros y nada mas:

    vuelta 1   PA_SC_WINDOW_OFFSET = 0          recorte filas 0-256
    vuelta 2   PA_SC_WINDOW_OFFSET = y -256     recorte filas 256-512
    vuelta 3   PA_SC_WINDOW_OFFSET = y -512     recorte filas 512-720

(el offset va como pareja de enteros de 15 bits con signo: 0x7F00 = -256.)

O sea: la misma geometria, subida 0, 256 y 512 filas, para que el tercio que
toca caiga siempre en las filas 0-255 de la EDRAM, que es lo unico que cabe.
Cada franja se resuelve con ESE desplazamiento puesto: sus vertices dicen
filas 256-512 y el desplazamiento las lleva a las 0-256 de la EDRAM.


COMO SE LO SALTA ESTE PARCHE
============================

1. La y de PA_SC_WINDOW_OFFSET pasa a valer cero, y lo que pidio el juego se
   guarda aparte (nfsmw_una_pasada_ventana). Los dibujos caen en su sitio real:
   la escena entera ocupa las filas 0-720 de una sola superficie en la EDRAM.

   SOLO la y. La x se queda, porque el juego la usa para otra cosa: resuelve la
   mitad derecha de la imagen (x 640-1280) desde una superficie de 640 de ancho
   con x = -640. La version que ponia el registro entero a cero mandaba ese
   resolve fuera de la superficie; el SDK lo rechazaba 5.124 veces por partida
   ("Resolve region 640 <= x < 1280 is outside the surface pitch 640") y la
   mitad derecha salia en negro con manchas blancas. Esa era la corrupcion.

2. El recorte se decide AL DIBUJAR, no al escribir el registro: el juego a
   veces escribe el recorte antes que la superficie nueva, y decidirlo al
   escribir lo apuntaba a la superficie anterior. Al dibujar, la superficie es
   la de verdad. Se guarda el recorte tal cual lo pide el juego y, en cada
   dibujo:
     - se aprende el borde de abajo menor y mayor de esa superficie;
     - si en el fotograma anterior tuvo bordes distintos (se trocea), se abre
       el recorte a la union: de arriba a abajo del todo;
     - si no, se deja el que pidio el juego.

3. En las vueltas 2 y 3 se tiran los DIBUJOS, y solo esos, y solo de una
   superficie a la que ya se le abrio el recorte: si no, se perderia su tira.
   No se tiran:
     - los resolves, que tambien van como paquete de dibujo (RB_MODECONTROL en
       modo copia): sin ellos las franjas 2 y 3 no llegaban nunca a su
       textura;
     - nada que no sea un dibujo: fences y eventos se siguen ejecutando.
       Saltarse el buffer indirecto ENTERO, que es lo que hacia la primera
       version, colgaba el juego en el video de arranque.

4. El resolve (util/draw.cpp) lee de la EDRAM las filas de verdad (256-512 para
   la franja 2, porque el desplazamiento ya es cero), pero escribe en la
   textura DONDE EL JUEGO LO ESPERA: con su desplazamiento aplicado, o sea en
   las filas 0-256 de la direccion que dio para esa franja. El resolve saca la
   direccion de destino de las mismas coordenadas que la de origen; sin esta
   correccion, la franja 2 se escribia 256 filas mas abajo y la 3, 512, fuera
   de su textura y machacando memoria. Eso es lo que corrompia la imagen (la
   mitad derecha en negro con una mancha blanca) en la version anterior.

5. La predicacion (SET_BIN_MASK) deja pasar en cada franja solo los dibujos
   que la tocan. Como las vueltas 2 y 3 se tiran, un dibujo que solo toca las
   franjas de abajo no se pintaria nunca y dejaria basura en esa zona. Asi que
   en la primera vuelta de una superficie abierta vale cualquier franja
   (bin_mask distinto de cero). Los resolves no: van atados a la suya.


CUIDADO
=======

No vale con MSAA. Con la EDRAM todavia en medio, una pasada de 1280x720 cabe
sin MSAA -3,5 MB de color mas 3,5 de profundidad, siete de los diez- pero con
MSAA 4x no cabe, que es justo por lo que el juego trocea. La app lo apaga sola
si el suavizado es MSAA (Ajustes.unaPasada). Con FXAA si vale: va despues.

El primer fotograma de cada escena se pinta en tres franjas, como siempre:
hasta que no se ha visto que una superficie se trocea no se le abre el recorte
ni se le quita nada.
"""

import argparse
import os
import pathlib
import sys


CP = "src/graphics/command_processor.cpp"
DRAW = "src/graphics/util/draw.cpp"

# (fichero, ancla, lo que la sustituye)
BLOQUES = [
    (
        CP,
        '''#include <string_view>
''',
        '''#include <map>  // PARCHE LOCAL - una pasada (tools/parche_una_pasada.py)
#include <string_view>
#include <utility>  // PARCHE LOCAL - una pasada
''',
    ),
    (
        CP,
        # DENTRO del namespace, no delante: parche_msaa deja su cvar justo antes
        # de esta linea, y meterse entre los dos le rompia el bloque (su
        # --estado decia "a medias" y su --revertir ya no lo encontraba).
        '''namespace rex::graphics {
''',
        '''namespace rex::graphics {

// PARCHE LOCAL - una pasada (tools/parche_una_pasada.py).
REXCVAR_DEFINE_BOOL(nfsmw_una_pasada, false, "GPU",
                    "Pintar la escena de una vez en vez de en tres franjas: quita el 40 % de los "
                    "dibujos del fotograma. No vale con MSAA, que no cabe en la EDRAM");

// PARCHE LOCAL - una pasada: la y del PA_SC_WINDOW_OFFSET que pidio el juego
// (solo esos bits; la x se queda en el registro). El registro lleva la y a
// cero; esto dice si la vuelta es una repeticion de franja, y util/draw.cpp lo
// usa para que el resolve escriba donde el juego espera.
uint32_t nfsmw_una_pasada_ventana = 0;

namespace {

// PARCHE LOCAL - una pasada: lo que hay que recordar de un fotograma.
struct NfsmwUnaPasada {
  // Bordes de abajo del recorte vistos AL DIBUJAR por superficie, el menor y
  // el mayor. Si no coinciden, esa superficie se trocea, y el mayor es la
  // union. Los del fotograma anterior son los que se aplican, porque los de
  // este todavia se estan aprendiendo.
  std::map<uint32_t, std::pair<uint32_t, uint32_t>> altos_anterior;
  std::map<uint32_t, std::pair<uint32_t, uint32_t>> altos_actual;
  // El recorte tal cual lo escribio el juego: el registro puede llevar el
  // abierto de un dibujo anterior.
  uint32_t recorte_tl = 0;
  uint32_t recorte_br = 0;
  // Para poder comprobar en el log que esto esta actuando de verdad, y cuanto.
  uint32_t saltados = 0;
  uint32_t fotogramas = 0;
};
NfsmwUnaPasada nfsmw_una_pasada_estado;

}  // namespace
''',
    ),
    (
        CP,
        '''void CommandProcessor::WriteRegister(uint32_t index, uint32_t value) {
  RegisterFile& regs = *register_file_;
''',
        '''void CommandProcessor::WriteRegister(uint32_t index, uint32_t value) {
  RegisterFile& regs = *register_file_;
  // PARCHE LOCAL - una pasada (tools/parche_una_pasada.py): el desplazamiento
  // de franja a cero, y el recorte se apunta tal cual; que hacer con el se
  // decide al dibujar, cuando ya se sabe de que superficie es.
  if ((index == XE_GPU_REG_PA_SC_WINDOW_OFFSET ||
       index == XE_GPU_REG_PA_SC_WINDOW_SCISSOR_BR ||
       index == XE_GPU_REG_PA_SC_WINDOW_SCISSOR_TL) &&
      REXCVAR_GET(nfsmw_una_pasada)) {
    if (index == XE_GPU_REG_PA_SC_WINDOW_OFFSET) {
      // SOLO la y (bits 16-30), que es lo que mueven las franjas. La x se
      // queda: el juego la usa aparte para resolver la mitad derecha de la
      // imagen (x 640-1280) desde una superficie de 640 de ancho, con x -640.
      // Poniendola a cero ese resolve caia fuera de la superficie, el SDK lo
      // rechazaba ("outside the surface pitch 640") y la mitad derecha salia
      // en negro con manchas blancas.
      nfsmw_una_pasada_ventana = value & (UINT32_C(0x7FFF) << 16);
      value &= ~(UINT32_C(0x7FFF) << 16);
    } else if (index == XE_GPU_REG_PA_SC_WINDOW_SCISSOR_BR) {
      nfsmw_una_pasada_estado.recorte_br = value;
    } else {
      nfsmw_una_pasada_estado.recorte_tl = value;
    }
  }
''',
    ),
    (
        CP,
        '''  if (packet & 1) {
    bool any_pass = (bin_select_ & bin_mask_) != 0;
    if (!any_pass || opcode == PM4_XE_SWAP) {
      reader->AdvanceRead(count * sizeof(uint32_t));
      return true;
    }
  }
''',
        '''  // PARCHE LOCAL - una pasada (tools/parche_una_pasada.py): el recorte, y que
  // dibujos sobran, se deciden aqui, con la superficie de verdad, y ANTES de la
  // predicacion, que tambien depende de ello (abajo).
  bool una_pasada_abierta = false;
  if ((opcode == PM4_DRAW_INDX || opcode == PM4_DRAW_INDX_2) &&
      REXCVAR_GET(nfsmw_una_pasada)) {
    NfsmwUnaPasada& una_pasada = nfsmw_una_pasada_estado;
    RegisterFile& regs = *register_file_;
    const uint32_t superficie = regs.values[XE_GPU_REG_RB_SURFACE_INFO];
    const uint32_t borde = (una_pasada.recorte_br >> 16) & UINT32_C(0x3FFF);
    const auto visto = una_pasada.altos_actual.find(superficie);
    if (visto == una_pasada.altos_actual.end()) {
      una_pasada.altos_actual[superficie] = std::make_pair(borde, borde);
    } else {
      visto->second.first = std::min(visto->second.first, borde);
      visto->second.second = std::max(visto->second.second, borde);
    }
    const auto aprendido = una_pasada.altos_anterior.find(superficie);
    const bool troceada = aprendido != una_pasada.altos_anterior.end() &&
                          aprendido->second.second > aprendido->second.first;
    uint32_t tl = una_pasada.recorte_tl;
    uint32_t br = una_pasada.recorte_br;
    if (troceada) {
      // De arriba del todo (el bit 31 de TL, window_offset_disable, se queda)
      // hasta el borde mayor de las tres franjas.
      tl &= ~(UINT32_C(0x3FFF) << 16);
      br = (br & ~(UINT32_C(0x3FFF) << 16)) | (aprendido->second.second << 16);
    }
    regs.values[XE_GPU_REG_PA_SC_WINDOW_SCISSOR_TL] = tl;
    regs.values[XE_GPU_REG_PA_SC_WINDOW_SCISSOR_BR] = br;
    // Los resolves se quedan fuera de todo lo que sigue: cada uno va atado a
    // su franja, y es el que la lleva a su textura.
    const bool es_resolve =
        regs.Get<reg::RB_MODECONTROL>().edram_mode == xenos::EdramMode::kCopy;
    una_pasada_abierta = troceada && !es_resolve;
    // Vueltas 2 y 3 de una superficie ya abierta: la primera vuelta ya pinto
    // toda la pantalla.
    if (una_pasada_abierta && nfsmw_una_pasada_ventana != 0) {
      ++una_pasada.saltados;
      reader->AdvanceRead(count * sizeof(uint32_t));
      return true;
    }
  }

  if (packet & 1) {
    bool any_pass = (bin_select_ & bin_mask_) != 0;
    // PARCHE LOCAL - una pasada: la predicacion deja pasar en cada franja solo
    // los dibujos que la tocan (SET_BIN_MASK). La primera vuelta de una
    // superficie abierta pinta TODA la pantalla, y las vueltas 2 y 3 se tiran:
    // un dibujo que solo toca las franjas de abajo (la carretera cerca de la
    // camara, la parte de abajo de un objeto) no se pintaria nunca, y ahi
    // quedaria basura. Asi que en la primera vuelta vale cualquier franja.
    if (una_pasada_abierta && nfsmw_una_pasada_ventana == 0) {
      any_pass = bin_mask_ != 0;
    }
    if (!any_pass || opcode == PM4_XE_SWAP) {
      reader->AdvanceRead(count * sizeof(uint32_t));
      return true;
    }
  }
''',
    ),
    (
        CP,
        # Delante de ++counter_ y no detras de IssueSwap: parche_vblank ya pone
        # ahi su NfsmwAvisarSwap(), y meterse en medio le rompia el bloque.
        '''  ++counter_;
  return true;
''',
        '''  // PARCHE LOCAL - una pasada: el fotograma se acaba aqui. Lo aprendido pasa a
  // ser lo que se aplica en el siguiente. SOLO con el ajuste puesto: apagado no
  // hay nada que aprender, y antes escribia una linea "0 dibujos tirados" en el
  // log cada 60 fotogramas para siempre.
  if (REXCVAR_GET(nfsmw_una_pasada)) {
    NfsmwUnaPasada& una_pasada = nfsmw_una_pasada_estado;
    // swap y no copia: sin reservar un nodo nuevo por superficie cada fotograma.
    std::swap(una_pasada.altos_anterior, una_pasada.altos_actual);
    una_pasada.altos_actual.clear();
    nfsmw_una_pasada_ventana = 0;
    // Sin esto no hay forma de saber desde el log si el ajuste esta actuando.
    if (++una_pasada.fotogramas >= 60) {
      REXGPU_INFO("[una pasada] {} dibujos de franja repetida tirados en {} fotogramas",
                  una_pasada.saltados, una_pasada.fotogramas);
      una_pasada.saltados = 0;
      una_pasada.fotogramas = 0;
    }
  }

  ++counter_;
  return true;
''',
    ),
    (
        DRAW,
        '''namespace rex::graphics::draw_util {
''',
        '''// PARCHE LOCAL - una pasada (tools/parche_una_pasada.py): el desplazamiento de
// ventana que pidio el juego. Cero si el ajuste esta apagado.
namespace rex::graphics {
extern uint32_t nfsmw_una_pasada_ventana;
}

namespace rex::graphics::draw_util {
''',
    ),
    (
        DRAW,
        '''  // Calculate the destination memory extent.
''',
        '''  // PARCHE LOCAL - una pasada (tools/parche_una_pasada.py): el origen ya es la
  // fila de verdad en la EDRAM (256-512 para la franja 2), porque el registro
  // de desplazamiento esta a cero. Pero la textura de destino el juego la
  // espera como si lo estuviera: la franja 2 en las filas 0-256 de la
  // direccion que dio para ella. Asi que el destino se calcula con su
  // desplazamiento, y el origen se devuelve mas abajo.
  const int32_t una_pasada_x0 = x0;
  const int32_t una_pasada_y0 = y0;
  const int32_t una_pasada_x1 = x1;
  const int32_t una_pasada_y1 = y1;
  if (nfsmw_una_pasada_ventana != 0 &&
      regs.Get<reg::PA_SU_SC_MODE_CNTL>().vtx_window_offset_enable) {
    reg::PA_SC_WINDOW_OFFSET pedido;
    pedido.value = nfsmw_una_pasada_ventana;
    x0 += pedido.window_x_offset;
    y0 += pedido.window_y_offset;
    x1 += pedido.window_x_offset;
    y1 += pedido.window_y_offset;
  }

  // Calculate the destination memory extent.
''',
    ),
    (
        DRAW,
        '''  // Offset relative to the beginning of the tile to put it in fewer bits.
''',
        '''  // PARCHE LOCAL - una pasada: de aqui en adelante, el origen en la EDRAM.
  x0 = una_pasada_x0;
  y0 = una_pasada_y0;
  x1 = una_pasada_x1;
  y1 = una_pasada_y1;

  // Offset relative to the beginning of the tile to put it in fewer bits.
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
        if (cand / CP).exists() and (cand / DRAW).exists():
            return cand
    sys.exit(f"[ERROR] No encuentro {CP} y {DRAW} del SDK.\n"
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
    textos = {f: leer(sdk / f) for f in (CP, DRAW)}
    puestos = sum(1 for f, _, nuevo in BLOQUES if nuevo in textos[f][0])

    if args.estado:
        estado = ("aplicado" if puestos == len(BLOQUES) else "sin aplicar" if puestos == 0
                  else f"A MEDIAS ({puestos}/{len(BLOQUES)})")
        print(f"  una_pasada                 {estado}")
        return 0

    if args.revertir:
        if puestos == 0:
            print("[ok] una_pasada: no habia nada puesto")
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
        print("[ok] una_pasada: ya estaba")
        return 0
    if puestos:
        sys.exit(f"[ERROR] una_pasada esta a medias ({puestos}/{len(BLOQUES)}). "
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
    print("[ok] Aplicado: ajuste nfsmw_una_pasada (no vale con MSAA)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
