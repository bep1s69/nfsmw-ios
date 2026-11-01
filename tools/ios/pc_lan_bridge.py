#!/usr/bin/env python3
"""Experimental mobile-to-original-PC LAN directory bridge, not proven cross-play.
Run beside a real PC LAN host. Phones join this bridge's --bind address; the
unaltered PC directory response sends the game directly to PC_HOST:9900.
No race traffic, identities, or game payloads are translated. Existing mobile
hosting is untouched. Uses victorgbd's launcher discovery/gamertag protocol.
"""
import argparse
import ipaddress
import json
import socket
import socketserver
import struct
import threading
import time
from pc_lan_probe import directory, read_frame


def relay_directory(client, pc_host, pc_port):
    client.settimeout(3)
    requests=[]
    for _ in range(2):
        command, subtype, body=read_frame(client)
        if command not in (b'@tic',b'@dir') or subtype!=bytes(4):
            raise ValueError('only plain EA directory requests accepted')
        requests.append(command+subtype+struct.pack('>I',12+len(body))+body)
        if command==b'@dir':
            break
    else:
        raise ValueError('missing directory command')
    with socket.create_connection((pc_host,pc_port),timeout=3) as backend:
        backend.settimeout(3);backend.sendall(b''.join(requests))
        command,subtype,body=read_frame(backend)
        if command!=b'@dir':
            raise ValueError('unexpected PC directory response')
        client.sendall(command+subtype+struct.pack('>I',12+len(body))+body)


class DirectoryHandler(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            relay_directory(self.request,self.server.pc_host,self.server.pc_port)
            print(json.dumps(dict(stage='directory relayed',peer=self.client_address[0])),flush=True)
        except (OSError,ValueError) as e:
            print(json.dumps(dict(stage='directory failed',error=str(e))),flush=True)


class CheckHandler(socketserver.StreamRequestHandler):
    def handle(self):
        self.request.settimeout(3)
        try:
            line=self.rfile.readline(256).decode('ascii').strip()
            if not line.startswith('GAMERTAG ') or not 1<=len(line[9:])<=15:
                return
            # Verify the original host is alive before accepting preflight.
            directory(self.server.pc_host,self.server.pc_port,profile='xbox')
            name=line[9:].casefold();now=time.monotonic()
            with self.server.hold_lock:
                old=self.server.holds.get(name)
                busy=old and old[0]!=self.client_address[0] and now<old[1]
                if not busy:
                    self.server.holds[name]=(self.client_address[0],now+600)
            self.wfile.write(b'IN_USE\n' if busy else b'FREE\n')
        except (OSError,ValueError,KeyError,UnicodeError):
            return


class SearchHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data,peer=self.request
        if data.strip()==b'NFSMW_DISCOVER':
            peer.sendto(b'NFSMW_SERVER\nNAME=PC LAN experimental\nPLAYERS=-1\n',self.client_address)


class TCP(socketserver.ThreadingTCPServer):
    daemon_threads=True


class UDP(socketserver.ThreadingUDPServer):
    daemon_threads=True


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bind',required=True,help='this computer LAN IPv4 address')
    p.add_argument('--pc-host',required=True,help='original PC LAN host IPv4')
    p.add_argument('--seconds',type=int,default=600,help='bounded test duration, 1–3600 seconds')
    a=p.parse_args()
    for value in (a.bind,a.pc_host):
        if not ipaddress.IPv4Address(value).is_private:
            p.error('use local/private IPv4 addresses')
    if not 1<=a.seconds<=3600:
        p.error('duration must be 1–3600 seconds')
    print(json.dumps(directory(a.pc_host,profile='xbox')),flush=True)
    servers=[];started=[]
    try:
        for cls,port,handler in [(TCP,30960,DirectoryHandler),(TCP,10902,CheckHandler),(UDP,10902,SearchHandler)]:
            server=cls((a.bind,port),handler)
            server.pc_host=a.pc_host;server.pc_port=9900
            server.holds={};server.hold_lock=threading.Lock()
            servers.append(server)
        for server in servers:
            threading.Thread(target=server.serve_forever,daemon=True).start()
            started.append(server)
        print('READY: experimental PC directory bridge; racing compatibility UNTESTED. Use distinct PC/mobile names.',flush=True)
        time.sleep(a.seconds)
    except KeyboardInterrupt:
        pass
    finally:
        for server in started:
            server.shutdown()
        for server in servers:
            server.server_close()


if __name__=='__main__':
    main()
