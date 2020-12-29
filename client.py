import time

from rdt import RDTSocket

addr1 = ('127.0.0.1', 6000)
addr2 = ('127.0.0.1', 7000)
addr3 = ('127.0.0.1', 8000)
addr4 = ('127.0.0.1', 9000)
server_address1 = ('127.0.0.1', 12345)
server_address2 = ('127.0.0.1', 23456)

if __name__ == '__main__':
    client = RDTSocket(debug=True)
    client2 = RDTSocket(debug=True)
    client.connect(('127.0.0.1', 9999))
    print(1)
    time.sleep(5)
    client2.connect(('127.0.0.1', 9999))
    print(2)
