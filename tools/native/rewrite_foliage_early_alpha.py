#!/usr/bin/env python3
"""Opt-in early alpha rejection for the shadowed cutout shader only.

Run after rewrite_shadow_filter.py. Specialization bit 13 is selected by
nfsmw_native_foliage_early_alpha (default false). Keep the original late path
when unset, and preserve surviving outputs, compare predicates and derivatives:
discard only, with no early return or early_fragment_tests attribute.

The body digest is an intentional fail-closed dataflow guard. If translation
changes, re-audit all alpha sources/writes and control flow before updating it.
Game-derived source is never embedded here.
"""
import hashlib
from pathlib import Path
import re
import sys

TARGET = "ps_684f4711f29b9f77"
BODY_SHA256 = "7d22a9278b1b15fd973c194464aee0237c2aa6b7f3351ef664a9eb9f585e1c66"
MARKER = "// NFSMW foliage early alpha: specialization bit 13"
BIT = "(g_SpecConstants() & 0x2000u)"


def rewrite(text, name):
    if Path(name).stem != TARGET:
        return text, 0
    if MARKER in text:
        raise ValueError("early-alpha rewrite already applied; regenerate baseline first")
    start = text.index("\n{\n#ifdef __air__\n\tPixelShaderOutput output")
    end = text.index("\n\treturn output;", start)
    body = text[start:end]
    if hashlib.sha256(body.encode()).hexdigest() != BODY_SHA256:
        raise ValueError("target shader body changed; re-audit alpha dataflow before rewriting")
    alpha = re.search(r"\toutput\.oC0\.w = (?P<expr>[^;\n]+);\n", body)
    test = re.search(r"\tBRANCH if \(g_SpecConstants\(\) & SPEC_CONSTANT_ALPHA_TEST\)\n"
                     r"\t\{\n.*?\n\t\}", body, re.S)
    fetch = re.search(r"\tr9\.xyzw = tfetch2D\(.*?\)\.xyzw;\n", body, re.S)
    if not alpha or not test or not fetch or not fetch.end() < alpha.start() < test.start():
        raise ValueError("expected diffuse fetch / final opacity / alpha test missing")
    # Copy the actual generated predicate (including its explicit NaN rule),
    # rather than maintaining a second independently written comparison table.
    early = test.group().replace(
        "BRANCH if (g_SpecConstants() & SPEC_CONSTANT_ALPHA_TEST)",
        f"BRANCH if ({BIT} && (g_SpecConstants() & SPEC_CONSTANT_ALPHA_TEST))"
    ).replace("output.oC0.w", "nfsmwEarlyAlpha")
    early = early.replace("\t{\n", "\t{\n\t\tfloat nfsmwEarlyAlpha = " + alpha["expr"] + ";\n", 1)
    late = test.group().replace(
        "BRANCH if (g_SpecConstants() & SPEC_CONSTANT_ALPHA_TEST)",
        f"BRANCH if (!{BIT} && (g_SpecConstants() & SPEC_CONSTANT_ALPHA_TEST))")
    body = body[:test.start()] + late + body[test.end():]
    body = body[:fetch.end()] + "\t" + MARKER + "\n" + early + "\n" + body[fetch.end():]
    return text[:start] + body + text[end:], 1


def main():
    for arg in sys.argv[1:]:
        path = Path(arg)
        text = path.read_text()
        new, count = rewrite(text, path.name)
        if count:
            path.write_text(new)
        print(f"{path}: {count} foliage early-alpha block(s) made specializable")


if __name__ == "__main__":
    main()
