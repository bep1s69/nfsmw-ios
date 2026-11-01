#!/usr/bin/env python3
"""Run actual SDK socket code on Darwin; verify event translation and USA hook.
Only kernel-object ownership is stubbed for sockets; all OS I/O and SDK endian
structures come from the real implementation. Needs local socket permission.
"""
import argparse
from pathlib import Path
import subprocess
import tempfile
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--sdk',type=Path,required=True)
a=p.parse_args()
root=Path(__file__).resolve().parents[2]
header=(a.sdk/'include/rex/system/xsocket.h').read_text()
header=header[header.index('namespace rex::system {'):]
source=(a.sdk/'src/system/xsocket.cpp').read_text()
source=source[source.index('namespace rex::system {'):]
prefix=r'''
#include <rex/types.h>
#include <atomic>
#include <functional>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <fcntl.h>
#include <unistd.h>
#include <cassert>
#include <cstring>
#include <queue>
#include <mutex>
#include <memory>
namespace rex { template<class T,size_t N>constexpr size_t countof(T(&)[N]){return N;} }
namespace rex::thread { struct Event {}; }
namespace rex::net {
int socket_close(int f) { return close(f); }
int socket_ioctl(int f,unsigned long cmd,uint8_t* a) { return ioctl(f,cmd,a); }
}
namespace rex::system {
using X_STATUS=uint32_t;
constexpr X_STATUS X_STATUS_SUCCESS=0, X_STATUS_UNSUCCESSFUL=0xc0000001;
struct KernelState {};
struct XObject {
 enum class Type {Socket};
 XObject(KernelState*k,Type):kernel_state_(k){}
 KernelState*kernel_state_;
};
template<class T>using object_ref=std::shared_ptr<T>;
}
'''
test=r'''
int main() {
 using namespace rex::system;
 KernelState k;
 XSocket x(&k),y(&k);
 assert(x.Initialize(XSocket::X_AF_INET,XSocket::X_SOCK_DGRAM,XSocket::X_IPPROTO_UDP)==0);
 assert(y.Initialize(XSocket::X_AF_INET,XSocket::X_SOCK_DGRAM,XSocket::X_IPPROTO_UDP)==0);
 N_XSOCKADDR_IN bindTo{};bindTo.sin_family=AF_INET;bindTo.sin_addr=0x7f000001;bindTo.sin_port=0;
 assert(x.Bind(&bindTo,16)==0); assert(y.Bind(&bindTo,16)==0);
 sockaddr_in ax{},ay{};socklen_t n=sizeof(ax);
 assert(getsockname(x.native_handle(),(sockaddr*)&ax,&n)==0);
 n=sizeof(ay);assert(getsockname(y.native_handle(),(sockaddr*)&ay,&n)==0);
 timeval timeout{1,0};setsockopt(y.native_handle(),SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout));
 N_XSOCKADDR_IN target{};target.sin_family=AF_INET;target.sin_addr=ntohl(ay.sin_addr.s_addr);target.sin_port=ntohs(ay.sin_port);
 uint8_t message[]={1,2,3,4};assert(x.SendTo(message,4,0,&target,16)==4);
 uint8_t buf[16];N_XSOCKADDR_IN from{};uint32_t size=16;
 assert(y.RecvFrom(buf,sizeof(buf),0,&from,&size)==4);
 assert(memcmp(buf,message,4)==0 && uint32_t(from.sin_addr)==0x7f000001);
 assert(uint16_t(from.sin_port)==ntohs(ax.sin_port));
 // TCP native sockaddr conversion and accepted peer family/data on Darwin.
 XSocket listenSocket(&k),client(&k);
 assert(listenSocket.Initialize(XSocket::X_AF_INET,XSocket::X_SOCK_STREAM,XSocket::X_IPPROTO_TCP)==0);
 assert(client.Initialize(XSocket::X_AF_INET,XSocket::X_SOCK_STREAM,XSocket::X_IPPROTO_TCP)==0);
 assert(listenSocket.Bind(&bindTo,16)==0 && listenSocket.Listen(1)==0);
 sockaddr_in addr{};n=sizeof(addr);assert(getsockname(listenSocket.native_handle(),(sockaddr*)&addr,&n)==0);
 N_XSOCKADDR connectTo{};connectTo.address_family=AF_INET;
 memcpy(connectTo.sa_data,&addr.sin_port,2);memcpy(connectTo.sa_data+2,&addr.sin_addr.s_addr,4);
 assert(client.Connect(&connectTo,16)==0);
 N_XSOCKADDR acceptedAddress{};int acceptedSize=16;
 auto accepted=listenSocket.Accept(&acceptedAddress,&acceptedSize);
 assert(accepted && acceptedAddress.address_family==AF_INET && acceptedSize==16);
 assert(client.Send(message,4,0)==4 && accepted->Recv(buf,16,0)==4);
 int noPipe=0;socklen_t noPipeSize=sizeof(noPipe);
 assert(getsockopt(client.native_handle(),SOL_SOCKET,SO_NOSIGPIPE,&noPipe,&noPipeSize)==0 && noPipe==1);
 // A second Close/destructor must never close a newly recycled descriptor.
 int old=x.native_handle();assert(x.Close()==0);
 int fresh=socket(AF_INET,SOCK_DGRAM,0);assert(fresh>=0);
 assert(x.Close()==0 && fcntl(fresh,F_GETFD)>=0);close(fresh);
}
'''
net=(a.sdk/'src/kernel/xam/xam_net.cpp').read_text()
wait=net[net.index('u32 NetDll_WSAWaitForMultipleEvents_entry'):net.index('u32 NetDll_WSACreateEvent_entry')]
waitprefix=r'''
#include <cstdint>
#include <cassert>
using u32=uint32_t;using mapped_u32=uint32_t*;using X_STATUS=uint32_t;
constexpr uint32_t X_STATUS_ALERTED=0x101;
#define XFAILED(x) ((x)&0x80000000u)
struct XThread {static void SetLastError(uint32_t) {}};
uint32_t answer=0,kind=99,calls=0;int64_t duration=0;bool infinite=false;
namespace xboxkrnl {
uint32_t xeRtlNtStatusToDosError(uint32_t x){return x;}
uint32_t xeNtWaitForMultipleObjectsEx(uint32_t,uint32_t*,uint32_t k,uint32_t,uint32_t,uint64_t*t){
 kind=k;infinite=t==nullptr;duration=t?int64_t(*t):0;++calls;return answer;
}
}
'''
waittest=r'''
int main(){
 uint32_t events[3]{};
 answer=2;assert(NetDll_WSAWaitForMultipleEvents_entry(3,events,0,50,0)==2);
 assert(kind==1 && duration==-500000 && !infinite);
 answer=0;assert(NetDll_WSAWaitForMultipleEvents_entry(3,events,1,~0u,0)==0);
 assert(kind==0 && infinite);
 answer=0x102;assert(NetDll_WSAWaitForMultipleEvents_entry(3,events,0,0,0)==0x102 && duration==0);
 calls=0;assert(NetDll_WSAWaitForMultipleEvents_entry(65,events,0,0,0)==~0u && calls==0);
}
'''
hook=(root/'ios/src/multiplayer/game_lan.cpp').read_text()
hook=hook[hook.index('extern "C" void __imp__'):]
hookprefix=r'''
#include <cstdint>
#include <cassert>
struct Reg {union{uint64_t u64;uint32_t u32;};};struct PPCContext{Reg r3{},r4{};};
#define REX_FUNC(n) void n(PPCContext&ctx,uint8_t*base)
#define REXCVAR_GET(n) (n)
#define REX_LOAD_U8(a) (base[(a)])
bool red_lan=false;int originals=0;
extern "C" void __imp__sub_828298E0(PPCContext&ctx,uint8_t*) {++originals;ctx.r3.u64=999;}
'''
hooktest=r'''
int main(){
 uint8_t memory[64]{};PPCContext c;c.r4.u64=16;memory[20]=192;
 sub_828298E0(c,memory);assert(originals==1 && c.r3.u64==999);
 red_lan=true;sub_828298E0(c,memory);assert(originals==1 && c.r3.u64==16);
 memory[20]=127;sub_828298E0(c,memory);assert(originals==2 && c.r3.u64==999);
}
'''
with tempfile.TemporaryDirectory(prefix='nfsmw-lan-transport-') as directory:
 tmp=Path(directory)
 for name,code in [('sockets',prefix+header+source+test),('events',waitprefix+wait+waittest),('hook',hookprefix+hook+hooktest)]:
  f=tmp/(name+'.cpp');f.write_text(code);exe=tmp/name
  subprocess.run(['clang++','-std=c++23','-O1','-pthread','-I'+str(a.sdk/'include'),str(f),'-o',str(exe)],check=True)
  subprocess.run([str(exe)],check=True)
  print(name,': actual implementation host checks passed')
