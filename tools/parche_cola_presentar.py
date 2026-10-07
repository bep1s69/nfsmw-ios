#!/usr/bin/env python3
"""
Presenta en pantalla desde una cola de Vulkan propia, no la del emulador.

    python tools/parche_cola_presentar.py            aplicar
    python tools/parche_cola_presentar.py --estado
    python tools/parche_cola_presentar.py --revertir

Toca dos ficheros del SDK:
    src/ui/vulkan/vulkan_device.cpp      crear 2 colas si la familia las tiene
    src/ui/vulkan/vulkan_presenter.cpp   vkQueuePresentKHR en la segunda

No guarda .original: aplica y deshace por sustitucion de texto exacta.


EL FALLO
========

El SDK crea UNA cola de Vulkan y la comparte todo el mundo, protegida por un
mutex: el procesador de comandos (CP) para enviar el trabajo de la GPU, y el
presentador (hilo de interfaz) para pintar y para vkQueuePresentKHR.

En Android, vkQueuePresentKHR acaba en BufferQueueProducer::queueBuffer, que
ESPERA al fence del fotograma presentado antes ("throttling" del productor).
Ese fotograma esta en la cola detras del trabajo del CP, asi que la espera dura
lo que tarde la GPU en acabar el trabajo del juego. Y todo ese rato el
presentador tiene el mutex de la cola:

    presentador: espera a la GPU con la cola cogida
    GPU: se queda sin trabajo, porque...
    CP: no puede enviar el siguiente, esta esperando la cola

Medido en el menu 3D con el driver de Qualcomm (perfil fuera de CPU ponderado
por tiempo): el CP pasaba el 63 % del tiempo en EndSubmission esperando la
cola y otro 18 % en IssueSwap, lo mismo. El hilo de interfaz, el 96 % dentro
de vkQueuePresentKHR -> queueBuffer -> Fence::waitForever. Y pinta al ritmo de
la pantalla, varias veces por fotograma del juego.


EL ARREGLO
==========

Si la familia de colas que presenta admite dos o mas (queueCount), se crean
dos, y vkQueuePresentKHR va a la segunda. El pintado se sigue enviando por la
primera (es corto); solo la espera larga del presente se va a su cola.

Vulkan permite esperar en una cola un semaforo senalado en otra de la misma
familia, que es lo que hace el presente con el semaforo del pintado. Si la
familia solo tiene una cola, todo queda como estaba.
"""

import argparse
import os
import pathlib
import sys


DISPOSITIVO = "src/ui/vulkan/vulkan_device.cpp"
PRESENTADOR = "src/ui/vulkan/vulkan_presenter.cpp"

BLOQUES = [
    (DISPOSITIVO,
     '''      if (queue_family.may_support_presentation) {
        queue_family.queues.resize(std::max(size_t(1), queue_family.queues.size()));
        has_presentation_queue_family = true;
      }
''',
     '''      if (queue_family.may_support_presentation) {
        // PARCHE LOCAL - cola de presentar: una segunda cola, si la hay, para
        // vkQueuePresentKHR (ver tools/parche_cola_presentar.py).
        const size_t colas_presentar = queue_family_properties.queueCount >= 2 ? 2 : 1;
        queue_family.queues.resize(std::max(colas_presentar, queue_family.queues.size()));
        has_presentation_queue_family = true;
      }
'''),
    (PRESENTADOR,
     '''    const VulkanDevice::Queue::Acquisition queue_acquisition =
        vulkan_device_->AcquireQueue(paint_context_.present_queue_family, 0);
    present_result = dfn.vkQueuePresentKHR(queue_acquisition.queue(), &present_info);
''',
     '''    // PARCHE LOCAL - cola de presentar: en la segunda cola de la familia si
    // existe. vkQueuePresentKHR puede quedarse esperando al fence del
    // fotograma anterior (queueBuffer en Android), y en la cola 0 eso
    // bloqueaba al procesador de comandos, que envia por ella.
    const uint32_t cola_presentar =
        vulkan_device_->queue_families()[paint_context_.present_queue_family].queues.size() > 1
            ? 1
            : 0;
    static bool cola_presentar_dicha = false;
    if (!cola_presentar_dicha) {
      cola_presentar_dicha = true;
      REXLOG_INFO("VulkanPresenter: presentando en la cola {} de la familia {}", cola_presentar,
                  paint_context_.present_queue_family);
    }
    const VulkanDevice::Queue::Acquisition queue_acquisition =
        vulkan_device_->AcquireQueue(paint_context_.present_queue_family, cola_presentar);
    present_result = dfn.vkQueuePresentKHR(queue_acquisition.queue(), &present_info);
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
        if (cand / DISPOSITIVO).exists() and (cand / PRESENTADOR).exists():
            return cand
    sys.exit(f"[ERROR] No encuentro {DISPOSITIVO} y {PRESENTADOR} del SDK.\n"
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
    textos = {f: leer(sdk / f) for f in (DISPOSITIVO, PRESENTADOR)}
    puestos = sum(1 for f, _, nuevo in BLOQUES if nuevo in textos[f][0])

    if args.estado:
        estado = ("aplicado" if puestos == len(BLOQUES)
                  else "sin aplicar" if puestos == 0
                  else f"a medias ({puestos}/{len(BLOQUES)})")
        print(f"  cola de presentar          {estado}")
        return 0

    if args.revertir:
        for f, ancla, nuevo in BLOQUES:
            txt, eol = textos[f]
            textos[f] = (txt.replace(nuevo, ancla), eol)
        for f, (txt, eol) in textos.items():
            escribir(sdk / f, txt, eol)
        print(f"[ok] Quitados {puestos} bloques")
        return 0

    for f, ancla, nuevo in BLOQUES:
        txt = textos[f][0]
        if nuevo not in txt and txt.count(ancla) != 1:
            sys.exit(f"[ERROR] Un anclaje no aparece exactamente una vez en {f}.\n"
                     "        El SDK habra cambiado. No he tocado nada.")
    for f, ancla, nuevo in BLOQUES:
        txt, eol = textos[f]
        if nuevo not in txt:
            textos[f] = (txt.replace(ancla, nuevo), eol)
    for f, (txt, eol) in textos.items():
        escribir(sdk / f, txt, eol)
    print("[ok] Aplicado: vkQueuePresentKHR en una cola propia si la familia tiene dos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
