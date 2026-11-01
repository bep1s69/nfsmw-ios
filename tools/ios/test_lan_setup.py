#!/usr/bin/env python3
"""Exercise actual LAN preflight at Host/Join boundaries and the automatic
sign-in decision (join a phone/PC lobby or host one) with deterministic peers.
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
#include "pc_gateway.h"
#include <arpa/inet.h>
#include <cassert>
#include <iostream>
#include <deque>
#include <vector>
int scans=0,parars=0;bool running=false;
std::deque<std::vector<nfsmw::red::Encontrado>> scanResults;
std::vector<uint32_t> guestPeers{1};
std::function<nfsmw::pc::Route()> decide;
int binds=0,checks=0,stops=0,failures=0,pcStarts=0;bool pcHost=false;
nfsmw::red::Comprobacion check=nfsmw::red::Comprobacion::kLibre;
namespace nfsmw::red {
std::string IpLocal(){return "192.168.1.150";}
std::string IpHacia(const std::string&){return IpLocal();}
bool IpValida(const std::string& s){in_addr a{};return inet_pton(AF_INET,s.c_str(),&a)==1;}
bool DireccionValida(const std::string& s){return IpValida(s)||s=="friend.local";}
std::string ResolverIpv4(const std::string& s){return s=="friend.local"?"192.168.1.205":s;}
std::string GamertagEfectivo(const std::string& s){return s.empty()?"User":s;}
Comprobacion ComprobarGamertag(const std::string&,const std::string&){++checks;return check;}
std::optional<std::vector<Encontrado>> BuscarServidores(std::function<void(const std::string&)>,bool stopAtUdp){
 assert(stopAtUdp);++scans;
 if(scanResults.empty())return std::vector<Encontrado>{};
 auto r=scanResults.front();scanResults.pop_front();return r;}
std::vector<uint32_t> PcPeers(const std::string&){return {};}
}
namespace nfsmw::boot {void Trace(const std::string&) {}}
namespace nfsmw::pc {
bool hosting=false;int hostStarts=0;
bool Probe(const std::string&){return pcHost;}
bool ProbeMobile(const std::string&){return false;}
void SetGuestPeers(const std::vector<uint32_t>&p){guestPeers=p;hosting=false;}
bool StartAuto(std::function<Route()> d,std::function<void(const std::string&)>,std::string*){decide=d;return true;}
void Stop(){hosting=false;}
bool Hosting(){return hosting;}
void StartHosting(){hosting=true;++hostStarts;}
bool Start(const std::string&, std::function<void(const std::string&)>, std::string*) {++pcStarts;return true;}
}
namespace nfsmw::servidor {
bool ArrancarPC(const std::string&,const std::string&,std::function<void()>,std::function<std::string()>,const std::string&ip,std::string*) {assert(ip=="192.168.1.150");running=true;return true;}
bool EnMarcha(){return running;}
int Jugadores(){return 0;}
void Parar(){++stops;running=false;}
bool Arrancar(const std::string&,const std::string&,std::function<void()>,std::function<std::string()>name,std::string*error){
 ++binds;assert(name()=="iPad150");
 if(failures-->0){*error="port still closing";return false;}running=true;return true;
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
 pcHost=true;int beforePc=checks;
 auto pc=Prepare("join","192.168.1.205","iPad150",dir);
 assert(pc.error.empty() && pc.pc && pc.ip=="192.168.1.205" && pc.own_ip=="192.168.1.150" && checks==beforePc && pcStarts==1);
 pcHost=false;
 check=nfsmw::red::Comprobacion::kLibre;failures=2;
 auto hosted=Prepare("host","","iPad150",dir);
 assert(hosted.error.empty() && hosted.hosting && hosted.ip=="192.168.1.150" && binds==3);
 auto hostedPc=Prepare("host_pc","","iPad150",dir);
 assert(hostedPc.hosting && !hostedPc.pc && hostedPc.error.empty());
 int priorStarts=nfsmw::pc::hostStarts;
 assert(Prepare("host_pc","","iPad150",dir).error.empty() && nfsmw::pc::hostStarts==priorStarts);
 int oldStops=stops;check=nfsmw::red::Comprobacion::kEnUso;
 assert(!Prepare("host","","iPad150",dir).error.empty() && stops==oldStops+1);
 assert(Prepare("off","","",dir).error.empty() && stops==oldStops+2);
 // Automatic LAN: the game's sign-in decides through the loopback relay.
 using nfsmw::red::Encontrado;
 auto autoMode=Prepare("auto","","iPad150",dir);
 assert(autoMode.error.empty() && autoMode.ip=="127.0.0.1" && autoMode.own_ip=="192.168.1.150" && decide);
 scanResults={{{"192.168.1.30","PC LAN host",-1,true},{"192.168.1.205","LAN host",1,false}}};
 auto r=decide();
 assert(r.ip=="192.168.1.205" && !r.pc && guestPeers.empty() && scans==1);
 assert(decide().ip=="192.168.1.205" && scans==1); // same sign-in reuses the lobby
 Prepare("auto","","iPad150",dir);
 scanResults={{{"192.168.1.30","PC LAN host",-1,true}}};
 r=decide();
 assert(r.ip=="192.168.1.30" && r.pc && guestPeers==std::vector<uint32_t>{0xc0a8011e});
 Prepare("auto","","iPad150",dir);
 int starts=nfsmw::pc::hostStarts;scans=0;
 scanResults={{},{{"192.168.1.200","LAN host",0,false}}}; // rival higher: stay host
 r=decide();
 assert(r.ip=="192.168.1.150" && !r.pc && running && nfsmw::pc::hosting && nfsmw::pc::hostStarts==starts+1 && scans==2);
 Prepare("auto","","iPad150",dir);
 scanResults={{},{{"192.168.1.100","LAN host",0,false}}}; // rival lower: join it
 r=decide();
 assert(r.ip=="192.168.1.100" && !r.pc && !running && !nfsmw::pc::hosting);
 Prepare("off","","",dir);
 std::cout<<"PASS: actual automatic sign-in prefers a mobile lobby over a PC, reuses it within one sign-in, joins a native PC, hosts for phones/PCs when alone, and the higher address yields to a simultaneous lower host\n";
 std::cout<<"PASS: actual preflight rejects self-join/partial IP, resolves remote host, handles duplicate/unreachable, retries retiring listeners and stops on cancel/failure\n";
}
'''
with tempfile.TemporaryDirectory(prefix='nfsmw-setup-test-') as directory:
 tmp=Path(directory);source=tmp/'test.cpp';source.write_text(code)
 exe=tmp/'test'
 subprocess.run(['clang++','-std=c++23','-I'+str(root/'ios/src/multiplayer'),str(source),str(root/'ios/src/multiplayer/lan_session.cpp'),'-o',str(exe),'-pthread'],check=True)
 subprocess.run([str(exe),str(tmp/'data')],check=True)
