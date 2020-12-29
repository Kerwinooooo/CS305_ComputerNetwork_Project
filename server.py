from network import Server
from rdt import RDTSocket

addr1 = ('127.0.0.1', 6000)
addr2 = ('127.0.0.1', 7000)
addr3 = ('127.0.0.1', 8000)
addr4 = ('127.0.0.1', 9000)
server_address1 = ('127.0.0.1', 12345)
server_address2 = ('127.0.0.1', 23456)

if __name__ == '__main__':
    server = RDTSocket(debug=True)
    server.bind(('127.0.0.1', 9999))
    conn, client_addr = server.accept()
    conn.close()
    conn3, client_addr3 = server.accept()
    # rep = conn.recv(4096)
    # print(rep.decode('utf-8'))