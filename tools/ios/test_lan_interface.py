#!/usr/bin/env python3
"""Compile actual LAN interface selection with a deterministic interface list."""
from pathlib import Path
import subprocess
import tempfile
root=Path(__file__).resolve().parents[2]
s=(root/'ios/src/multiplayer/red_lan.cpp').read_text()
selection=s[s.index('int PuntosInterfaz('):s.rindex('}  // namespace nfsmw::red')]
code=r'''
#include <ifaddrs.h>
#include <net/if.h>
#include <arpa/inet.h>
#include <string>
#include <vector>
#include <algorithm>
#include <cassert>
#include <cstring>
std::string Minusculas(std::string s){for(auto&c:s)c=tolower(c);return s;}
bool EsLocal(uint32_t ip){return (ip>>24)==10 || (ip>>20)==0xac1 || (ip>>16)==0xc0a8;}
std::string Texto(uint32_t ip){in_addr a{htonl(ip)};return inet_ntoa(a);}
ifaddrs interfaces[4]{};sockaddr_in addresses[4]{},masks[4]{};
int fake_getifaddrs(ifaddrs**p){*p=interfaces;return 0;}
void fake_freeifaddrs(ifaddrs*){}
#define getifaddrs fake_getifaddrs
#define freeifaddrs fake_freeifaddrs
'''+selection+r'''
void setup(int i,const char*name,const char*ip,unsigned flags){
 interfaces[i]={};addresses[i]={};addresses[i].sin_family=AF_INET;
 inet_pton(AF_INET,ip,&addresses[i].sin_addr);
 interfaces[i].ifa_name=const_cast<char*>(name);interfaces[i].ifa_flags=flags;
 interfaces[i].ifa_addr=reinterpret_cast<sockaddr*>(&addresses[i]);
 if(i)interfaces[i-1].ifa_next=&interfaces[i];
}
int main(){
 setup(0,"en0","192.168.1.151",IFF_UP);
 assert(IpLocal()=="192.168.1.151");
 setup(1,"bridge100","172.20.10.1",IFF_UP);
 assert(IpLocal()=="172.20.10.1");
 // Order must not determine which active network is advertised.
 setup(0,"bridge100","172.20.10.1",IFF_UP);
 setup(1,"en0","192.168.1.151",IFF_UP);
 assert(IpLocal()=="172.20.10.1");
 interfaces[0].ifa_flags=0;assert(IpLocal()=="192.168.1.151");
 setup(2,"utun0","10.1.1.1",IFF_UP);
 setup(3,"pdp_ip0","10.2.2.2",IFF_UP);
 assert(IpLocal()=="192.168.1.151");
 interfaces[1].ifa_flags=0;assert(IpLocal().empty());
 interfaces[0].ifa_flags=IFF_UP;interfaces[1].ifa_flags=IFF_UP;
 masks[0].sin_family=masks[1].sin_family=AF_INET;
 inet_pton(AF_INET,"255.255.255.240",&masks[0].sin_addr);
 inet_pton(AF_INET,"255.255.0.0",&masks[1].sin_addr);
 interfaces[0].ifa_netmask=reinterpret_cast<sockaddr*>(&masks[0]);
 interfaces[1].ifa_netmask=reinterpret_cast<sockaddr*>(&masks[1]);
 auto hotspot=Vecinos("172.20.10.1");assert(hotspot.size()==13 && hotspot.front()==0xac140a02 && hotspot.back()==0xac140a0e);
 auto wifi=Vecinos("192.168.1.151");assert(wifi.size()==253 && wifi.front()==0xc0a80101 && wifi.back()==0xc0a801fe);
 assert(std::find(wifi.begin(),wifi.end(),0xc0a80197)==wifi.end());
 assert(Vecinos("10.1.1.1").empty() && Vecinos("8.8.8.8").empty());
 interfaces[0].ifa_flags=0;assert(Vecinos("172.20.10.1").empty());
}
'''
with tempfile.TemporaryDirectory(prefix='nfsmw-lan-interface-') as d:
 p=Path(d);(p/'test.cpp').write_text(code)
 subprocess.run(['clang++','-std=c++23','-fsanitize=address,undefined',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS: actual interface selector prefers active hotspot over Wi-Fi in either order; Wi-Fi fallback and inactive/VPN/cellular exclusions')
