import socket
import sys
import threading
import base64
import datetime
import traceback
import pickle
from io import BytesIO
import time


class StreamServer:
    host = ''
    port = 1337
    sock = None
    connections = {}
    closed = False
    connections_lock = None
    received_data = False
    poi = []
    poi_lock = threading.Lock()

    def __init__(self, poi):
        self.sock = socket.socket()
        self.poi = poi
        self.sock.bind((self.host, self.port))
        # Set accept timeout to 60 sec
        socket.setdefaulttimeout(30)
        self.connections_lock = threading.Lock()
        self.sock.listen(10)

    def __enter__(self, poi):
        self.sock = socket.socket()
        self.sock.bind((self.host, self.port))
        self.poi = poi
        # Set accept timeout to 60 sec
        socket.setdefaulttimeout(30)
        self.connections_lock = threading.Lock()
        self.sock.listen(10)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.closed = True

    def start(self):
        try:
            while True:
                conn, addr = self.sock.accept()
                if conn is not None and addr is not None:
                    self.connections_lock.acquire()
                    self.connections.update({addr[0]: conn})
                    self.connections_lock.release()
                    client_thread = threading.Thread(target=self.receive_poi, args=(conn, addr))
                    client_thread.daemon = True
                    client_thread.start()
                    print(str(addr) + ' Connected! ' + str(datetime.datetime.now()))
                if self.closed:
                    break

        except Exception as e:
            traceback.print_exc(file=sys.stdout)
        finally:
            self.sock.close()

    def close(self):
        self.closed = True

    def send_data(self, data, conn):
        try:
            data_string = pickle.dumps(data)
            conn.sendall(data_string)
        except socket.error as e:
            print(e.strerror)

    def send_data_to_all(self, data, data2):
        if len(self.connections) > 0:
            buffer = BytesIO()
            buffer2 = BytesIO()
            data.save(buffer, format='JPEG')
            data2.save(buffer2, format='JPEG')
            data_str = base64.b64encode(buffer.getvalue())
            data_str2 = base64.b64encode(buffer2.getvalue())
            send_data = [data_str, data_str2]
            send_data = pickle.dumps(send_data)
            self.connections_lock.acquire()
            disconnected = []
            for addr in self.connections:
                try:
                    self.connections[addr].sendall(send_data)
                except socket.error as e:
                    # Save key if disconnected
                    disconnected.append(addr)
                    print(str(addr) + ' Disconnected!')
            # Delete disconnected addresses
            if len(disconnected) > 0:
                for addr in disconnected:
                    del self.connections[addr]
            self.connections_lock.release()

    def get_poi(self):
        self.poi_lock.acquire()
        saved_poi = self.poi.copy()
        self.received_data = False
        self.poi_lock.release()
        return saved_poi

    def receive_poi(self, conn, addr):
        self.send_data(self.poi, conn)
        try:
            while True:
                chunks = []
                chunk = 0
                try:
                    chunk = conn.recv(4096)
                except socket.error:
                    pass
                finally:
                    if self.closed:
                        break
                    if chunk:
                        chunks.append(chunk)
                        while True:
                            try:
                                conn.settimeout(0.5)
                                chunk = conn.recv(4096)
                                if not chunk:
                                    break
                                chunks.append(chunk)
                            except socket.error:
                                break
                        data = b''.join(chunks)
                        self.poi_lock.acquire()
                        self.poi.clear()
                        self.poi = pickle.loads(data)
                        self.poi_lock.release()
                        self.received_data = True
                        conn.settimeout(10)
                        print('Received new points of interest!')
                    if self.closed:
                        break
        except socket.error as e:
            traceback.print_exc(file=sys.stdout)

