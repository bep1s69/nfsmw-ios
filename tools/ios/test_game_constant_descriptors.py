#!/usr/bin/env python3
"""Production patch differential, rollback, sampled counters and OFF/ON cost."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile
import patch_game_constant_descriptors as patch
import patch_game_constant_copies as copies

sys.path.insert(0,str(patch.ROOT/'tools/native'))
import test_constant_descriptor_run as gate


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--benchmark',action='store_true')
    args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    paths=[p for p in patch.GENERATED.glob('*.cpp') if 'DEFINE_REX_FUNC(sub_82699100) {' in p.read_text()]
    assert len(paths)==1
    current=patch.original_text(paths[0].read_text())
    original=copies.original_text(current);assert copies.transform(original)==current
    installed=patch.transform(current);assert patch.original_text(installed)==current
    with tempfile.TemporaryDirectory(prefix='nfsmw-descriptor-patch-') as folder:
        folder=Path(folder);file=folder/'sample.cpp';file.write_text(current)
        command=[sys.executable,str(Path(patch.__file__)), '--dir',str(folder)]
        for options in [[],[],['--status'],['--revert'],['--revert'],[]]:
            subprocess.run(command+options,check=True,capture_output=True)
        assert file.read_text()==installed
        # Coexistence with the old patch's status/apply normalization.
        assert copies.transform(copies.original_text(installed))==installed
        for damaged in [current.replace('loc_826991D8:', 'loc_changed:',1),
                        current.replace('loc_8269933C:\n','loc_8269933C:\n\t// changed full body\n',1),
                        installed.replace('loc_826991D8_runs_fallback:;', 'loc_bad:;',1),
                        installed.replace(patch.REPORT,'',1)]:
            file.write_text(damaged);before=file.read_bytes()
            assert subprocess.run(command,capture_output=True).returncode!=0
            assert file.read_bytes()==before
    print('PASS production patch apply/idempotence/status/revert, old patch coexistence and atomic rejection',flush=True)
    refs=[]
    for label,(name,_) in gate.SITES.items():
        for arm,source in [('Original',original),('Current',current),('IntegratedOff',installed),('IntegratedOn',installed)]:
            a=source.index(f'loc_{label}:\n')
            if arm.startswith('Integrated'):
                end=f'loc_{label}_runs_done:; // {patch.MARK}\n'
                b=source.index(end,a)+len(end);prefix=patch.LOCAL;suffix=patch.REPORT
            else:
                end=f'\tif (cr6.lt) goto loc_{label};\n';b=source.index(end,a)+len(end);prefix=suffix=''
            refs.append(f'__attribute__((noinline)) void {arm}{name}(PPCContext& ctx,uint8_t* base,PPCCRRegister& cr6,uint32_t& ea,PPCRegister& temp) {{\nconst bool native_constant_copies=true;\n{prefix}{source[a:b]}{suffix}\n}}')
    harness=gate.HARNESS.replace('three-arm full-loop comparisons','five-arm full-loop comparisons (original/current/core/OFF/ON)')
    stub='''
static bool trial_flag=false;
__attribute__((noinline)) bool& FLAGS_nfsmw_native_descriptor_runs_storage_(){return trial_flag;}
static nfsmw::constants::descriptors::Counts last_report{};
static unsigned reports=0;
namespace nfsmw::constants::descriptors {void Report(const Counts& c){last_report=c;++reports;}}
'''
    harness=harness.replace('@REFERENCES@',stub+'\n'+'\n'.join(refs))
    anchor='template<bool Pixel,int Arm> __attribute__((noinline)) static void Invoke(State& s) {\n'
    dispatch='''  if constexpr(Arm==3) {
    if constexpr(Pixel)IntegratedOffPixel(s.ctx,s.memory.data(),s.cr,s.ea,s.temp);
    else IntegratedOffVertex(s.ctx,s.memory.data(),s.cr,s.ea,s.temp);
    return;
  }
  if constexpr(Arm==4) {
    if constexpr(Pixel)IntegratedOnPixel(s.ctx,s.memory.data(),s.cr,s.ea,s.temp);
    else IntegratedOnVertex(s.ctx,s.memory.data(),s.cr,s.ea,s.temp);
    return;
  }
'''
    harness=harness.replace(anchor,anchor+dispatch)
    anchor='  Same(a,b);Same(b,c);\n'
    check='''  State off=seed,on=seed;
  trial_flag=false;reports=0;nfsmw::constants::descriptors::sample_sequence.store(0);
  inject();Invoke<Pixel,3>(off);Same(b,off);
  assert(reports==0 && nfsmw::constants::descriptors::sample_sequence.load()==0);
  trial_flag=true;reports=0;nfsmw::constants::descriptors::sample_sequence.store(0);
  inject();Invoke<Pixel,4>(on);Same(b,on);
  assert(reports==1);
  const auto& count=last_report.stage[Pixel?1:0];
  // In particular: a late refusal must not retry admission on each remaining
  // fallback backedge. The entire current suffix remains unchanged.
  assert(count.attempts==1 && count.complete+count.partial+count.refused==1);
  if(expected==1)assert(count.complete==1 && count.fallback==0);
  if(expected==0)assert(count.refused==1 && count.native==0);
'''
    harness=harness.replace(anchor,anchor+check)
    # Costs: CURRENT / actual installed OFF / actual installed ON. Include
    # static-flag admission, sampling and Observe; host Report is a counter stub.
    at=harness.index('template<bool Pixel,int Arm> static uint64_t Bench(')
    before,after=harness[:at],harness[at:]
    after=after.replace('    Invoke<Pixel,Arm>(s);','''    if constexpr(Arm==0)Invoke<Pixel,1>(s);
    else if constexpr(Arm==1)Invoke<Pixel,3>(s);
    else Invoke<Pixel,4>(s);''')
    after=after.replace('original=%.3f current=%.3f candidate=%.3f','current=%.3f off=%.3f on=%.3f')
    harness=before+after
    source=args.output/'production-fixture.cpp'
    source.write_text(harness.replace('@HEADER@',str(patch.ROOT/'tools/native/constant_descriptor_candidate.h')))
    exe=args.output/('production-benchmark' if args.benchmark else 'production-sanitized')
    sdk=patch.ROOT.parent/'rexglue-sdk-ios'
    flags=['-O2'] if args.benchmark else ['-O1','-DINJECT_STORES','-fsanitize=address,undefined','-fno-omit-frame-pointer']
    subprocess.run(['xcrun','clang++','-std=c++23','-Wno-asm-operand-widths',*flags,
                    '-I',str(sdk/'include'),'-I',str(sdk/'thirdparty/simde'),str(source),'-o',str(exe)],check=True)
    subprocess.run([str(exe)]+(['benchmark'] if args.benchmark else []),check=True)


if __name__=='__main__':main()
