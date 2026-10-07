#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Traduce direcciones del ejecutable de referencia (PAL Espana) a las de otra
edicion del juego.

    python tools/ediciones/emparejar.py <referencia.xex> <otra.xex> <salida.tsv> [direcciones...]

Sin direcciones en la linea de comandos, las lee de la entrada estandar, una
por linea. Sin dependencias: Python 3.8+.

El metodo es el de StevensND/nfsmw-nx (tools/editions/emparejar.py y
verificar_ganchos.py, GPL-3.0), reescrito sin numpy y con los limites de las
funciones sacados de .pdata en vez del reparto del codegen:

  .text    Las instrucciones PowerPC se normalizan quitando lo que depende de
           la posicion (desplazamientos de salto, inmediatos de 16 bits de
           lis/addi/ori y de cargas y guardados). Se buscan tiras de 12
           instrucciones que salgan UNA sola vez en cada edicion (anclas), se
           dejan las que van en el mismo orden, y cada direccion se traduce con
           el desplazamiento de su ancla anterior (o de la siguiente). Cada
           traduccion se comprueba comparando 16 instrucciones normalizadas.
  .rdata   Se busca el contenido en la otra edicion; tiene que salir una vez.
  .data    Misma direccion: la seccion no se mueve entre PAL y USA. Se apunta
           si los bytes de alrededor cambian.

Normalizar quita tambien los inmediatos que son campos de una estructura
("lwz r3,0x854(r31)"), y un gancho depende de ellos. Por eso las funciones
enganchadas se comparan ademas ENTERAS y sin normalizar (comparar_funcion).
"""

import bisect
import hashlib
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import imagen  # noqa: E402

BASE = imagen.BASE
K = 12            # instrucciones por ancla
VERIFICAR = 16    # instrucciones que se comparan en cada traduccion

# Lo que se quita de cada instruccion, por codigo de operacion (6 bits altos).
_MASCARA = [0xFFFFFFFF] * 64
_MASCARA[18] = 0xFC000003                      # b, bl
_MASCARA[16] = 0xFFFF0003                      # bc
for _op in [14, 15, 24, 25] + list(range(32, 56)):
    _MASCARA[_op] = 0xFFFF0000                 # addi, addis, ori, oris, cargas y guardados


def normalizar(datos):
    """bytes de instrucciones -> bytes de instrucciones normalizadas."""
    n = len(datos) // 4
    m = _MASCARA
    return struct.pack(">%dI" % n, *[w & m[w >> 26] for w in struct.unpack(">%dI" % n, datos[:n * 4])])


def _unicas(norm):
    """{tira de K instrucciones: indice}, solo las que salen una vez."""
    vistas = {}
    ancho = K * 4
    for i in range(0, len(norm) - ancho + 4, 4):
        clave = norm[i:i + ancho]
        vistas[clave] = -1 if clave in vistas else i >> 2
    return {k: v for k, v in vistas.items() if v >= 0}


def _anclas(na, nb):
    ua, ub = _unicas(na), _unicas(nb)
    pares = sorted((i, ub[k]) for k, i in ua.items() if k in ub)
    # la subsecuencia creciente mas larga en la otra edicion: anclas en el mismo orden
    colas, idx, prev = [], [], [-1] * len(pares)
    for i, (_, b) in enumerate(pares):
        k = bisect.bisect_left(colas, b)
        if k == len(colas):
            colas.append(b)
            idx.append(i)
        else:
            colas[k] = b
            idx[k] = i
        prev[i] = idx[k - 1] if k else -1
    cadena, i = [], idx[-1] if idx else -1
    while i >= 0:
        cadena.append(pares[i])
        i = prev[i]
    return cadena[::-1]


# --- Direcciones que el codigo calcula con lis + parte baja ------------------
#
# PowerPC carga una direccion entera en dos instrucciones: "lis rX,ALTA" y otra
# con base rX que pone la parte baja (addi y las cargas y guardados de forma D;
# ori, que lleva la base en los bits 21-25; ld/std de forma DS). Es lo que usan
# datos_por_referencias.py y verificar_parejas.py de nfsmw-nx, y estas son sus
# mismas reglas.
_CARGAS = set(range(32, 56)) | {14}
# Guardados: los bits 21-25 son el registro que se guarda, no uno que se escribe.
_GUARDADOS = (36, 37, 38, 39, 44, 45, 47, 52, 53, 54, 55, 62)


def _completa(op):
    return op in _CARGAS or op == 24 or op in (58, 62)


def _base(x, op):
    return (x >> 21) & 31 if op == 24 else (x >> 16) & 31


def _parte_baja(x, op):
    if op == 24:
        return x & 0xFFFF
    v = x & (0xFFFC if op in (58, 62) else 0xFFFF)
    return v - 0x10000 if v & 0x8000 else v


def _referencias(w, desde, hasta):
    """{direccion: [(indice del lis, indice de la parte baja)]}, solo las de [desde, hasta)."""
    out = {}
    n = len(w)
    for i, a in enumerate(w):
        if a >> 26 != 15 or (a >> 16) & 31:
            continue
        rd = (a >> 21) & 31
        alta = (a & 0xFFFF) << 16
        for j in range(i + 1, min(i + 9, n)):
            x = w[j]
            op = x >> 26
            if _completa(op) and _base(x, op) == rd:
                d = (alta + _parte_baja(x, op)) & 0xFFFFFFFF
                if desde <= d < hasta:
                    out.setdefault(d, []).append((i, j))
            # la pareja acaba si la instruccion escribe rX (aproximado: destino en los bits 21-25)
            if (op in (14, 15, 24, 31) or op in range(32, 48, 2)) and (x >> 21) & 31 == rd \
                    and not (op == 24 and (x >> 16) & 31 != rd) \
                    and not (op in _CARGAS and op >= 36 and op not in (40, 41, 42, 43, 46, 48, 49, 50, 51)):
                break
    return out


def _direccion_en(w, i, j):
    """La direccion que calcula la pareja w[i] (lis) + w[j], o None si no es una pareja."""
    if i < 0 or j >= len(w):
        return None
    a, x = w[i], w[j]
    if a >> 26 != 15 or (a >> 16) & 31:
        return None
    op = x >> 26
    if not _completa(op) or _base(x, op) != (a >> 21) & 31:
        return None
    return (((a & 0xFFFF) << 16) + _parte_baja(x, op)) & 0xFFFFFFFF


def funciones(img):
    """[(inicio, fin)] de .pdata: las funciones con informacion de desenrollado."""
    sec = next(s for s in imagen.secciones(img) if s[0] == ".pdata")
    out = []
    for at in range(sec[1] - BASE, sec[2] - BASE - 7, 8):
        ini, info = struct.unpack_from(">II", img, at)
        if ini:
            out.append((ini, ini + 4 * ((info >> 8) & 0x3FFFFF)))
    return sorted(out)


class Emparejador:
    def __init__(self, img_ref, img_otra):
        self.a, self.b = img_ref, img_otra
        self.sa, self.sb = imagen.secciones(img_ref), imagen.secciones(img_otra)
        self.ta = next(s for s in self.sa if s[0] == ".text")
        self.tb = next(s for s in self.sb if s[0] == ".text")
        self.na = normalizar(img_ref[self.ta[1] - BASE:self.ta[2] - BASE])
        self.nb = normalizar(img_otra[self.tb[1] - BASE:self.tb[2] - BASE])
        self.cadena = _anclas(self.na, self.nb)
        self.pos_a = [a for a, _ in self.cadena]
        self.fa = funciones(img_ref)
        self._inicios = [f[0] for f in self.fa]
        self._rdata_b = next(s for s in self.sb if s[0] == ".rdata")
        self._refs = None       # _por_referencias, la primera vez que hace falta

    def _preparar_referencias(self):
        if self._refs is not None:
            return
        def palabras(img, sec):
            datos = img[sec[1] - BASE:sec[2] - BASE]
            return struct.unpack(">%dI" % (len(datos) // 4), datos[:len(datos) // 4 * 4])
        da = next(s for s in self.sa if s[0] == ".data")
        self._wa, self._wb = palabras(self.a, self.ta), palabras(self.b, self.tb)
        self._refs = _referencias(self._wa, da[1] - 0x400, da[2] + 0x400)
        self._conocidas = sorted(self._refs)

    def _indice(self, i):
        """Instruccion i de la referencia en la otra edicion, con el ancla anterior."""
        k = bisect.bisect_right(self.pos_a, i) - 1
        return i + (self.cadena[k][1] - self.cadena[k][0]) if k >= 0 else None

    def _votos(self, v, cuantas=64):
        """{lo que calculan en la otra edicion: cuantas} las parejas que dan v."""
        votos = {}
        for i, j in self._refs.get(v, [])[:cuantas]:
            i2, j2 = self._indice(i), self._indice(j)
            if i2 is None or j2 is None or j2 - i2 != j - i:
                continue
            otra = _direccion_en(self._wb, i2, j2)
            if otra is not None:
                votos[otra] = votos.get(otra, 0) + 1
        return votos

    def _desplazamiento_directo(self, v):
        """Lo que se mueve v si todas sus parejas coinciden, o None."""
        votos = self._votos(v)
        return next(iter(votos)) - v if len(votos) == 1 else None

    def _primer_desplazamiento(self, vecinas):
        for v in vecinas:
            desplazamiento = self._desplazamiento_directo(v)
            if desplazamiento is not None:
                return desplazamiento
        return None

    def _por_referencias(self, d):
        """
        (destino, estado) de una direccion de .data por el codigo que la
        calcula (datos_por_referencias.py de nfsmw-nx): las parejas lis + parte
        baja que dan d en la referencia se llevan a la otra edicion con las
        anclas, y se lee lo que calculan alli. Si no hay ninguna, el
        desplazamiento de las vecinas (a menos de 0x400) que si tienen; y si
        tampoco, el de las dos mas cercanas con referencias, una a cada lado,
        cuando se mueven lo mismo (como el traducir() de su verificar_parejas.py:
        una tabla cuya base se calcula y sus entradas no). Solo es segura si
        todas coinciden.
        """
        self._preparar_referencias()
        votos = self._votos(d)
        como = "directa"
        if not votos:
            como = "vecinas"
            k = bisect.bisect_left(self._conocidas, d)
            for v in self._conocidas[max(0, k - 3):k + 3]:
                if abs(v - d) >= 0x400:
                    continue
                for otra, n in self._votos(v, 16).items():
                    destino = (d + otra - v) & 0xFFFFFFFF
                    votos[destino] = votos.get(destino, 0) + n
        if not votos:
            k = bisect.bisect_left(self._conocidas, d)
            abajo = self._primer_desplazamiento(reversed(self._conocidas[max(0, k - 8):k]))
            arriba = self._primer_desplazamiento(self._conocidas[k:k + 8])
            if abajo is not None and abajo == arriba:
                return (d + abajo) & 0xFFFFFFFF, "referencias (entre vecinas, %+X)" % abajo
            return None, "REVISAR (sin referencias)"
        mejor = max(votos, key=votos.get)
        n, total = votos[mejor], sum(votos.values())
        if n == total:
            return mejor, "referencias (%s %d/%d)" % (como, n, total)
        return mejor, "REVISAR (referencias %s %d/%d)" % (como, n, total)

    @staticmethod
    def _seccion(secs, d):
        return next((s for s in secs if s[1] <= d < s[2]), None)

    def _texto(self, d, por_contenido=True):
        """
        Traduce una direccion de .text. Devuelve (destino, estado).

        por_contenido=False: sin el ultimo recurso (buscar las 16 instrucciones
        en toda la otra edicion). Puede dar con una coincidencia dentro de otra
        funcion: en la USA, 8256FEE0 salia en 8256FE84, y es 8256FCE8.
        """
        i = (d - self.ta[1]) // 4
        n_a, n_b = len(self.na) // 4, len(self.nb) // 4
        k = bisect.bisect_right(self.pos_a, i) - 1
        candidatos = []
        for ancla in (k, k + 1):                    # la anterior y, si falla, la siguiente
            if 0 <= ancla < len(self.cadena):
                j = i + (self.cadena[ancla][1] - self.cadena[ancla][0])
                if 0 <= j < n_b and j not in candidatos:
                    candidatos.append(j)
        for j in candidatos:
            n = min(VERIFICAR, n_a - i, n_b - j)
            if self.na[i * 4:(i + n) * 4] == self.nb[j * 4:(j + n) * 4]:
                return self.tb[1] + 4 * j + (d & 3), "exacta"
        # ultimo recurso: que las 16 instrucciones salgan una sola vez en la otra edicion
        trozo = self.na[i * 4:(i + VERIFICAR) * 4]
        p = self.nb.find(trozo) if por_contenido else -1
        while p >= 0 and p % 4:
            p = self.nb.find(trozo, p + 1)
        if p >= 0:
            q = self.nb.find(trozo, p + 4)
            while q >= 0 and q % 4:
                q = self.nb.find(trozo, q + 1)
            if q < 0:
                return self.tb[1] + p + (d & 3), "exacta (por contenido)"
        if candidatos:
            return self.tb[1] + 4 * candidatos[0] + (d & 3), "REVISAR"
        return None, "sin traducir"

    def traducir(self, d, por_contenido=True):
        """Devuelve (seccion, destino o None, estado)."""
        s = self._seccion(self.sa, d)
        nombre = s[0] if s else "fuera"
        destino, estado = None, "sin traducir"
        if nombre == ".text":
            destino, estado = self._texto(d, por_contenido)
        elif nombre == ".rdata":
            # 32 bytes y, si salen varias veces (cabeceras de shader parecidas), ventanas mayores
            zona = self.b[self._rdata_b[1] - BASE:self._rdata_b[2] - BASE]
            estado = "REVISAR (no aparece)"
            for ventana in (32, 64, 128, 256, 512, 1024):
                trozo = self.a[d - BASE:d - BASE + ventana]
                p = zona.find(trozo)
                if p < 0:
                    break
                if zona.find(trozo, p + 1) < 0:
                    destino, estado = self._rdata_b[1] + p, "exacta"
                    break
                estado = "REVISAR (aparece varias veces)"
        elif nombre in (".embsec_", ".no_bbt"):
            # codigo incrustado: la seccion del mismo orden y tamano; tiene que ser identica
            orden = [x for x in self.sa if x[0] == nombre].index(s)
            iguales = [x for x in self.sb if x[0] == nombre]
            if orden < len(iguales) and iguales[orden][2] - iguales[orden][1] == s[2] - s[1]:
                destino = iguales[orden][1] + (d - s[1])
                na = normalizar(self.a[d - BASE:d - BASE + 4 * VERIFICAR])
                nb = normalizar(self.b[destino - BASE:destino - BASE + 4 * VERIFICAR])
                estado = "exacta" if na == nb else "REVISAR (instrucciones distintas)"
        elif nombre == ".data" or nombre.startswith((".tls", ".idata")):
            otra = self._seccion(self.sb, d)
            if nombre == ".data" and otra and otra[0] == nombre and otra[2] - otra[1] != s[2] - s[1]:
                # La seccion cambia de tamano (la japonesa crece 0x5A0 bytes): los
                # datos se mueven dentro, a trozos. Por el codigo que los calcula.
                destino, estado = self._por_referencias(d)
            elif otra and otra[0] == nombre and otra[1] == s[1]:
                igual = self.a[d - BASE - 16:d - BASE + 16] == self.b[d - BASE - 16:d - BASE + 16]
                destino, estado = d, "misma direccion" + ("" if igual else " (contenido distinto alrededor)")
            else:
                estado = "REVISAR (la seccion se mueve)"
        return nombre, destino, estado

    def huella(self, destino):
        """Resumen de las 16 instrucciones normalizadas de la OTRA edicion en `destino`."""
        if not self.tb[1] <= destino < self.tb[2]:
            return "-"
        i = destino - self.tb[1]
        return hashlib.sha1(self.nb[i:i + 4 * VERIFICAR]).hexdigest()[:16]

    def funcion_de(self, d):
        """(inicio, fin) de la funcion de referencia que contiene d, segun .pdata."""
        k = bisect.bisect_right(self._inicios, d) - 1
        if k >= 0 and self.fa[k][0] <= d < self.fa[k][1]:
            return self.fa[k]
        # funcion hoja, sin entrada en .pdata: hasta la siguiente que si la tiene
        fin = self._inicios[k + 1] if k + 1 < len(self._inicios) else self.ta[2]
        return d, min(fin, d + 4 * 256)

    def comparar_funcion(self, d):
        """
        Compara ENTERA, sin normalizar, la funcion que contiene d. Devuelve la
        lista de diferencias que no se explican por un cambio de direccion:
          - saltos: el destino traducido tiene que ser el de la otra edicion;
          - lis: el mismo registro (la parte alta de una direccion);
          - addi/ori/cargas/guardados con otro inmediato: solo si el registro
            base sale de un lis de la misma funcion (la parte baja);
          - palabras de datos (tablas de salto): direcciones de .text traducidas.
        """
        ini, fin = self.funcion_de(d)
        e, estado = self._texto(ini)
        if e is None or not estado.startswith("exacta"):
            return ["el inicio %08X no tiene traduccion exacta" % ini]

        def destino(w, en):
            if w >> 26 == 18:
                li = w & 0x03FFFFFC
                li = li - 0x04000000 if li & 0x02000000 else li
                return (li if w & 2 else en + li) & 0xFFFFFFFF
            bd = w & 0xFFFC
            bd = bd - 0x10000 if bd & 0x8000 else bd
            return (bd if w & 2 else en + bd) & 0xFFFFFFFF

        def traducida(x):
            if self.ta[1] <= x < self.ta[2]:
                return self._texto(x)[0]
            return self.traducir(x)[1]

        lis, problemas = set(), []
        for k in range(0, fin - ini, 4):
            a = struct.unpack_from(">I", self.a, ini + k - BASE)[0]
            b = struct.unpack_from(">I", self.b, e + k - BASE)[0]
            op = a >> 26
            if a == b:
                if op == 15 and (a >> 16) & 31 == 0:
                    lis.add((a >> 21) & 31)
                continue
            # Palabra de datos (tabla de saltos): una direccion de .text,
            # traducida. Antes que mirar el opcode: 0x82xxxxxx se lee como un
            # lwz, y si la tabla no cambia de bloque de 64 KB pasaria por un
            # inmediato distinto.
            if self.ta[1] <= a < self.ta[2] and traducida(a) == b:
                continue
            if op != b >> 26:
                problemas.append("+%X: %08X / %08X" % (k, a, b))
            elif op in (16, 18):
                fijo = 0xFC000003 if op == 18 else 0xFFFF0003
                if a & fijo == b & fijo and traducida(destino(a, ini + k)) == destino(b, e + k):
                    continue
                problemas.append("+%X: salto %08X / %08X" % (k, a, b))
            elif a & 0xFFFF0000 == b & 0xFFFF0000:
                if op == 15 and (a >> 16) & 31 == 0:
                    lis.add((a >> 21) & 31)
                    continue
                if (op in (14, 24) or 32 <= op <= 55) and (a >> 16) & 31 in lis:
                    continue
                problemas.append("+%X: inmediato %08X / %08X" % (k, a, b))
            else:
                problemas.append("+%X: %08X / %08X" % (k, a, b))
        return problemas

    def comprobar_parejas(self, d):
        """
        Mas estricto que comparar_funcion, que da por buena cualquier parte baja
        de un lis (es una direccion): aqui cada pareja lis + parte baja de la
        funcion que contiene d tiene que calcular, en la otra edicion, la
        traduccion de la direccion de la referencia (verificar_parejas.py de
        nfsmw-nx). En el codigo y en .data, la de traducir(); en el resto, el
        mismo contenido salvo punteros a codigo, traducidos. Es lo que
        comprueba que .data se ha traducido bien en una edicion donde se mueve.

        Devuelve (parejas, problemas, avisos). Avisos: constantes que la otra
        edicion cambia de valor (la japonesa: 4400.0 por 2800.0 en la funcion
        de la luminancia). Es su codigo y lee lo suyo; solo importan si la app
        sustituye esa funcion por codigo nativo con los valores de la
        referencia.
        """
        ini, fin = self.funcion_de(d)
        e, estado = self._texto(ini, por_contenido=False)
        if e is None or not estado.startswith("exacta"):
            return 0, ["el inicio %08X no tiene traduccion exacta" % ini], []
        alta_a, alta_b = {}, {}
        parejas, problemas, avisos = 0, [], []
        for k in range(0, fin - ini, 4):
            a = struct.unpack_from(">I", self.a, ini + k - BASE)[0]
            b = struct.unpack_from(">I", self.b, e + k - BASE)[0]
            op = a >> 26
            if op == 15 and (a >> 16) & 31 == 0:
                alta_a[(a >> 21) & 31] = (a & 0xFFFF) << 16
                if b >> 26 == 15 and (b >> 16) & 31 == 0:
                    alta_b[(b >> 21) & 31] = (b & 0xFFFF) << 16
                continue
            if _completa(op):
                base = _base(a, op)
                if base and base in alta_a and base in alta_b:
                    da = (alta_a[base] + _parte_baja(a, op)) & 0xFFFFFFFF
                    db = (alta_b[base] + _parte_baja(b, b >> 26)) & 0xFFFFFFFF
                    parejas += 1
                    s = self._seccion(self.sa, da)
                    nombre = s[0] if s else "fuera"
                    if nombre in (".text", ".data", ".embsec_", ".no_bbt"):
                        # Sin traduccion no hay con que comparar: la app no la
                        # usa (si la usara, faltaria en la tabla).
                        _, esperada, _ = self.traducir(da, por_contenido=False)
                        if esperada is not None and esperada != db:
                            problemas.append("+%X: %08X (%s) tendria que ser %08X y la otra usa %08X" % (
                                k, da, nombre, esperada, db))
                    elif nombre != "fuera" and not self._mismo_contenido(da, db):
                        avisos.append("%08X+%X: %08X (%s) con otro valor en %08X" % (ini, k, da, nombre, db))
            # la pareja acaba si se escribe la base (aproximado: destino en los bits 21-25)
            if op == 24:
                alta_a.pop((a >> 16) & 31, None)
                alta_b.pop((b >> 16) & 31, None)
            elif op not in _GUARDADOS:
                alta_a.pop((a >> 21) & 31, None)
                alta_b.pop((b >> 21) & 31, None)
        return parejas, problemas, avisos

    def _mismo_contenido(self, da, db, n=16):
        """Los mismos n bytes, salvo punteros a codigo (tablas de funciones), traducidos."""
        for k in range(0, n, 4):
            x = struct.unpack_from(">I", self.a, da + k - BASE)[0]
            y = struct.unpack_from(">I", self.b, db + k - BASE)[0]
            if x == y:
                continue
            s = self._seccion(self.sa, x)
            if s and s[0] in (".text", ".embsec_", ".no_bbt") and self.traducir(x, por_contenido=False)[1] == y:
                continue
            return False
        return True


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    cache = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                         "assets", "ediciones", "imagenes")
    img_a, _ = imagen.cargar(sys.argv[1], cache)
    img_b, _ = imagen.cargar(sys.argv[2], cache)
    pedidas = ([int(x, 16) for x in sys.argv[4:]] if len(sys.argv) > 4 else
               [int(l.split()[0], 16) for l in sys.stdin if l.strip()])
    emp = Emparejador(img_a, img_b)
    print("anclas en .text: %d (de %d instrucciones)" % (len(emp.cadena), len(emp.na) // 4))
    filas, cuenta = [], {}
    for d in sorted(set(pedidas)):
        nombre, destino, estado = emp.traducir(d)
        clave = nombre + " " + estado.split(" (")[0]
        cuenta[clave] = cuenta.get(clave, 0) + 1
        filas.append("%08X\t%s\t%s\t%s" % (d, nombre, "%08X" % destino if destino else "-", estado))
    with open(sys.argv[3], "w", encoding="utf-8", newline="\n") as fh:
        fh.write("ref\tseccion\totra\testado\n" + "\n".join(filas) + "\n")
    for k, v in sorted(cuenta.items()):
        print("  %-40s %d" % (k, v))
    return 0


if __name__ == "__main__":
    sys.exit(main())
