#!/usr/bin/env python3
"""Observe the USA engine accumulator without altering any PPC register.

Exact anchors are validated before writing. Repartitioning generated files is
allowed; a changed/partial function body is rejected. Runtime logging uses the
existing default-off nfsmw_frame_ticks_log switch.
"""
import argparse
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
MARK = "nfsmw-world-step-trace"
HEAD = "DEFINE_REX_FUNC(sub_823C6500) {"
DECL = ('extern "C" void nfsmw_world_step_trace(double, double, double, double, '
        'double, int32_t, uint32_t, uint32_t, uint32_t); // ' + MARK + '\n')
LOCALS = ('\tconst double nfsmw_step_input = ctx.f1.f64; // ' + MARK + '\n'
          '\tdouble nfsmw_step_before = -1, nfsmw_step_limit = -1, nfsmw_step_after = -1; // ' + MARK + '\n'
          '\tconst uint32_t nfsmw_step_flag = REX_LOAD_U32(0x828FD868); // ' + MARK + '\n'
          '\tconst uint32_t nfsmw_step_budget = REX_LOAD_U32(0x828FD87C); // ' + MARK + '\n'
          '\tconst uint32_t nfsmw_step_caller = uint32_t(ctx.lr); // ' + MARK + '\n')
SITES = [
    ('\tREX_FUNC_PROLOGUE();\n', LOCALS),
    ('\tctx.f0.f64 = double(float(ctx.f0.f64 + ctx.f1.f64));\n',
     '\tnfsmw_step_before = ctx.f0.f64; // ' + MARK + '\n'),
    ('\tctx.f13.f64 = double(float(ctx.f13.f64 * ctx.f12.f64));\n',
     '\tnfsmw_step_limit = ctx.f13.f64; // ' + MARK + '\n'),
    ('loc_823C65D8:\n', '\tnfsmw_step_after = ctx.f0.f64; // ' + MARK + '\n'),
    ('\tREX_STORE_U32(ctx.r11.u32 + -27040, temp.u32);\n',
     '\tnfsmw_world_step_trace(nfsmw_step_input, nfsmw_step_before, nfsmw_step_limit, '
     'nfsmw_step_after, ctx.f0.f64, ctx.r30.s32, nfsmw_step_flag, nfsmw_step_budget, nfsmw_step_caller); // ' + MARK + '\n'),
]


def transform(text, revert=False):
    original = text
    if MARK in text:
        for addition in [DECL] + [addition for _, addition in SITES]:
            if text.count(addition) != 1:
                raise ValueError("partial or modified world-step trace patch")
            text = text.replace(addition, '', 1)
    start = text.index(HEAD)
    end = text.find('\nDEFINE_REX_FUNC(', start + len(HEAD))
    end = len(text) if end < 0 else end
    body = text[start:end]
    for anchor, _ in SITES:
        if body.count(anchor) != 1:
            raise ValueError(f"world-step trace anchor missing/ambiguous: {anchor.strip()}")
    if revert:
        return text
    for anchor, addition in SITES:
        body = body.replace(anchor, anchor + addition, 1)
    result = text[:start] + body + text[end:]
    result = result.replace(HEAD, DECL + HEAD, 1)
    if MARK in original and result != original:
        raise ValueError("modified world-step trace placement")
    return result


def apply(directory, revert=False, status=False):
    matches = [p for p in directory.glob('*.cpp') if HEAD in p.read_text()]
    if len(matches) != 1:
        raise ValueError(f"expected one {HEAD}, found {len(matches)}")
    path = matches[0]
    text = path.read_text()
    result = transform(text, revert)
    if not status and result != text:
        path.write_text(result)
    print(f"[world-step-trace] {path.name}: " +
          (('applied' if MARK in text else 'not applied') if status else
           ('reverted' if revert else 'applied')))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dir', type=pathlib.Path, default=ROOT / 'ios/generated/default')
    parser.add_argument('--revert', action='store_true')
    parser.add_argument('--status', action='store_true')
    args = parser.parse_args()
    apply(args.dir, args.revert, args.status)
