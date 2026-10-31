#!/usr/bin/env python3
"""Exercise actual LAN preflight at Host/Join boundaries with deterministic peers.
Network/server interfaces are stubbed; this does not validate UIKit or Wi-Fi.
"""
from pathlib import Path
import subprocess
import tempfile
root=Path(__file__).resolve().parents[2]
code=r'''
#include "lan_session.h"
#include "red_lan.h"
#include "servidor_ea.h"
#include <arpa/inet.h>
#include <cassert>
#include <iostream>
int binds=0,checks=0,stops=0,failures=0;
nfsmw::red::Comprobacion check=nfsmw::red::Comprobacion::kLibre;
namespace nfsmw::red {
std::string IpLocal(){return "192.168.1.150";}
bool IpValida(const std::string& s){in_addr a{};return inet_pton(AF_INET,s.c_str(),&a)==1;}
bool DireccionValida(const std::string& s){return IpValida(s)||s=="friend.local";}
std::string ResolverIpv4(const std::string& s){return s=="friend.local"?"192.168.1.205":s;}
std::string GamertagEfectivo(const std::string& s){return s.empty()?"User":s;}
Comprobacion ComprobarGamertag(const std::string&,const std::string&){++checks;return check;}
}
namespace nfsmw::servidor {
void Parar(){++stops;}
bool Arrancar(const std::string&,const std::string&,std::function<void()>,std::function<std::string()>name,std::string*error){
 ++binds;assert(name()=="iPad150");
 if(failures-->0){*error="port still closing";return false;}return true;
}
}
int main(int argc,char**argv){
 using nfsmw::lan::Prepare;
 auto dir=std::filesystem::path(argv[1]);
 assert(!Prepare("unknown","","iPad150",dir).error.empty() && binds==0 && checks==0);
 auto self=Prepare("join","192.168.1.150","iPad150",dir);
 assert(self.error.find("OTHER device")!=std::string::npos && checks==0 && binds==0);
 assert(!Prepare("join","192.168.1","iPad150",dir).error.empty() && checks==0);
 auto joined=Prepare("join","friend.local","iPad150",dir);
 assert(joined.error.empty() && joined.ip=="192.168.1.205" && !joined.hosting && checks==1);
 check=nfsmw::red::Comprobacion::kEnUso;
 assert(Prepare("join","192.168.1.205","iPad150",dir).error.find("already in use")!=std::string::npos);
 check=nfsmw::red::Comprobacion::kSinRespuesta;
 assert(Prepare("join","192.168.1.205","iPad150",dir).error.find("did not answer")!=std::string::npos);
 check=nfsmw::red::Comprobacion::kLibre;failures=2;
 auto hosted=Prepare("host","","iPad150",dir);
 assert(hosted.error.empty() && hosted.hosting && hosted.ip=="192.168.1.150" && binds==3);
 int oldStops=stops;check=nfsmw::red::Comprobacion::kEnUso;
 assert(!Prepare("host","","iPad150",dir).error.empty() && stops==oldStops+1);
 assert(Prepare("off","","",dir).error.empty() && stops==oldStops+2);
 std::cout<<"PASS: actual preflight rejects self-join/partial IP, resolves remote host, handles duplicate/unreachable, retries retiring listeners and stops on cancel/failure\n";
}
'''
with tempfile.TemporaryDirectory(prefix='nfsmw-setup-test-') as directory:
 tmp=Path(directory);source=tmp/'test.cpp';source.write_text(code)
 exe=tmp/'test'
 subprocess.run(['clang++','-std=c++23','-I'+str(root/'ios/src/multiplayer'),str(source),str(root/'ios/src/multiplayer/lan_session.cpp'),'-o',str(exe)],check=True)
 subprocess.run([str(exe),str(tmp/'data')],check=True)
