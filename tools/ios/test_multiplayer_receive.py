#!/usr/bin/env python3
"""Exercise actual WSARecvFrom after reusing its caller's WSABUF stack array.
Socket delivery is gated deterministically; memory/endian pointers and receive
implementation are real. Kernel ownership and event objects are test doubles.
"""
import argparse
from pathlib import Path
import subprocess
import tempfile
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--sdk', type=Path, required=True)
a = p.parse_args()
s = (a.sdk / 'src/kernel/xam/xam_net.cpp').read_text()
structs = s[s.index('struct XWSABUF {'):s.index('void LoadSockaddr(')]
receive = s[s.index('static uint32_t RedRepartir('):s.index('// PARCHE LOCAL (red): recoge una WSARecvFrom')]
prefix = r'''
#include <rex/types.h>
#include <vector>
#include <thread>
#include <atomic>
#include <memory>
#include <chrono>
#include <algorithm>
#include <cassert>
#include <cerrno>
#include <arpa/inet.h>
uint8_t guest[4096]{};
struct Memory {
 template<class T=void*> T TranslateVirtual(uint32_t a) {assert(a < sizeof(guest));return reinterpret_cast<T>(guest+a);}
} guest_memory;
#define REX_KERNEL_MEMORY() (&guest_memory)
#define RED_LOG(...) ((void)0)
namespace memory {template<class T>void store_and_swap(void*p,T v){auto b=rex::be<T>(v);memcpy(p,&b,sizeof(b));}}
struct N_XSOCKADDR_IN {uint16_t sin_family,sin_port;uint32_t sin_addr;uint8_t x_sin_zero[8];};
using XSOCKADDR_IN=struct Address {rex::be<uint16_t>sin_family,sin_port;rex::be<uint32_t>sin_addr;uint8_t x_sin_zero[8];};
std::atomic<bool> deliver{false};
struct XSocket {
 int RecvFrom(uint8_t*p,uint32_t capacity,int,N_XSOCKADDR_IN*from,uint32_t*) {
  if(!deliver.load()){errno=EAGAIN;return -1;}
  assert(capacity==21);for(int i=0;i<21;++i)p[i]=uint8_t(i+1);
  from->sin_family=2;from->sin_port=3658;from->sin_addr=0xac140a05;return 21;
 }
};
struct XEvent {std::atomic<bool>set{false};void Set(int,bool){set.store(true);}};
auto sock=std::make_shared<XSocket>();auto event=std::make_shared<XEvent>();
struct Objects {template<class T>std::shared_ptr<T>LookupObject(uint32_t){
 if constexpr(std::is_same_v<T,XSocket>)return sock;else return event;
}} objects;
#define REX_KERNEL_OBJECTS() (&objects)
struct XThread {static inline uint32_t error=0;static void SetLastError(uint32_t e){error=e;}};
uint32_t RedFijarError(){return 10035;}uint32_t RedErrorWsa(int){return 10022;}
'''
test = r'''
template<class T>ppc_ptr_t<T> ptr(uint32_t a){return {reinterpret_cast<T*>(guest+a),a};}
int main(){
 for(bool immediate:{false,true}){
  memset(guest,0,sizeof(guest));event->set=false;deliver=immediate;
  auto descriptors=ptr<XWSABUF>(128);
  descriptors[0].len=8;descriptors[0].buf_ptr=512;
  descriptors[1].len=13;descriptors[1].buf_ptr=600;
  auto ov=ptr<XWSAOVERLAPPED>(256);ov->event_handle=9;
  auto n=ptr<rex::be<uint32_t>>(300), flags=ptr<rex::be<uint32_t>>(304),size=ptr<rex::be<uint32_t>>(308);
  *size=16;
  auto result=NetDll_WSARecvFrom_entry(1,8,descriptors,2,n,flags,ptr<XSOCKADDR_IN>(320),size,ov,nullptr);
  assert(result==(immediate?0:~0u));
  if(!immediate){
   assert(XThread::error==997 && ov->internal==0x103);
   // The guest function has returned. Its old stack descriptors now point
   // at unrelated live data, just as NetCrit reuses DirtySock's stack frame.
   descriptors[0].len=0xffffffff;descriptors[0].buf_ptr=1024;
   descriptors[1].len=0;descriptors[1].buf_ptr=1100;
   deliver=true;
  }
  for(int i=0;i<2000 && !event->set.load();++i)std::this_thread::sleep_for(std::chrono::milliseconds(1));
  assert(event->set.load() && ov->internal==0 && ov->internal_high==21);
  for(int i=1024;i<1100;++i)assert(guest[i]==0);
  for(int i=0;i<8;++i)assert(guest[512+i]==i+1);
  for(int i=0;i<13;++i)assert(guest[600+i]==i+9);
  assert(*size==16 && ptr<XSOCKADDR_IN>(320)->sin_port==3658);
  if(immediate)assert(*n==21);
 }
}
'''
with tempfile.TemporaryDirectory(prefix='nfsmw-lan-receive-') as d:
    source = Path(d)/'receive.cpp'; binary = Path(d)/'receive'
    source.write_text(prefix+structs+receive+test)
    subprocess.run(['clang++','-std=c++23','-O1','-pthread','-fsanitize=address,undefined',
                    '-I'+str(a.sdk/'include'),str(source),'-o',str(binary)],check=True)
    subprocess.run([str(binary)],check=True)
print('Actual WSARecvFrom: pending stack reuse, scatter buffers, immediate completion and untouched canaries passed (ASan/UBSan)')
