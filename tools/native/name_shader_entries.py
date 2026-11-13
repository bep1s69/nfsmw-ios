#!/usr/bin/env python3
"""Give translated Metal entry points stable material names for GPU profiling.

Run after shader rewrites. Only entry identifiers change; shaderBody, interfaces,
constants and specialization bits are untouched. Generated sources stay private.
"""
from pathlib import Path
import re
import sys


def rename(text, material):
    if not re.fullmatch(r"[pv]s_[0-9a-f]{16}(?:_dbg[0-9]+)?", material):
        raise ValueError("expected a shader material key")
    names = {"shaderMain": "nfsmw_" + material,
             "shaderMainMotion": "nfsmw_" + material + "_motion"}
    identifier = re.compile(r"\b(shaderMainMotion|shaderMain)(?=\s*\()")
    named_base = re.compile(r"\b" + names["shaderMain"] + r"\s*\(")
    old = list(identifier.finditer(text))
    if not old:
        if not named_base.search(text):
            raise ValueError("missing expected base shader entry point")
        return text  # idempotent
    if named_base.search(text) or not any(m[1] == "shaderMain" for m in old):
        raise ValueError("mixed or incomplete shader entry naming")
    result = identifier.sub(lambda m: names[m[1]], text)
    # Mechanical identifier substitution must be exactly reversible.
    restored = re.sub(r"\b(" + "|".join(map(re.escape, reversed(list(names.values()))))
                      + r")(?=\s*\()", lambda m: {v: k for k, v in names.items()}[m[1]], result)
    if restored != text:
        raise ValueError("entry renaming changed unrelated source")
    return result


def main():
    for arg in sys.argv[1:]:
        path = Path(arg)
        text = path.read_text()
        result = rename(text, path.stem)
        if result != text:
            path.write_text(result)
        print(f"{path.name}: material entry names ready")


if __name__ == "__main__":
    main()
