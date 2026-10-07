#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Saca la imagen del ejecutable (el PE ya descifrado y descomprimido) de un XEX.

    python tools/ediciones/imagen.py assets/game_root/default.xex salida.bin

Sin dependencias: Python 3.8+ de la biblioteca estandar.

Es lo que el SDK hace al cargar el juego (src/system/xex_module.cpp): descifra
la clave de sesion con la clave de retail, descifra los datos con AES-128-CBC y
los descomprime con LZX. Aqui hace falta para COMPARAR dos ediciones del juego:
el XEX va cifrado, asi que dos ejecutables casi iguales no se parecen en nada
hasta que se sacan sus imagenes.

La imagen queda tal como se carga en 0x82000000: la direccion D del juego esta
en el byte D - 0x82000000.

La imagen ES el juego. No se versiona: va a assets/, que esta en .gitignore.
"""

import hashlib
import os
import struct
import sys

BASE = 0x82000000
CLAVE_RETAIL = bytes.fromhex("20B185A59D28FDC340583FBB0896BF91")


# ---------------------------------------------------------------------------
# AES-128, solo descifrar (cifrador inverso equivalente, con tablas)
# ---------------------------------------------------------------------------

def _tablas_aes():
    def xtime(a):
        a <<= 1
        return (a ^ 0x11B) & 0xFF if a & 0x100 else a

    def mul(a, b):
        r = 0
        while b:
            if b & 1:
                r ^= a
            a = xtime(a)
            b >>= 1
        return r

    # caja S: inverso multiplicativo y transformacion afin
    s = [0] * 256
    p = q = 1
    while True:
        p = p ^ xtime(p)                       # p por 3
        q ^= q << 1
        q ^= q << 2
        q ^= q << 4
        q &= 0xFF
        if q & 0x80:
            q ^= 0x09                          # q entre 3
        x = q ^ ((q << 1) | (q >> 7)) ^ ((q << 2) | (q >> 6)) ^ ((q << 3) | (q >> 5)) ^ ((q << 4) | (q >> 4))
        s[p] = (x ^ 0x63) & 0xFF
        if p == 1:
            break
    s[0] = 0x63
    si = [0] * 256
    for i, v in enumerate(s):
        si[v] = i
    td0 = [(mul(v, 14) << 24) | (mul(v, 9) << 16) | (mul(v, 13) << 8) | mul(v, 11) for v in si]
    td1 = [((t >> 8) | (t << 24)) & 0xFFFFFFFF for t in td0]
    td2 = [((t >> 16) | (t << 16)) & 0xFFFFFFFF for t in td0]
    td3 = [((t >> 24) | (t << 8)) & 0xFFFFFFFF for t in td0]
    return s, si, td0, td1, td2, td3


_S, _SI, _TD0, _TD1, _TD2, _TD3 = _tablas_aes()


def _claves_descifrado(clave):
    w = list(struct.unpack(">4I", clave))
    rcon = 1
    for i in range(4, 44):
        t = w[i - 1]
        if i % 4 == 0:
            t = ((t << 8) | (t >> 24)) & 0xFFFFFFFF
            t = (_S[t >> 24] << 24) | (_S[(t >> 16) & 255] << 16) | (_S[(t >> 8) & 255] << 8) | _S[t & 255]
            t ^= rcon << 24
            rcon = ((rcon << 1) ^ 0x11B) & 0xFF if rcon & 0x80 else rcon << 1
        w.append(w[i - 4] ^ t)
    # orden inverso de rondas, con InvMixColumns en las de en medio
    rk = []
    for ronda in range(10, -1, -1):
        for x in w[4 * ronda:4 * ronda + 4]:
            if 0 < ronda < 10:
                x = (_TD0[_S[x >> 24]] ^ _TD1[_S[(x >> 16) & 255]] ^
                     _TD2[_S[(x >> 8) & 255]] ^ _TD3[_S[x & 255]])
            rk.append(x)
    return rk


def aes_cbc_descifrar(clave, datos):
    """AES-128-CBC con IV cero. La cola que no llena un bloque se deja como esta."""
    rk = _claves_descifrado(clave)
    td0, td1, td2, td3, si = _TD0, _TD1, _TD2, _TD3, _SI
    n = len(datos) // 16
    palabras = struct.unpack(">%dI" % (n * 4), datos[:n * 16])
    salida = [0] * (n * 4)
    p0 = p1 = p2 = p3 = 0
    k0, k1, k2, k3 = rk[0:4]
    medias = [tuple(rk[4 * r:4 * r + 4]) for r in range(1, 10)]
    f0, f1, f2, f3 = rk[40:44]
    for b in range(0, n * 4, 4):
        c0, c1, c2, c3 = palabras[b:b + 4]
        s0, s1, s2, s3 = c0 ^ k0, c1 ^ k1, c2 ^ k2, c3 ^ k3
        for r0, r1, r2, r3 in medias:
            t0 = td0[s0 >> 24] ^ td1[(s3 >> 16) & 255] ^ td2[(s2 >> 8) & 255] ^ td3[s1 & 255] ^ r0
            t1 = td0[s1 >> 24] ^ td1[(s0 >> 16) & 255] ^ td2[(s3 >> 8) & 255] ^ td3[s2 & 255] ^ r1
            t2 = td0[s2 >> 24] ^ td1[(s1 >> 16) & 255] ^ td2[(s0 >> 8) & 255] ^ td3[s3 & 255] ^ r2
            t3 = td0[s3 >> 24] ^ td1[(s2 >> 16) & 255] ^ td2[(s1 >> 8) & 255] ^ td3[s0 & 255] ^ r3
            s0, s1, s2, s3 = t0, t1, t2, t3
        salida[b] = ((si[s0 >> 24] << 24) | (si[(s3 >> 16) & 255] << 16) |
                     (si[(s2 >> 8) & 255] << 8) | si[s1 & 255]) ^ f0 ^ p0
        salida[b + 1] = ((si[s1 >> 24] << 24) | (si[(s0 >> 16) & 255] << 16) |
                         (si[(s3 >> 8) & 255] << 8) | si[s2 & 255]) ^ f1 ^ p1
        salida[b + 2] = ((si[s2 >> 24] << 24) | (si[(s1 >> 16) & 255] << 16) |
                         (si[(s0 >> 8) & 255] << 8) | si[s3 & 255]) ^ f2 ^ p2
        salida[b + 3] = ((si[s3 >> 24] << 24) | (si[(s2 >> 16) & 255] << 16) |
                         (si[(s1 >> 8) & 255] << 8) | si[s0 & 255]) ^ f3 ^ p3
        p0, p1, p2, p3 = c0, c1, c2, c3
    return struct.pack(">%dI" % (n * 4), *salida) + datos[n * 16:]


# ---------------------------------------------------------------------------
# LZX (el de los .cab), segun thirdparty/libmspack del SDK
# ---------------------------------------------------------------------------

_RANURAS = [30, 32, 34, 36, 38, 42, 50, 66, 98, 162, 290]   # por bits de ventana, desde 15
_FRAME = 32768


def _tabla_huffman(longitudes, n, puede_estar_vacia=False):
    """Tabla de descodificado directo: indice = los proximos `maxima` bits."""
    maxima = max(longitudes[:n])
    if maxima == 0:
        if puede_estar_vacia:
            return None, 0
        raise ValueError("LZX: arbol de Huffman vacio")
    tabla = [0] * (1 << maxima)
    pos = 0
    for largo in range(1, maxima + 1):
        tramo = 1 << (maxima - largo)
        for simbolo in range(n):
            if longitudes[simbolo] == largo:
                tabla[pos:pos + tramo] = [(simbolo << 5) | largo] * tramo
                pos += tramo
    if pos != len(tabla):
        raise ValueError("LZX: arbol de Huffman incompleto")
    return tabla, maxima


def lzx_descomprimir(datos, tam_salida, bits_ventana):
    if not 15 <= bits_ventana <= 25:
        raise ValueError("LZX: ventana de %d bits" % bits_ventana)
    n_principal = 256 + (_RANURAS[bits_ventana - 15] << 3)
    bits_extra = [0, 0, 0, 0] + [min(i // 2 - 1, 17) for i in range(4, 290)]
    base_pos = [0]
    for i in range(1, 290):
        base_pos.append(base_pos[-1] + (1 << bits_extra[i - 1]))

    datos = bytes(datos) + bytes(64)
    out = bytearray(tam_salida)
    # estado del flujo de bits: palabras de 16 bits little-endian, del bit alto al bajo
    pos = 0          # siguiente byte sin leer
    buf = 0          # bits leidos y aun sin consumir (los nb bajos)
    nb = 0

    def bits(n):
        nonlocal pos, buf, nb
        while nb < n:
            buf = ((buf & ((1 << nb) - 1)) << 16) | datos[pos] | (datos[pos + 1] << 8)
            pos += 2
            nb += 16
        nb -= n
        return (buf >> nb) & ((1 << n) - 1)

    def simbolo(tabla, maxima):
        nonlocal pos, buf, nb
        while nb < maxima:
            buf = ((buf & ((1 << nb) - 1)) << 16) | datos[pos] | (datos[pos + 1] << 8)
            pos += 2
            nb += 16
        e = tabla[(buf >> (nb - maxima)) & ((1 << maxima) - 1)]
        nb -= e & 31
        return e >> 5

    def leer_longitudes(longitudes, desde, hasta):
        pre = [bits(4) for _ in range(20)]
        tabla, maxima = _tabla_huffman(pre, 20)
        x = desde
        while x < hasta:
            z = simbolo(tabla, maxima)
            if z == 17:
                y = bits(4) + 4
                valor = 0
            elif z == 18:
                y = bits(5) + 20
                valor = 0
            elif z == 19:
                y = bits(1) + 4
                valor = (longitudes[x] - simbolo(tabla, maxima)) % 17
            else:
                y = 1
                valor = (longitudes[x] - z) % 17
            for _ in range(y):
                if x < len(longitudes):
                    longitudes[x] = valor
                x += 1

    if bits(1):
        if (bits(16) << 16) | bits(16):
            # Traduccion de saltos de x86 (E8). Un ejecutable de PowerPC no la lleva.
            raise ValueError("LZX: flujo con preprocesado de x86, no soportado")

    lon_principal = [0] * (n_principal + 64)
    lon_largos = [0] * (249 + 64)
    lon_alineado = [0] * 8
    t_principal = t_largos = t_alineado = None
    m_principal = m_largos = m_alineado = 0
    r0 = r1 = r2 = 1
    tipo = 0
    largo_bloque = quedan = 0
    wp = 0

    while wp < tam_salida:
        fin_frame = min(wp + _FRAME, tam_salida)
        while wp < fin_frame:
            if quedan == 0:
                if tipo == 3 and largo_bloque & 1:
                    pos += 1                       # relleno de un bloque sin comprimir impar
                tipo = bits(3)
                largo_bloque = quedan = (bits(16) << 8) | bits(8)
                if tipo in (1, 2):
                    if tipo == 2:
                        for i in range(8):
                            lon_alineado[i] = bits(3)
                        t_alineado, m_alineado = _tabla_huffman(lon_alineado, 8)
                    leer_longitudes(lon_principal, 0, 256)
                    leer_longitudes(lon_principal, 256, n_principal)
                    t_principal, m_principal = _tabla_huffman(lon_principal, n_principal)
                    leer_longitudes(lon_largos, 0, 249)
                    t_largos, m_largos = _tabla_huffman(lon_largos, 249, True)
                elif tipo == 3:
                    # se alinea a 16 bits; si ya lo estaba, se salta una palabra entera
                    consumidos = pos * 8 - nb
                    consumidos += 16 - consumidos % 16
                    pos, buf, nb = consumidos // 8, 0, 0
                    r0, r1, r2 = struct.unpack_from("<3I", datos, pos)
                    pos += 12
                else:
                    raise ValueError("LZX: tipo de bloque %d" % tipo)

            tramo = min(quedan, fin_frame - wp)
            quedan -= tramo
            fin = wp + tramo
            if tipo == 3:
                out[wp:fin] = datos[pos:pos + tramo]
                pos += tramo
                wp = fin
                continue

            alineado = tipo == 2
            mascara = (1 << m_principal) - 1
            while wp < fin:
                if nb < 16:
                    buf = ((buf & ((1 << nb) - 1)) << 16) | datos[pos] | (datos[pos + 1] << 8)
                    pos += 2
                    nb += 16
                e = t_principal[(buf >> (nb - m_principal)) & mascara]
                nb -= e & 31
                e >>= 5
                if e < 256:
                    out[wp] = e
                    wp += 1
                    continue
                e -= 256
                largo = e & 7
                if largo == 7:
                    if t_largos is None:
                        raise ValueError("LZX: hace falta el arbol de largos y esta vacio")
                    if nb < 16:
                        buf = ((buf & ((1 << nb) - 1)) << 16) | datos[pos] | (datos[pos + 1] << 8)
                        pos += 2
                        nb += 16
                    x = t_largos[(buf >> (nb - m_largos)) & ((1 << m_largos) - 1)]
                    nb -= x & 31
                    largo += x >> 5
                largo += 2
                ranura = e >> 3
                if ranura == 0:
                    dist = r0
                elif ranura == 1:
                    dist = r1
                    r1 = r0
                    r0 = dist
                elif ranura == 2:
                    dist = r2
                    r2 = r0
                    r0 = dist
                else:
                    extra = bits_extra[ranura]
                    dist = base_pos[ranura] - 2
                    if extra >= 3 and alineado:
                        if extra > 3:
                            n = extra - 3
                            while nb < n:
                                buf = ((buf & ((1 << nb) - 1)) << 16) | datos[pos] | (datos[pos + 1] << 8)
                                pos += 2
                                nb += 16
                            nb -= n
                            dist += ((buf >> nb) & ((1 << n) - 1)) << 3
                        if nb < 16:
                            buf = ((buf & ((1 << nb) - 1)) << 16) | datos[pos] | (datos[pos + 1] << 8)
                            pos += 2
                            nb += 16
                        x = t_alineado[(buf >> (nb - m_alineado)) & ((1 << m_alineado) - 1)]
                        nb -= x & 31
                        dist += x >> 5
                    elif extra:
                        while nb < extra:
                            buf = ((buf & ((1 << nb) - 1)) << 16) | datos[pos] | (datos[pos + 1] << 8)
                            pos += 2
                            nb += 16
                        nb -= extra
                        dist += (buf >> nb) & ((1 << extra) - 1)
                    r2 = r1
                    r1 = r0
                    r0 = dist
                origen = wp - dist
                if origen < 0:
                    raise ValueError("LZX: copia de antes del principio")
                if dist >= largo:
                    out[wp:wp + largo] = out[origen:origen + largo]
                else:
                    for i in range(largo):
                        out[wp + i] = out[origen + i]
                wp += largo
            if wp > fin:
                # la ultima copia se paso del tramo: sale del resto del bloque
                quedan -= wp - fin
                if quedan < 0 or wp > fin_frame:
                    raise ValueError("LZX: una copia se sale del bloque")

        # cada frame de 32 KB empieza en palabra de 16 bits
        if tipo != 3:
            consumidos = pos * 8 - nb
            if consumidos % 16:
                consumidos += 16 - consumidos % 16
            pos, buf, nb = consumidos // 8, 0, 0
    return bytes(out[:tam_salida])


# ---------------------------------------------------------------------------
# XEX2
# ---------------------------------------------------------------------------

def _opcionales(xex):
    n = struct.unpack_from(">I", xex, 0x14)[0]
    return dict(struct.unpack_from(">II", xex, 0x18 + i * 8) for i in range(n))


def imagen_de_xex(xex):
    """Devuelve la imagen (bytes) de un XEX2 leido entero en memoria."""
    if xex[:4] != b"XEX2":
        raise ValueError("no empieza por 'XEX2': no es un ejecutable de Xbox 360")
    off_datos, off_seguridad = struct.unpack_from(">I", xex, 0x08)[0], struct.unpack_from(">I", xex, 0x10)[0]
    tam_imagen = struct.unpack_from(">I", xex, off_seguridad + 0x004)[0]
    clave_fichero = xex[off_seguridad + 0x150:off_seguridad + 0x160]
    ffi = _opcionales(xex).get(0x000003FF)
    if ffi is None:
        raise ValueError("XEX sin 'file format info'")
    tam_info, cifrado, compresion = struct.unpack_from(">IHH", xex, ffi)

    datos = xex[off_datos:]
    if cifrado == 1:
        clave_sesion = aes_cbc_descifrar(CLAVE_RETAIL, clave_fichero)
        datos = aes_cbc_descifrar(clave_sesion, datos)
    elif cifrado != 0:
        raise ValueError("cifrado %d desconocido" % cifrado)

    if compresion == 0:
        img = datos[:tam_imagen]
    elif compresion == 1:
        # basica: pares (bytes de datos, bytes a cero)
        trozos, p = [], 0
        for i in range((tam_info - 8) // 8):
            n_datos, n_ceros = struct.unpack_from(">II", xex, ffi + 8 + i * 8)
            trozos.append(datos[p:p + n_datos])
            trozos.append(bytes(n_ceros))
            p += n_datos
        img = b"".join(trozos)[:tam_imagen]
    elif compresion == 2:
        ventana, tam_bloque = struct.unpack_from(">II", xex, ffi + 8)
        resumen = xex[ffi + 16:ffi + 36]
        comprimido, p = [], 0
        while tam_bloque:
            bloque = datos[p:p + tam_bloque]
            if hashlib.sha1(bloque).digest() != resumen:
                raise ValueError("el resumen de un bloque no cuadra: XEX danado, o cifrado con "
                                 "otra clave (un XEX de devkit, por ejemplo)")
            siguiente = struct.unpack_from(">I", bloque, 0)[0]
            resumen = bloque[4:24]
            q = 24
            while True:
                n = (bloque[q] << 8) | bloque[q + 1]
                q += 2
                if not n:
                    break
                comprimido.append(bloque[q:q + n])
                q += n
            p += tam_bloque
            tam_bloque = siguiente
        img = lzx_descomprimir(b"".join(comprimido), tam_imagen, ventana.bit_length() - 1)
    else:
        raise ValueError("compresion %d no soportada (3 es un parche delta)" % compresion)

    if img[:2] != b"MZ":
        raise ValueError("lo descifrado no es un PE: clave o formato equivocados")
    return img.ljust(tam_imagen, b"\0")


def cargar(ruta_xex, cache=None):
    """
    Imagen de un XEX. Con `cache` (una carpeta), la guarda alli con el SHA-256
    del XEX en el nombre y la proxima vez la lee de ahi: descomprimir en Python
    tarda unos segundos.
    """
    with open(ruta_xex, "rb") as fh:
        xex = fh.read()
    huella = hashlib.sha256(xex).hexdigest()
    guardada = os.path.join(cache, huella + ".img") if cache else None
    if guardada and os.path.isfile(guardada):
        with open(guardada, "rb") as fh:
            return fh.read(), huella
    img = imagen_de_xex(xex)
    if guardada:
        os.makedirs(cache, exist_ok=True)
        with open(guardada, "wb") as fh:
            fh.write(img)
    return img, huella


def secciones(img):
    """[(nombre, direccion inicial, direccion final)] de la tabla de secciones del PE."""
    pe = struct.unpack_from("<I", img, 0x3C)[0]
    n = struct.unpack_from("<H", img, pe + 6)[0]
    opt = struct.unpack_from("<H", img, pe + 20)[0]
    out = []
    for i in range(n):
        at = pe + 24 + opt + i * 40
        nombre = img[at:at + 8].rstrip(b"\0").decode("latin-1")
        vsize, vaddr = struct.unpack_from("<II", img, at + 8)
        out.append((nombre, BASE + vaddr, BASE + vaddr + vsize))
    return out


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    with open(sys.argv[1], "rb") as fh:
        xex = fh.read()
    img = imagen_de_xex(xex)
    with open(sys.argv[2], "wb") as fh:
        fh.write(img)
    print("XEX    sha256 %s" % hashlib.sha256(xex).hexdigest())
    print("imagen %d bytes, sha256 %s" % (len(img), hashlib.sha256(img).hexdigest()))
    for nombre, ini, fin in secciones(img):
        print("  %-8s %08X - %08X" % (nombre, ini, fin))
    return 0


if __name__ == "__main__":
    sys.exit(main())
