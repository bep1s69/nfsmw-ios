#!/usr/bin/env python3
"""Protocol-boundary checks; synthetic peers cannot prove game cross-play."""
import socket
import struct
import threading
import unittest
from pc_lan_probe import discovery, frame, read_frame
from pc_lan_bridge import relay_directory


class PCProtocol(unittest.TestCase):
    def test_discovery(self):
        data=bytearray(384);data[:8]=b'gEA\x03\x05abc';data[8:15]=b'NFSMWNA'
        data[40:45]=b'Room\0';data[72:79]=b'9900|2\0'
        self.assertEqual(discovery(data)['players'],2)
        self.assertEqual(discovery(data)['port'],9900)
        for bad in [data[:-1],b'NFSMW_SERVER',bytes(384)]:
            with self.assertRaises(ValueError):discovery(bad)
        data[8:15]=b'NFSMWXX'
        with self.assertRaises(ValueError):discovery(data)

    def test_fragmented_frame(self):
        a,b=socket.socketpair()
        payload=frame(b'@dir',b'ADDR=127.0.0.1\tPORT=9900')
        def send():
            for byte in payload:b.sendall(bytes([byte]))
            b.close()
        t=threading.Thread(target=send);t.start()
        with a:
            self.assertEqual(read_frame(a),(b'@dir',bytes(4),b'ADDR=127.0.0.1\tPORT=9900\0'))
        t.join()

    def test_reject_invalid_frame(self):
        for size in [0,11,65537]:
            a,b=socket.socketpair()
            with a,b:
                b.sendall(b'@dir'+bytes(4)+struct.pack('>I',size))
                with self.assertRaises(ValueError):read_frame(a)

    def test_directory_relay_preserves_both_profiles(self):
        for product in [b'nfs-pc-2006',b'nfs-xbox-2006']:
            listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1)
            response=frame(b'@dir',b'ADDR=127.0.0.1\tPORT=9900\tSESS=42\tMASK=abcd')
            observed=[];errors=[]
            def backend():
                try:
                    with listener:
                        peer,_=listener.accept()
                        with peer:
                            observed.append(read_frame(peer));observed.append(read_frame(peer))
                            peer.sendall(response[:5]);peer.sendall(response[5:])
                except Exception as e:errors.append(e)
            t=threading.Thread(target=backend);t.start()
            a,b=socket.socketpair()
            request=frame(b'@tic',b'RC4+MD5-V2')+frame(b'@dir',b'PROD='+product)
            b.sendall(request)
            relay_directory(a,'127.0.0.1',listener.getsockname()[1]);a.close()
            self.assertEqual(read_frame(b),(b'@dir',bytes(4),response[12:]))
            b.close();t.join();self.assertEqual(errors,[])
            self.assertEqual(observed[0][2],b'RC4+MD5-V2\0')
            self.assertEqual(observed[1][2],b'PROD='+product+b'\0')

    def test_reject_non_directory_commands(self):
        a,b=socket.socketpair()
        with a,b:
            b.sendall(frame(b'auth',b'NAME=no'))
            with self.assertRaises(ValueError):relay_directory(a,'127.0.0.1',1)


if __name__=='__main__':
    unittest.main()
