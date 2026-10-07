#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ediciones del juego: reconocer la de un default.xex y llevar las direcciones
del proyecto, que estan escritas para la PAL Espana, a las de otra edicion.

    python tools/ediciones/ediciones.py detectar [default.xex]
    python tools/ediciones/ediciones.py aplicar <edicion> <carpeta de salida>
    python tools/ediciones/ediciones.py fuentes <edicion> <carpeta de salida> <fichero>...
    python tools/ediciones/ediciones.py mapa <edicion> <referencia.xex> <otra.xex>

Sin dependencias: Python 3.8+. Ver docs/ediciones.md.


POR QUE HACE FALTA
==================

Cada default.xex distinto es un programa distinto. overrides.toml, huecos.toml
y los ganchos de C++ nombran funciones y datos del juego por su direccion, y
esas direcciones son las del ejecutable PAL Espana. En la edicion USA casi todo
el codigo esta unos cientos de bytes antes: los mismos ganchos, puestos en las
direcciones espanolas, caerian en mitad de otras funciones.


QUE SE GUARDA EN EL REPOSITORIO
===============================

  ediciones.json            las ediciones conocidas: SHA-256 del XEX, nombre del
                            PDB, idioma y pais que se le pasan al juego
  <edicion>/direcciones.tsv cada direccion que usa el proyecto y su equivalente
                            en esa edicion, con un resumen de las 16
                            instrucciones (normalizadas) que hay alli

Son direcciones y resumenes, no codigo del juego. Con eso, quien solo tiene la
ISO de USA compila sin necesitar el XEX espanol: `aplicar` traduce los
ficheros con la tabla, y los resumenes comprueban que su XEX es el de la tabla.

Rehacer una tabla (`mapa`) si necesita los DOS ejecutables: el de referencia y
el de la edicion. Hay que rehacerla cuando el proyecto usa una direccion nueva.
"""

import hashlib
import json
import os
import pathlib
import re
import sys

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
sys.path.insert(0, str(AQUI))
import imagen  # noqa: E402

DATOS = AQUI / "ediciones.json"
CACHE = RAIZ / "assets" / "ediciones" / "imagenes"

# Lo que lee el codegen. El manifiesto se reescribe aparte.
CODEGEN = ["common/codegen/overrides.toml", "common/codegen/huecos.toml"]
MANIFIESTO = "common/codegen/nfsmw_manifest.toml"
# Donde hay C++ del proyecto que puede nombrar direcciones del juego.
CARPETAS_CPP = ["common/src"]
EXT_CPP = (".cpp", ".h", ".hpp", ".inl", ".c")

DIRECCION = re.compile(r"(?<![0-9A-Fa-f])82[0-9A-Fa-f]{6}(?![0-9A-Fa-f])")
# Trozos de un fichero: comentario, cadena o el resto. Solo se traduce lo que
# NO es comentario: los comentarios cuentan la historia de la edicion de
# referencia y muchos nombran direcciones que en otra edicion ni existen.
_TROZOS = {
    "toml": re.compile(r'(?P<cadena>"[^"\n]*")|(?P<comentario>#[^\n]*)'),
    "cpp": re.compile(r'(?P<cadena>"(?:\\.|[^"\\\n])*")|(?P<comentario>//[^\n]*|/\*.*?\*/)', re.S),
}
_FIN = re.compile(r"\bend\s*=\s*(?:0x)?$")
SEGUROS = ("exacta", "misma direccion", "a mano")


def fallar(msg):
    sys.exit("[ERROR] " + msg)


def datos():
    with open(DATOS, encoding="utf-8") as fh:
        return json.load(fh)


def _leer(ruta):
    """El texto tal cual, sin tocar los finales de linea."""
    with open(ruta, encoding="utf-8", newline="") as fh:
        return fh.read()


def _tipo(ruta):
    return "toml" if str(ruta).endswith(".toml") else "cpp"


def _recorrer(texto, tipo, cambiar):
    """
    Pasa cada direccion que esta fuera de un comentario por cambiar(direccion,
    uso, texto original) y devuelve el texto con lo que cambiar() devuelva.
    uso es "fin" tras "end =" (el final de una funcion) y "dir" en el resto.
    """
    salida, pos = [], 0

    def codigo(trozo):
        def sustituir(m):
            uso = "fin" if _FIN.search(trozo, 0, m.start()) else "dir"
            return cambiar(int(m.group(), 16), uso, m.group())
        return DIRECCION.sub(sustituir, trozo)

    for m in _TROZOS[tipo].finditer(texto):
        salida.append(codigo(texto[pos:m.start()]))
        salida.append(m.group() if m.group("comentario") else codigo(m.group()))
        pos = m.end()
    salida.append(codigo(texto[pos:]))
    return "".join(salida)


def fuentes_cpp():
    out = []
    for carpeta in CARPETAS_CPP:
        out += sorted(p for p in (RAIZ / carpeta).iterdir() if p.is_file() and p.suffix in EXT_CPP)
    return out


def direcciones_del_proyecto():
    """{(direccion, uso): [ficheros]} de todo lo que el proyecto nombra en codigo."""
    usadas = {}
    for ruta in [RAIZ / r for r in CODEGEN] + fuentes_cpp():
        rel = ruta.relative_to(RAIZ).as_posix()

        def apuntar(d, uso, original):
            usadas.setdefault((d, uso), []).append(rel)
            return original
        _recorrer(_leer(ruta), _tipo(ruta), apuntar)
    return usadas


# ---------------------------------------------------------------------------
# La tabla de una edicion
# ---------------------------------------------------------------------------

def ruta_tabla(edicion):
    return AQUI / edicion / "direcciones.tsv"


def cargar_tabla(edicion):
    """{(direccion, uso): (destino o None, estado, huella)}"""
    ruta = ruta_tabla(edicion)
    if not ruta.is_file():
        fallar("No hay tabla de direcciones para la edicion '%s' (%s)." % (edicion, ruta))
    tabla = {}
    for linea in ruta.read_text(encoding="utf-8").splitlines()[1:]:
        ref, uso, _seccion, otra, estado, huella = linea.split("\t")
        tabla[(int(ref, 16), uso)] = (None if otra == "-" else int(otra, 16), estado, huella)
    return tabla


def _huella(norm_texto, inicio_texto, fin_texto, d):
    if not inicio_texto <= d < fin_texto:
        return "-"
    i = d - inicio_texto
    return hashlib.sha1(norm_texto[i:i + 64]).hexdigest()[:16]


def comprobar_huellas(edicion, img):
    """Cuantas direcciones de la tabla NO tienen en `img` el codigo que la tabla espera."""
    import emparejar
    texto = next(s for s in imagen.secciones(img) if s[0] == ".text")
    norm = emparejar.normalizar(img[texto[1] - imagen.BASE:texto[2] - imagen.BASE])
    total = malas = 0
    for (_, _), (destino, _estado, huella) in cargar_tabla(edicion).items():
        if destino is None or huella == "-":
            continue
        total += 1
        malas += _huella(norm, texto[1], texto[2], destino) != huella
    return total, malas


# ---------------------------------------------------------------------------
# detectar
# ---------------------------------------------------------------------------

def _pdb(img):
    m = re.search(rb"NfsMW[0-9A-Za-z_]*\.pdb", img)
    return m.group().decode("ascii") if m else None


def detectar(ruta_xex):
    """
    Devuelve la ficha de la edicion de ese XEX: las claves de ediciones.json
    mas "id", "sha256", "tabla" (la edicion cuya tabla de direcciones vale) y
    "aviso" si no se reconocio por su SHA-256.
    """
    conocidas = datos()
    with open(ruta_xex, "rb") as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()
    for ident, ficha in conocidas["ediciones"].items():
        if sha in ficha.get("sha256", []):
            return dict(ficha, id=ident, sha256=sha, tabla=ficha.get("tabla", ident))

    # XEX que no se ha visto: por el nombre del PDB, y comprobando el codigo.
    img, _ = imagen.cargar(ruta_xex, str(CACHE))
    pdb = _pdb(img)
    candidata = None
    for ident, ficha in conocidas["ediciones"].items():
        if pdb and pdb == ficha.get("pdb"):
            candidata = dict(ficha, id=ident, tabla=ficha.get("tabla", ident))
    if candidata is None and pdb:
        # NfsMWEurope<idioma>Release.pdb: la compilacion europea de la de referencia
        m = re.fullmatch(r"NfsMWEurope([A-Za-z]+)Release\.pdb", pdb)
        if m:
            for ident, ficha in conocidas["europeas"].items():
                if m.group(1).lower().startswith(tuple(ficha["pdb_empieza"])):
                    candidata = dict(ficha, id=ident, pdb=pdb, tabla=conocidas["referencia"])
            if candidata is None:
                fallar("El XEX es de la compilacion europea (%s) pero no se de que idioma.\n"
                       "        Anade su prefijo a \"europeas\" en %s." % (pdb, DATOS))
    if candidata is None:
        fallar("No reconozco esta edicion del juego.\n"
               "        SHA-256 del XEX: %s\n        PDB: %s\n"
               "        Ediciones con soporte: %s.\n"
               "        Para anadir una hace falta tambien el XEX de referencia: ver docs/ediciones.md."
               % (sha, pdb, ", ".join(sorted(conocidas["ediciones"]))))
    total, malas = comprobar_huellas(candidata["tabla"], img)
    if malas:
        fallar("El XEX parece '%s' (%s), pero %d de las %d direcciones de su tabla no llevan el "
               "codigo esperado.\n        Es otra compilacion del juego: hace falta una tabla "
               "nueva. Ver docs/ediciones.md.\n        SHA-256: %s"
               % (candidata["nombre"], pdb, malas, total, sha))
    candidata["sha256"] = sha
    candidata["aviso"] = ("XEX no visto antes (SHA-256 %s). Reconocido por el PDB '%s'; las %d "
                          "direcciones de la tabla '%s' llevan el codigo esperado."
                          % (sha, pdb, total, candidata["tabla"]))
    return candidata


# ---------------------------------------------------------------------------
# aplicar / fuentes: traducir ficheros con la tabla
# ---------------------------------------------------------------------------

class Traductor:
    def __init__(self, edicion):
        self.edicion = edicion
        self.identidad = edicion == datos()["referencia"]
        self.tabla = {} if self.identidad else cargar_tabla(edicion)
        self.faltan = set()

    def texto(self, texto, tipo):
        if self.identidad:
            return texto

        def cambiar(d, uso, original):
            destino, estado, _ = self.tabla.get((d, uso), (None, "no esta en la tabla", "-"))
            if destino is None or not estado.startswith(SEGUROS):
                self.faltan.add("%08X (%s)" % (d, estado))
                return original
            nuevo = "%08X" % destino
            return nuevo.lower() if any(c in "abcdef" for c in original) else nuevo
        return _recorrer(texto, tipo, cambiar)

    def huecos(self, texto):
        """
        huecos.toml: una declaracion cuyo sitio en la otra edicion es dudoso
        puede partir otra funcion. Esas lineas se quitan; las que falten las
        encuentra tools/huecos.py tras el codegen y van a <edicion>/huecos.toml.
        """
        if self.identidad:
            return texto, []
        lineas, quitadas = [], []
        for linea in texto.splitlines(True):
            antes = set(self.faltan)
            nueva = self.texto(linea, "toml")
            if self.faltan != antes:
                quitadas.append(linea.split("#")[0].strip())
                self.faltan = antes
                continue
            lineas.append(nueva)
        return "".join(lineas), quitadas


def _escribir(ruta, texto):
    """Solo escribe si cambia: asi no se recompila lo que no ha cambiado."""
    ruta = pathlib.Path(ruta)
    if ruta.is_file() and _leer(ruta) == texto:
        return False
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="") as fh:
        fh.write(texto)
    return True


def _cabecera(tipo, edicion, origen):
    marca = "#" if tipo == "toml" else "//"
    return ("%s GENERADO por tools/ediciones/ediciones.py para la edicion '%s'. NO EDITAR:\n"
            "%s se rehace a partir de %s.\n"
            "%s Las direcciones del codigo son las de esta edicion; las de los comentarios\n"
            "%s siguen siendo las de la edicion de referencia.\n\n"
            % (marca, edicion, marca, origen, marca, marca))


def aplicar(edicion, salida, xex="../assets/game_root/default.xex"):
    """
    Deja en `salida` lo que el codegen necesita para esa edicion: overrides.toml
    y huecos.toml traducidos y un manifiesto que los incluye. Devuelve la ruta
    del manifiesto. `xex` es la ruta del XEX relativa a la carpeta del manifiesto.
    """
    salida = pathlib.Path(salida)
    t = Traductor(edicion)
    for rel in CODEGEN:
        origen = _leer(RAIZ / rel)
        nombre = pathlib.Path(rel).name
        if nombre == "huecos.toml":
            texto, quitadas = t.huecos(origen)
            extra = AQUI / edicion / "huecos.toml"
            if extra.is_file():
                texto += "\n# --- Solo de la edicion '%s' (tools/ediciones/%s/huecos.toml) ---\n" % (edicion, edicion)
                texto += "".join(l for l in extra.read_text(encoding="utf-8").splitlines(True)
                                 if l.strip() and not l.lstrip().startswith(("#", "[")))
            if quitadas:
                print("     huecos.toml: %d declaraciones sin sitio seguro en '%s', quitadas: %s"
                      % (len(quitadas), edicion, "; ".join(quitadas)))
        else:
            texto = t.texto(origen, "toml")
        _escribir(salida / nombre, _cabecera("toml", edicion, rel) + texto)
    if t.faltan:
        fallar("Direcciones sin traduccion segura a '%s': %s.\n"
               "        Rehaz la tabla (ediciones.py mapa) o corrigelas en tools/ediciones/%s/correcciones.json."
               % (edicion, ", ".join(sorted(t.faltan)), edicion))

    # El manifiesto: mismas rutas, vistas desde la carpeta de salida.
    app = (RAIZ / MANIFIESTO).parent  # the folder the manifest's paths are relative to
    def desde_salida(relativa_a_app):
        return os.path.relpath(app / relativa_a_app, salida).replace(os.sep, "/")
    manifiesto = _leer(RAIZ / MANIFIESTO)
    cambios = [
        ('game_root = "../assets/game_root"', 'game_root = "%s"' % desde_salida(os.path.dirname(xex))),
        ('file_path = "../assets/game_root/default.xex"', 'file_path = "%s"' % desde_salida(xex)),
        ('out_directory_path = "generated-android/default"',
         'out_directory_path = "%s"' % os.path.relpath(salida.parent / "default", salida).replace(os.sep, "/")),
    ]
    for viejo, nuevo in cambios:
        if manifiesto.count(viejo) != 1:
            fallar("%s: no encuentro la linea  %s" % (MANIFIESTO, viejo))
        manifiesto = manifiesto.replace(viejo, nuevo)
    destino = salida / pathlib.Path(MANIFIESTO).name
    _escribir(destino, _cabecera("toml", edicion, MANIFIESTO) + manifiesto)
    return destino


def fuentes(edicion, salida, ficheros):
    """Traduce ficheros de C++ a `salida`, con el mismo nombre. Lo llama CMake."""
    salida = pathlib.Path(salida)
    t = Traductor(edicion)
    for fichero in ficheros:
        origen = pathlib.Path(fichero)
        try:
            rel = origen.resolve().relative_to(RAIZ).as_posix()
        except ValueError:
            rel = origen.name
        texto = t.texto(_leer(origen), "cpp")
        # Siempre se escribe, aunque no cambie: CMake decide por la fecha si
        # esta copia esta al dia con su original.
        salida.mkdir(parents=True, exist_ok=True)
        with open(salida / origen.name, "w", encoding="utf-8", newline="") as fh:
            fh.write(_cabecera("cpp", edicion, rel) + texto)
    if t.faltan:
        fallar("Direcciones sin traduccion segura a '%s': %s.\n"
               "        Si son nuevas en el proyecto hay que rehacer la tabla, y eso pide los dos XEX:\n"
               "        python tools/ediciones/ediciones.py mapa %s <referencia.xex> <otra.xex>"
               % (edicion, ", ".join(sorted(t.faltan)), edicion))


# ---------------------------------------------------------------------------
# mapa: hacer la tabla de una edicion (necesita los dos XEX)
# ---------------------------------------------------------------------------

def mapa(edicion, xex_ref, xex_otra):
    import emparejar
    img_a, _ = imagen.cargar(xex_ref, str(CACHE))
    img_b, sha_b = imagen.cargar(xex_otra, str(CACHE))
    emp = emparejar.Emparejador(img_a, img_b)
    print("anclas en .text: %d (de %d instrucciones)" % (len(emp.cadena), len(emp.na) // 4))

    correcciones = {}
    ruta_correcciones = AQUI / edicion / "correcciones.json"
    if ruta_correcciones.is_file():
        with open(ruta_correcciones, encoding="utf-8") as fh:
            correcciones = {int(k, 16): int(v, 16) for k, v in json.load(fh).get("direcciones", {}).items()}

    usadas = direcciones_del_proyecto()
    filas, cuenta, dudosas = [], {}, []
    for (d, uso) in sorted(usadas):
        if uso == "fin":
            # El final de una funcion: lo que sigue a su ultima instruccion. Se
            # comprueba con las 16 instrucciones de ANTES, que son suyas; las de
            # despues son de la funcion siguiente y pueden haber cambiado.
            for atras in (4 * emparejar.VERIFICAR, 4):
                seccion, destino, estado = emp.traducir(d - atras)
                destino = destino + atras if destino is not None else None
                if estado.startswith("exacta"):
                    break
        else:
            seccion, destino, estado = emp.traducir(d)
        if d in correcciones:
            destino, estado = correcciones[d], "a mano"
        huella = emp.huella(destino) if destino is not None and uso == "dir" else "-"
        clave = "%s %s" % (seccion, estado.split(" (")[0])
        cuenta[clave] = cuenta.get(clave, 0) + 1
        if not estado.startswith(SEGUROS):
            dudosas.append("%08X %s -> %s, %s  [%s]" % (d, uso, "%08X" % destino if destino else "-",
                                                         estado, ", ".join(sorted(set(usadas[(d, uso)])))))
        filas.append("%08X\t%s\t%s\t%s\t%s\t%s" % (d, uso, seccion, "%08X" % destino if destino is not None else "-",
                                                    estado, huella))

    # Las funciones que se enganchan desde C++ dependen de los campos de las
    # estructuras: se comparan enteras, sin normalizar.
    distintas = 0
    cpp = {p.relative_to(RAIZ).as_posix() for p in fuentes_cpp()}
    vistas = set()
    for (d, uso), ficheros in sorted(usadas.items()):
        if uso != "dir" or not cpp & set(ficheros) or not emp.ta[1] <= d < emp.ta[2]:
            continue
        ini, fin = emp.funcion_de(d)
        if ini in vistas:
            continue
        vistas.add(ini)
        problemas = emp.comparar_funcion(d)
        if problemas:
            distintas += 1
            print("  FUNCION DISTINTA %08X..%08X (gancho en %08X): %s" % (ini, fin, d, "; ".join(problemas[:6])))

    destino_tabla = ruta_tabla(edicion)
    destino_tabla.parent.mkdir(parents=True, exist_ok=True)
    with open(destino_tabla, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("ref\tuso\tseccion\totra\testado\thuella\n" + "\n".join(filas) + "\n")
    for k, v in sorted(cuenta.items()):
        print("  %-40s %d" % (k, v))
    for linea in dudosas:
        print("  DUDOSA " + linea)
    print("funciones con gancho comparadas enteras: %d, distintas: %d" % (len(vistas), distintas))
    print("[ok] %s: %d direcciones, %d dudosas" % (destino_tabla.relative_to(RAIZ), len(filas), len(dudosas)))
    print("     XEX de la edicion: sha256 %s, PDB %s" % (sha_b, _pdb(img_b)))
    return 1 if distintas else 0


# ---------------------------------------------------------------------------

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    orden, resto = args[0], args[1:]
    if orden == "detectar":
        ficha = detectar(resto[0] if resto else str(RAIZ / "assets" / "game_root" / "default.xex"))
        print(json.dumps(ficha, ensure_ascii=False, indent=2))
    elif orden == "aplicar" and len(resto) == 2:
        print("[ok] %s" % aplicar(resto[0], resto[1]))
    elif orden == "fuentes" and len(resto) >= 3:
        fuentes(resto[0], resto[1], resto[2:])
    elif orden == "mapa" and len(resto) == 3:
        return mapa(*resto)
    else:
        sys.exit(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
