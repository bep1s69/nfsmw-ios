"""
The game edition of the generated code, for the patch_game_*.py scripts.

Those scripts are written with USA addresses. The PAL Europe edition gets the
same edits: usa() moves the addresses in a piece of text to the edition the
code was generated for (ios/generated/edicion.json, from generate_code.py),
with tools/ediciones/<edition>/desde_usa.tsv. For USA it changes nothing.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "ediciones"))
import ediciones  # noqa: E402

_INFO = ROOT / "ios" / "generated" / "edicion.json"
if not _INFO.is_file():
    sys.exit(f"[ERROR] {_INFO} is missing. Run tools/ios/generate_code.py first.")
EDITION = json.loads(_INFO.read_text(encoding="utf-8"))["tabla"]
_TABLE = None if EDITION == "usa" else ediciones.cargar_tabla(EDITION, "usa")


def usa(text):
    """text with its USA addresses (82xxxxxx) in this edition's."""
    if _TABLE is None:
        return text

    def move(m):
        dest, state, _ = _TABLE.get((int(m.group(), 16), "dir"), (None, "not in the table", "-"))
        if dest is None or not state.startswith(ediciones.SEGUROS):
            sys.exit(f"[ERROR] USA {m.group()} has no safe '{EDITION}' address in "
                     f"{ediciones.ruta_tabla(EDITION, 'usa').relative_to(ROOT)} ({state})")
        new = "%08X" % dest
        return new.lower() if any(c in "abcdef" for c in m.group()) else new
    return ediciones.DIRECCION.sub(move, text)
