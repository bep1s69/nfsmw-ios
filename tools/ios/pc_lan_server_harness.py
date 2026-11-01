#!/usr/bin/env python3
"""Build a tiny bounded Win32 harness for a locally owned PC server.dll.

Own generated PE code only; no EA binary is embedded. Run in a disposable Wine/
CrossOver bottle with the game's server.cfg as working directory. Reverse
checked against supplied speed.exe's four-argument cdecl StartServer call:
(name, locale_flag, optional_callback, callback_context). The server's own
configuration chooses its interface/9900 listener. This does not run a PC racer.
"""
import argparse
from pathlib import Path
import struct
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--dll',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--seconds',type=int,default=30)
args=parser.parse_args()
if not 1<=args.seconds<=60:parser.error('duration must be 1–60 seconds')
dll=args.dll.resolve(strict=True)
winpath=('Z:'+str(dll).replace('/', '\\')).encode('ascii')+b'\0'
base=0x400000;rva=0x1000;section=bytearray(0x800);cursor=0x100

def alloc(b):
 global cursor
 o=cursor;section[o:o+len(b)]=b;cursor=(o+len(b)+3)&~3;return base+rva+o
path=alloc(winpath)
start=alloc(b'StartServer\0');stop=alloc(b'StopServer\0');name=alloc(b'PCprobe\0')
imports=['LoadLibraryA','GetProcAddress','Sleep','ExitProcess'];kernel=alloc(b'KERNEL32.dll\0')
hints=[alloc(b'\0\0'+s.encode()+b'\0')-base for s in imports]
if cursor>0x300:parser.error('DLL path too long for minimal harness')
for i,h in enumerate(hints):struct.pack_into('<I',section,0x340+4*i,h);struct.pack_into('<I',section,0x360+4*i,h)
struct.pack_into('<5I',section,0x300,rva+0x340,0,0,kernel-base,rva+0x360)
code=bytearray();fixups=[]
def emit(h):code.extend(bytes.fromhex(h))
def push(v):emit('68');code.extend(struct.pack('<I',v))
def call(i):emit('ff15');code.extend(struct.pack('<I',base+rva+0x360+4*i))
def fail():emit('0f84');fixups.append(len(code));code.extend(bytes(4))
push(path);call(0);emit('85c0');fail();emit('89c6');push(start);emit('56');call(1);emit('85c0');fail();emit('89c3')
for _ in range(3):push(0)
push(name);emit('ffd3 83c410 84c0');fail();push(args.seconds*1000);call(2)
push(stop);emit('56');call(1);emit('85c0');fail();emit('ffd0');push(0);call(3)
failure=len(code);push(2);call(3)
for o in fixups:struct.pack_into('<i',code,o,failure-(o+4))
assert len(code)<0x100
section[:len(code)]=code
headers=bytearray(0x200);headers[:2]=b'MZ';struct.pack_into('<I',headers,0x3c,0x80);headers[0x80:0x84]=b'PE\0\0';struct.pack_into('<HHIIIHH',headers,0x84,0x14c,1,0,0,0,224,0x102)
o=0x98;struct.pack_into('<H',headers,o,0x10b);struct.pack_into('<III',headers,o+4,0x800,0,0);struct.pack_into('<III',headers,o+16,rva,rva,rva);struct.pack_into('<III',headers,o+28,base,0x1000,0x200);struct.pack_into('<HH',headers,o+40,4,0);struct.pack_into('<HH',headers,o+48,4,0);struct.pack_into('<II',headers,o+56,0x2000,0x200);struct.pack_into('<H',headers,o+68,3);struct.pack_into('<IIIIII',headers,o+72,0x100000,0x1000,0x100000,0x1000,0,16);struct.pack_into('<II',headers,o+104,rva+0x300,40)
s=o+224;headers[s:s+8]=b'.probe\0\0';struct.pack_into('<IIIIIIHHI',headers,s+8,0x800,rva,0x800,0x200,0,0,0,0,0xe0000060)
args.output.write_bytes(headers+section)
print('Built',args.output,'bytes',len(headers+section),'duration',args.seconds,'seconds')
