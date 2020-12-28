from socket import socket, AF_INET, SOCK_DGRAM, inet_aton, inet_ntoa
import random
import time
import threading
import queue
from socketserver import ThreadingUDPServer

lock = threading.Lock()


def bytes_to_addr(bytes):
    return inet_ntoa(bytes[:4]), int.from_bytes(bytes[4:8], 'big')


def addr_to_bytes(addr):
    return inet_aton(addr[0]) + addr[1].to_bytes(4, 'big')


def corrupt(data: bytes) -> bytes:
    raw = list(data)
    for _ in range(0, random.randint(0, 3)):
        pos = random.randint(0, len(raw) - 1)
        raw[pos] = random.randint(0, 255)
    return bytes(raw)


class Server(ThreadingUDPServer):
    def __init__(self, addr, rate=None, delay=None, loss=None):
        super().__init__(addr, None)
        self.rate = rate
        self.buffer = 0
        self.delay = delay
        self.loss = 0

    def verify_request(self, request, client_address):
        """
        request is a tuple (data, socket)
        data is the received bytes object
        socket is new socket created automatically to handle the request

        if this function returns False， the request will not be processed, i.e. is discarded.
        details: https://docs.python.org/3/library/socketserver.html
        """
        if self.buffer < 100000:  # some finite buffer size (in bytes)
            self.buffer += len(request[0])
            return True
        else:
            return False

    def finish_request(self, request, client_address):
        data, socket = request

        with lock:
            if self.rate:
                time.sleep(len(data) / self.rate)
            self.buffer -= len(data)
            """
            blockingly process each request
            you can add random loss/corrupt here

            for example:
            if random.random() < loss_rate:
                return
            for i in range(len(data)-1):
                if random.random() < corrupt_rate:
                    data[i] = data[:i] + (data[i]+1).to_bytes(1,'big) + data[i+1:]
            """

        """
        this part is not blocking and is executed by multiple threads in parallel
        you can add random delay here, this would change the order of arrival at the receiver side.

        for example:
        time.sleep(random.random())
        """

        to = bytes_to_addr(data[:8])
        flag_loss = False
        flag_corrupt = False
        if random.random() < 0.2:
            print(client_address, to, 'loss')  # observe tht traffic
            flag_loss = True
            return
        for i in range(len(data) - 1):
            if random.random() < 0.05:
                flag_corrupt = True
                data = data[:i] + (data[i] + 1).to_bytes(1, 'big') + data[i + 1:]
                print(client_address, to, 'corrupt')  # observe tht traffic
        if not flag_loss and not flag_corrupt:
            print(client_address, to, 'success')
        socket.sendto(addr_to_bytes(client_address) + data[8:], to)


server_address = ('127.0.0.1', 12345)

if __name__ == '__main__':
    with Server(server_address) as server:
        server.serve_forever()
