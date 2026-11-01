#!/usr/bin/env python3
"""Actual PC-host backend/announcements with synthetic clients, not a PC game.
Pass this Mac's current LAN IPv4 with --ip; listeners run only during the test.
"""
import argparse
from pathlib import Path
import socket, struct, subprocess, tempfile, time
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--sdk',type=Path,required=True)
p.add_argument('--ip',required=True)
a=p.parse_args()
root=Path(__file__).resolve().parents[2]
code=r'''
#include "servidor_ea.h"
#include "pc_gateway.h"
#include <cassert>
#include <iostream>
#include <thread>
using namespace nfsmw::pc;
int main(int argc,char**argv) {
 auto room="D=$00090000c0a801cd\nP=V%3d192641%0aM%3d2%0a";
 auto reply=HostReply("+uss",room,"192.168.1.205");
 assert(Field(reply,"D")=="$cd01a8c0" && Field(reply,"P")=="V%3d192359%0aM%3d2%0a");
 assert(Field(HostReply("+uss","P=V%3d999999%0a","192.168.1.205"),"P")=="V%3d999999%0a");
 auto login=HostLogin("NAME=PC\nMADDR=$ca01a8c0","192.168.1.202");
 assert(Field(login,"MADDR").starts_with("$00090000c0a801ca^"));
 auto game="HOST=Phone\nIDENT=5\nADDR0=192.168.1.205\nMADDR0=$00090000c0a801cd^binary\nSESS=$binary\nPLATPARAMS=binary";
 auto wire=HostReply("+ses",game,"192.168.1.205");
 assert(Field(wire,"MADDR0")=="$cd01a8c0" && Field(wire,"SESS").empty());
 assert(Field(game,"SESS")=="$binary");
 StartHosting(); assert(Hosting() && !Active());
 assert(SetHostingPeer(0xc0a801ca) && !SetHostingPeer(0xc0a801cb));
 ObserveRaceId(0xc0a801ca,0);assert(HasRaceId(0xc0a801ca));
 Stop();assert(!Hosting() && !Active() && !HasRaceId(0xc0a801ca));
 StartHosting();std::string error;
 if(!nfsmw::servidor::ArrancarPC(argv[1],argv[1],[]{},[]{return std::string("PhoneHostLongName");},argv[2],&error)) {
  std::cerr<<error;return 1;
 }
 std::cout<<"ready"<<std::endl;
 std::string line;std::getline(std::cin,line);
 nfsmw::servidor::Parar();Stop();
 // Existing server listener threads retire at their next500ms poll.
 std::this_thread::sleep_for(std::chrono::milliseconds(600));
}
'''
class Client:
 def __init__(self,port):
  self.s=socket.create_connection((a.ip,port),timeout=3);self.s.settimeout(.1);self.buf=b''
 def ask(self,cmd,**fields):
  body=(''.join(k+'='+v+'\n' for k,v in fields.items())+'\0').encode('latin1')
  self.s.sendall(cmd.encode()+b'\0'*4+struct.pack('>I',12+len(body))+body)
  return self.read()
 def read(self):
  out=[]
  while True:
   try:data=self.s.recv(65536)
   except socket.timeout:break
   if not data:break
   self.buf+=data
   while len(self.buf)>=12:
    n=int.from_bytes(self.buf[8:12],'big');assert 12<=n<=1048576
    if len(self.buf)<n:break
    msg,self.buf=self.buf[:n],self.buf[n:]
    f=dict(x.split('=',1) for x in msg[12:].rstrip(b'\0').decode('latin1').split('\n') if '=' in x)
    out.append((msg[:4].decode(),f))
  return out
 def close(self):self.s.close()
def field(records,cmd):return next(f for c,f in records if c==cmd)
with tempfile.TemporaryDirectory(prefix='nfsmw-pc-host-') as d:
 t=Path(d);(t/'test.cpp').write_text(code)
 subprocess.run(['clang++','-std=c++23','-O1','-pthread','-fsanitize=address,undefined',
  '-I'+str(root/'ios/src/multiplayer'),'-I'+str(a.sdk/'thirdparty/inja/third_party/include'),
  str(t/'test.cpp'),*[str(root/'ios/src/multiplayer'/f) for f in ['servidor_ea.cpp','red_lan.cpp','pc_gateway.cpp']],'-o',str(t/'test')],check=True)
 udp=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);udp.bind(('',9999));udp.settimeout(5)
 proc=subprocess.Popen([str(t/'test'),d,a.ip],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
 clients=[]
 try:
  assert proc.stdout.readline().strip()=='ready'
  packet,source=udp.recvfrom(1024)
  assert len(packet)==384 and packet[:5]==b'gEA\x03\x05' and source[0]==a.ip
  assert packet[8:15]==b'NFSMWNA' and packet[40:52]==b'PhoneHostLo\x00'
  assert packet[72:79]==b'9900|0\x00' and packet[258:].startswith(b'TCP:~1:1024\tUDP:~1:1024\x00')
  phone,pc=Client(10901),Client(9900);clients=[phone,pc]
  assert field(pc.ask('@dir'),'@dir')['PORT']=='9900'
  assert field(phone.ask('@dir'),'@dir')['PORT']=='10901'
  for client,name in [(phone,'Phone'),(pc,'PC')]:
   client.ask('auth',NAME=name,MADDR='$00090000c0a801cd^binary' if name=='Phone' else '$ca01a8c0')
   client.ask('pers',PERS=name)
  params='V%3d192641%0aM%3d2%0a'
  phone.ask('ucre',NAME='Room',SIZE='2',TYPE='0',PARAMS=params)
  phone.ask('uadm',NAME='Room',DESC='$00090000c0a801cd',PARAMS=params)
  listed=field(pc.ask('usea'),'+uss')
  expected='$'+''.join(f'{int(x):02x}' for x in a.ip.split('.')[::-1])
  assert listed['D']==expected and listed['P']=='V%3d192359%0aM%3d2%0a'
  phone.ask('gcre',NAME='Room',MINSIZE='2',MAXSIZE='2',PLATPARAMS='binary')
  phone.ask('gset',SESS='$binary')
  pc.ask('ujoi',NAME='Room')
  joined=field(pc.ask('gjoi',NAME='Room'),'gjoi')
  assert joined['COUNT']=='2' and joined['SESS']=='' and joined['MADDR0']==expected and joined['MADDR1']==expected
  update=field(phone.read(),'+mgm')
  assert update['SESS']=='$binary' and update['MADDR0']=='$00090000c0a801cd^binary'
  assert update['MADDR1'].startswith('$00090000') and '^' in update['MADDR1']
  phone.ask('gsta');assert field(pc.read(),'+ses')['SESS']==''
  assert any(c=='gcre' and f=={} for c,f in pc.ask('gcre',NAME='Forbidden'))
  print('PASS: actual PC-host server, source-bound native384-byte broadcast, dual directory ports, PC room build/address, guest synthetic Xbox identity, per-recipient game/session updates and start; no real PC game tested.')
 finally:
  for client in clients:client.close()
  udp.close()
  proc.communicate('\n',timeout=5)
  assert proc.returncode==0
