#!/usr/bin/env python3
"""The shadow-map caster shader (ps 4fbaecfb) without its unused cut-out.

The shader cuts out see-through casters when the float constant
g_bShadowMapAlphaEnabled (c1.x) is not 0. Most casters draw with it at 0, but
the discard stays reachable, which keeps the GPU from removing hidden caster
pixels early. This puts the test behind specialization bit 12
(SPEC_CONSTANT_NO_SHADOW_ALPHA in the renderer): with the bit set the branch is
compiled out; the renderer sets it only for draws whose c1.x is 0, where the
branch is never taken, so the shadow map is the same.

    rewrite_shadow_caster_alpha.py FILE.hlsl [...]   (in place; prints a count)
"""
import sys

OLD = "\tp0 = g_bShadowMapAlphaEnabled.x != 0.0;\n"
NEW = "\tp0 = ((g_SpecConstants() & 0x1000u) == 0u) && (g_bShadowMapAlphaEnabled.x != 0.0);\n"

for path in sys.argv[1:]:
    text = open(path).read()
    n = text.count(OLD) if "ps_4fbaecfb8e7c4f40" in path else 0
    if n == 1:
        open(path, "w").write(text.replace(OLD, NEW))
    print(f"{path}: {n if n == 1 else 0} shadow caster cut-out(s) made specializable")
