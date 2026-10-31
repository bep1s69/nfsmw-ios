#!/usr/bin/env python3
"""Compile actual in-app gateway and verify fragmented PC/mobile control flow."""
from pathlib import Path
import subprocess
import tempfile
root=Path(__file__).resolve().parents[2]
code=r'''
#include "pc_gateway.h"
#include <arpa/inet.h>
#include <sys/socket.h>
#include <unistd.h>
#include <atomic>
#include <cassert>
#include <cstring>
#include <thread>
#include <iostream>
using namespace nfsmw::pc;
bool readall(int s,std::string&out,size_t n){while(out.size()<n){char b[4096];int r=recv(s,b,std::min(sizeof(b),n-out.size()),0);if(r<=0)return false;out.append(b,r);}return true;}
std::string receive(int s){std::string out;assert(readall(s,out,12));uint32_t n;memcpy(&n,out.data()+8,4);assert(readall(s,out,ntohl(n)));return out;}
void sendall(int s,const std::string&v){for(size_t i=0;i<v.size();++i)assert(send(s,v.data()+i,1,0)==1);}
int conn(int port){int s=socket(AF_INET,SOCK_STREAM,0);sockaddr_in a{};a.sin_family=AF_INET;a.sin_addr.s_addr=htonl(INADDR_LOOPBACK);a.sin_port=htons(port);assert(connect(s,(sockaddr*)&a,sizeof(a))==0);timeval t{3,0};setsockopt(s,SOL_SOCKET,SO_RCVTIMEO,&t,sizeof(t));return s;}
int main(){
 assert(Field("PERS=\tNAME=Abc\0","PERS").empty());assert(Field("NAME=Abc\tPERS=Guest\0","PERS")=="Guest");
 std::string binary="MADDR=$";binary+=char(0x80);binary+=char(0xff);binary+="\nGTAG=Guest\0";
 auto fixed=Put(binary,"PERS","Guest");assert(Field(fixed,"MADDR")==std::string("$")+char(0x80)+char(0xff));
 assert(Field(Put("PERS=Old\tX=1\0","PERS","New"),"PERS")=="New");
 int listener=socket(AF_INET,SOCK_STREAM,0);int yes=1;setsockopt(listener,SOL_SOCKET,SO_REUSEADDR,&yes,sizeof(yes));
 sockaddr_in a{};a.sin_family=AF_INET;a.sin_addr.s_addr=htonl(INADDR_LOOPBACK);a.sin_port=htons(9900);assert(bind(listener,(sockaddr*)&a,sizeof(a))==0 && listen(listener,4)==0);
 std::thread backend([&]{
  int s=accept(listener,nullptr,nullptr);assert(s>=0);assert(receive(s).substr(0,4)=="@tic");assert(receive(s).substr(0,4)=="@dir");
  sendall(s,Frame("@dir","ADDR=127.0.0.1\tPORT=9900\tSESS=42"));close(s);
  s=accept(listener,nullptr,nullptr);assert(s>=0);
  assert(receive(s).substr(0,4)=="@tic");assert(receive(s).substr(0,4)=="@dir");sendall(s,Frame("@dir","ADDR=127.0.0.1\tPORT=9900\tSESS=42"));close(s);
  s=accept(listener,nullptr,nullptr);assert(s>=0);
  auto addr=receive(s);assert(Field(addr.substr(12),"ADDR")=="127.0.0.1");
  assert(receive(s).substr(0,4)=="auth");auto pers=receive(s);
  assert(Field(pers.substr(12),"PERS")=="Guest");assert(Field(pers.substr(12),"MADDR")==std::string("$")+char(0x80)+char(0xff));
  sendall(s,Frame("pers","PERS=Guest\tNAME=Guest"));
  // The Xbox-only 'user' request must not reach the PC (which returns badc).
  auto ping=receive(s);assert(ping.substr(0,4)=="~png");
  std::string news="newsbadc";news+=std::string(3,'\0');news+=char(12);sendall(s,news);close(s);
 });
 assert(Probe("127.0.0.1"));std::string error;assert(Start("127.0.0.1",{},&error));
 int s=conn(30960);sendall(s,Frame("@tic","RC4+MD5-V2")+Frame("@dir","PROD=nfs-xbox-2006"));auto dir=receive(s);assert(Field(dir.substr(12),"PORT")=="30960" && Field(dir.substr(12),"SESS")=="42");close(s);
 s=conn(30960);sendall(s,Frame("addr","ADDR=127.9.9.9\nPORT=1234")+Frame("auth","GTAG=Guest")+Frame("pers",binary));assert(Field(receive(s).substr(12),"PERS")=="Guest");
 sendall(s,Frame("user","PERS=Guest"));auto stats=receive(s);auto values=Field(stats.substr(12),"STAT");assert(std::count(values.begin(),values.end(),',')==43 && Field(stats.substr(12),"PERS")=="Guest");
 sendall(s,Frame("~png","TIME=1"));auto news=receive(s);assert(news.substr(0,8)=="newsbadc" && news.size()==12);close(s);
 backend.join();Stop();Stop();close(listener);
 std::cout<<"PASS: actual PC gateway directory/persona/physical-source address/44-value local history, Binary7 preservation, fragmented frames, badc pass-through and clean shutdown\n";
}
'''
with tempfile.TemporaryDirectory(prefix='nfsmw-pc-gateway-') as d:
 p=Path(d);(p/'test.cpp').write_text(code)
 subprocess.run(['clang++','-std=c++23','-O1','-pthread','-fsanitize=address,undefined','-I'+str(root/'ios/src/multiplayer'),str(p/'test.cpp'),str(root/'ios/src/multiplayer/pc_gateway.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
