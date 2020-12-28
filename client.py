import time

from rdt import RDTSocket

addr1 = ('127.0.0.1', 6000)
addr2 = ('127.0.0.1', 7000)
addr3 = ('127.0.0.1', 8000)
addr4 = ('127.0.0.1', 9000)
server_address1 = ('127.0.0.1', 12345)
server_address2 = ('127.0.0.1', 23456)

if __name__ == '__main__':
    socket1 = RDTSocket()
    socket1.bind(addr1)
    socket2 = RDTSocket()
    socket2.bind(addr2)
    socket1.connect(addr3)
    socket1.sendto(b'hello')
    socket1.close()
    # while True:
    #     try:
    #         socket1.recv_from(1024)
    #     except OSError:
    #         break
