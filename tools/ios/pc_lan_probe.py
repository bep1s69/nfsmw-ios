#!/usr/bin/env python3
"""Read-only PC LAN feasibility probe; never advertises a playable mobile host.

PC discovery/auth reference: OhhhThatVarun/nfsmw-lan-protocol (MIT),
commit dd2eb3329566f3b0c1e11e3e07a0a26b14da0487. Independently implemented.
A directory connection is not a cross-play/race compatibility test.
"""
import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
import socket
import struct
import time


def frame(command, body=b''):
    if len(command) != 4:
        raise ValueError('four-byte command required')
    return command + bytes(4) + struct.pack('>I', 13 + len(body)) + body + b'\0'


def discovery(data):
    if len(data) != 384 or data[:4] != b'gEA\x03':
        raise ValueError('not a PC LAN announcement')
    if data[8:16].rstrip(b'\0') != b'NFSMWNA':
        raise ValueError('unknown PC game/region identifier')
    def field(start, end):
        return data[start:end].split(b'\0', 1)[0].decode('ascii')
    name = field(40, 72)
    if not name or len(name) > 12:
        raise ValueError('invalid lobby name')
    port, count = map(int, field(72, 258).split('|'))
    if not 1 <= port <= 65535 or not 0 <= count <= 64:
        raise ValueError('invalid port/count')
    return dict(name=name, port=port, players=count, capabilities=field(258,384))


def read_frame(peer):
    def exact(count):
        data = b''
        while len(data) < count:
            chunk = peer.recv(count-len(data))
            if not chunk:
                raise ValueError('connection closed during EA frame')
            data += chunk
        return data
    header = exact(12)
    size, = struct.unpack('>I', header[8:12])
    if not 12 <= size <= 65536:
        raise ValueError('invalid EA frame length')
    return header[:4], header[4:8], exact(size-12)


def directory(host, port=9900, profile="pc"):
    ipaddress.IPv4Address(host)
    request = b'\n'.join([
        b'REGN=NA', b'CLST=194010', b'NETV=20', b'FROM=US', b'LANG=EN',
        b'PROD=nfs-pc-2006', b'VERS="pc/1.3-Nov 21 2005"', b'SLUS=SLUS_21351',
        b'SKU=14705', b'SDKVERS=3.9.3.0', b'BUILDDATE="Oct 19 2005"'])
    if profile == 'xbox':
        request = request.replace(b'CLST=194010',b'CLST=192641').replace(b'NETV=20',b'NETV=0').replace(b'nfs-pc-2006',b'nfs-xbox-2006').replace(b'pc/1.3-Nov 21 2005',b'xbox/1.2-Nov  2 2005')
    with socket.create_connection((host, port), timeout=3) as peer:
        peer.settimeout(3)
        peer.sendall(frame(b'@tic',b'RC4+MD5-V2')+frame(b'@dir',request))
        command, subtype, body = read_frame(peer)
    if command != b'@dir' or subtype != bytes(4):
        raise ValueError('directory rejected request or returned unexpected command')
    fields = {}
    for line in body.rstrip(b'\0').replace(b'\t',b'\n').split(b'\n'):
        key, sep, value = line.partition(b'=')
        if sep:
            fields[key.decode('ascii')] = value.decode('ascii')
    ipaddress.IPv4Address(fields['ADDR'])
    if not 1 <= int(fields['PORT']) <= 65535:
        raise ValueError('invalid advertised lobby port')
    return dict(stage='PC directory only; race compatibility untested',fields=fields,
                response_hex=body.hex())


def audit(folder):
    executable = next((p for p in folder.iterdir() if p.name.lower()=='speed.exe'),None)
    if executable is None:
        raise ValueError('speed.exe not found')
    data=executable.read_bytes()
    if data[:2]!=b'MZ':
        raise ValueError('not a Windows executable')
    pe,=struct.unpack_from('<I',data,0x3c)
    if data[pe:pe+4]!=b'PE\0\0':
        raise ValueError('invalid PE header')
    machine,=struct.unpack_from('<H',data,pe+4)
    names={p.name.lower() for p in folder.iterdir()}
    return dict(path=str(executable.resolve()),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
                machine=hex(machine),
                pc_host_files={n:n in names for n in ['server.dll','server.cfg']},
                warning='Static audit only; missing server files concern PC hosting, not proof that PC joining fails.')


def listen(seconds):
    deadline=time.monotonic()+seconds
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as peer:
        peer.bind(('',9999))
        while time.monotonic()<deadline:
            peer.settimeout(max(.01,deadline-time.monotonic()))
            try:
                data,address=peer.recvfrom(65536)
            except socket.timeout:
                break
            try:
                result=discovery(data)
            except (ValueError,UnicodeError):
                continue
            print(json.dumps(dict(source=address[0],source_port=address[1],
                                  announcement=result,packet_hex=data.hex())),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--audit',type=Path,metavar='PC_GAME_FOLDER')
    g.add_argument('--directory',metavar='PC_HOST_IPV4')
    g.add_argument('--listen',type=int,metavar='SECONDS')
    p.add_argument('--profile',choices=['pc','xbox'],default='pc',help='directory request identity only')
    a=p.parse_args()
    try:
        if a.audit:
            print(json.dumps(audit(a.audit),indent=2))
        elif a.directory:
            print(json.dumps(directory(a.directory,profile=a.profile),indent=2))
        elif 1<=a.listen<=60:
            listen(a.listen)
        else:
            p.error('listen duration must be 1–60 seconds')
    except (OSError,ValueError,KeyError,struct.error) as e:
        p.exit(1,str(e)+'\n')


if __name__=='__main__':
    main()
