from rdt import RDTSocket

addr1 = ('127.0.0.1', 60)
addr2 = ('127.0.0.1', 70)
addr3 = ('127.0.0.1', 80)
addr4 = ('127.0.0.1', 90)
server_address1 = ('127.0.0.1', 12345)
server_address2 = ('127.0.0.1', 23456)

if __name__ == '__main__':
    socket1 = RDTSocket()
    socket1.bind(addr1)
    socket2 = RDTSocket()
    socket2.bind(addr2)
    client1 = socket1.connect(addr3)
    # f = open('alice.txt', 'rb')
    client1._send_to(b'hello')
    client1._recv_from(1024)
    client1 = socket1.connect(addr3)
