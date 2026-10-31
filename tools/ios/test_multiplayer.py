#!/usr/bin/env python3
"""Host checks for the copied LAN lobby, SDK patch, USA hook and socket adaptation.
No game assets or phone connectivity claims; compiles/runs actual implementation.
"""
import argparse
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--sdk', type=Path, required=True)
p.add_argument('--reference-server', type=Path, required=True)
a = p.parse_args()


def run(*args, **kw):
    return subprocess.run(*args, check=True, **kw)


def patch_check(tmp):
    # The canonical shared SDK is read-only for this check, even when patched SDK
    # is supplied for compiling the host server.
    source = Path.home() / 'Developer/GitHub/rexglue-sdk-ios'
    names = ['src/kernel/xam/xam_net.cpp', 'src/system/xsocket.cpp',
             'src/kernel/xam/apps/xgi_app.cpp', 'src/kernel/xam/apps/xlivebase_app.cpp',
             'src/kernel/xam/xam_user.cpp', 'src/kernel/xam/xam_misc.cpp', 'include/rex/system/xsocket.h']
    fixture = tmp / 'sdk'
    original = {}
    for name in names:
        original[name] = (source / name).read_bytes()
        target = fixture / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(original[name])
    env = dict(os.environ, NFSMW_SDK=str(fixture))
    script = ROOT / 'tools/ios/patch_ios_multiplayer.py'
    for options in [[], [], ['--status'], ['--revert'], ['--revert']]:
        run(['python3', str(script), *options], env=env)
    assert all((fixture / n).read_bytes() == b for n, b in original.items())
    # Whole patch must reject a changed anchor without partial mutation.
    changed = fixture / names[0]
    changed.write_text(changed.read_text().replace('  // Just return a loopback address atm.', '  // changed input fixture'))
    saved = {n: (fixture / n).read_bytes() for n in names}
    result = subprocess.run(['python3', str(script)], env=env, capture_output=True)
    assert result.returncode != 0
    assert all((fixture / n).read_bytes() == b for n, b in saved.items())
    print('SDK patch: apply/idempotency/revert/atomic rejection passed')


def compile_server(tmp):
    harness = tmp / 'server.cpp'
    harness.write_text('''#include "servidor_ea.h"
#include <iostream>
int main(int argc,char**argv) {
 std::string error;
 if(!nfsmw::servidor::Arrancar(argv[1],argv[2],[]{},[]{return std::string("test");},&error)) {
  std::cerr<<error;return 1;
 }
 std::cout<<"ready"<<std::endl;
 std::string line;std::getline(std::cin,line);
 nfsmw::servidor::Parar();
}
''')
    dest = tmp / 'server'
    run(['clang++', '-std=c++23', '-O1', '-pthread',
         '-I' + str(ROOT / 'ios/src/multiplayer'),
         '-I' + str(a.sdk / 'thirdparty/inja/third_party/include'),
         str(ROOT / 'ios/src/multiplayer/servidor_ea.cpp'),
         str(ROOT / 'ios/src/multiplayer/red_lan.cpp'), str(harness), '-o', str(dest)])
    return dest


class Client:
    def __init__(self, port):
        self.s = socket.create_connection(('127.0.0.1', port), timeout=3)
        self.s.settimeout(.12)
        self.buf = b''
    def ask(self, cmd, **fields):
        body = ''.join(str(k)+'='+str(v)+'\n' for k,v in fields.items()).encode('latin1') + b'\0'
        self.s.sendall(cmd.encode() + b'\0'*4 + struct.pack('>I', 12+len(body)) + body)
        return self.read()
    def read(self):
        out = []
        while True:
            try:
                data = self.s.recv(65536)
            except socket.timeout:
                break
            if not data: break
            self.buf += data
            while len(self.buf) >= 12:
                n = int.from_bytes(self.buf[8:12], 'big')
                assert 12 <= n <= 1024*1024
                if len(self.buf) < n: break
                packet,self.buf = self.buf[:n],self.buf[n:]
                fields = dict(line.split('=',1) for line in packet[12:].rstrip(b'\0').decode('latin1').split('\n') if '=' in line)
                # Only startup-dependent values are normalized; all fields compared.
                for key in ['MASK','LKEY','SEED','WHEN','REF','LGAME']:
                    if key in fields: fields[key] = '<variable>'
                if packet[:4] == b'@dir' and 'SESS' in fields: fields['SESS'] = '<variable>'
                out.append((packet[:8],fields))
        return out
    def close(self): self.s.close()


def scenario():
    # Synthetic two-player lobby flow. Same source IP on macOS so no extra
    # loopback aliases required; unique names and MADDR still verify protocol.
    trace=[]
    binary7 = ''.join(chr(i) for i in range(128,256))
    session = '$' + binary7
    d=Client(30960); trace += [('directory', d.ask('@dir',PROD='nfs-xbox-2006'))]; d.close()
    x,y=Client(10901),Client(10901)
    try:
        for c,name in [(x,'iPhone'),(y,'Android')]:
            for cmd,fields in [('skey',{}),('auth',dict(NAME=name,MADDR='$'+name+'^'+binary7)),('pers',dict(PERS=name)),('sele',dict(MYGAME=1,USERSETS=1)),('auxi',dict(TEXT='SCF%3d0%0aV%3d0%0a'))]:
                trace.append((name+cmd,c.ask(cmd,**fields)))
        trace.append(('room',x.ask('ucre',NAME='lan-test',TYPE=0,SIZE=4,PARAMS='M=2')))
        trace.append(('game',x.ask('gcre',NAME='lan-test',MINSIZE=2,MAXSIZE=4,PARAMS='M=2',PLATPARAMS=binary7)))
        trace.append(('session',x.ask('gset',SESS=session)))
        trace.append(('browse',y.ask('usea')))
        trace.append(('subscribe',y.ask('sele',USERSET0='lan-test')))
        trace.append(('joinroom',y.ask('ujoi',NAME='lan-test')))
        joined=y.ask('gjoi',NAME='lan-test')
        record=next(f for cmd,f in joined if cmd[:4]==b'gjoi')
        assert record['SESS']==session and record['PLATPARAMS']==binary7
        assert record['MADDR0']=='$iPhone^'+binary7 and record['MADDR1']=='$Android^'+binary7
        trace.append(('joingame',joined))
        trace.append(('hostupdates',x.read()))
        trace.append(('start',x.ask('gsta')))
        trace.append(('peerstart',y.read()))
        trace.append(('leave',y.ask('glea')))
        trace.append(('hostleave',x.read()))
        trace.append(('delete',x.ask('gdel')))
        trace.append(('leaveroom',x.ask('ulea')))
        with socket.create_connection(('127.0.0.1',10902),timeout=3) as c:
            c.sendall(b'GAMERTAG AvailableName\n'); assert c.recv(128).strip() == b'FREE'
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as c:
            c.settimeout(3); c.sendto(b'NFSMW_DISCOVER',('127.0.0.1',10902))
            reply=c.recv(1024).decode(); assert reply.startswith('NFSMW_SERVER\n') and 'PLAYERS=' in reply
    finally: x.close(); y.close()
    return trace


def start(cmd, cwd, tmp):
    log=open(tmp,'wb')
    proc=subprocess.Popen(cmd,cwd=cwd,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT)
    deadline=time.monotonic()+6
    while time.monotonic()<deadline:
        if proc.poll() is not None: raise AssertionError(Path(tmp).read_text())
        try:
            with socket.create_connection(('127.0.0.1',10901),timeout=.1): return proc,log
        except OSError: time.sleep(.05)
    raise AssertionError('server startup timeout')


def stop(proc, log):
    proc.communicate(b'\n',timeout=5) if proc.args[0] != 'python3' else proc.terminate()
    proc.wait(timeout=5);log.close();time.sleep(.15)


with tempfile.TemporaryDirectory(prefix='nfsmw-lan-test-') as path:
    tmp=Path(path)
    patch_check(tmp)
    server=compile_server(tmp)
    data,logs=tmp/'data',tmp/'logs';data.mkdir();logs.mkdir()
    proc,log=start([str(server),str(data),str(logs)],tmp,tmp/'cpp.log')
    try: actual=scenario()
    finally: stop(proc,log)
    ref=tmp/'reference';ref.mkdir()
    shutil.copy(a.reference_server/'ea_server.py',ref/'ea_server.py')
    proc,log=start(['python3','ea_server.py','--ip','127.0.0.1','--log',str(ref/'server.log'),'--name','test'],ref,tmp/'python.log')
    try: expected=scenario()
    finally: stop(proc,log)
    for (step,left),(step2,right) in zip(actual,expected):
        assert step==step2
        assert left==right,(step,left,right)
    assert len(actual)==len(expected)
    assert any(cmd[:4]==b'gjoi' and f.get('COUNT')=='2' for step,msg in actual for cmd,f in msg)
    assert any(cmd[:4]==b'+ses' for step,msg in actual for cmd,f in msg)
    print('Lobby: C++ vs unmodified Python parity,',len(actual),'two-player stages; binary7 session/address preservation, create/join/start/leave, gamertag and discovery passed')
