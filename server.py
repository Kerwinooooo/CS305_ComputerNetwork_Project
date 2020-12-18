from network import Server
from rdt import RDTSocket

addr1 = ('127.0.0.1', 60)
addr2 = ('127.0.0.1', 70)
addr3 = ('127.0.0.1', 80)
addr4 = ('127.0.0.1', 90)
server_address1 = ('127.0.0.1', 12345)
server_address2 = ('127.0.0.1', 23456)

if __name__ == '__main__':
    socket1 = RDTSocket()
    socket1.bind(addr3)
    socket2 = RDTSocket()
    socket2.bind(addr4)
    # server1 = Server(server_address1)
    # server1.serve_forever()
    server1 = socket1.accept()
    server1._recv_from(1024)
    server1.close()
    server1 = socket1.accept()
