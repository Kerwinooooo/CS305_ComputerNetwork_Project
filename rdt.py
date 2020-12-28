import time

from USocket import UnreliableSocket
from segment import *
import math

# 超时时间
time_out = 1
# 发送间隔
frequency = 0.05


class RDTSocket(UnreliableSocket):
    """。，
    The functions with which you are to build your RDT.
    -   recvfrom(bufsize)->bytes, addr
    -   sendto(bytes, address)
    -   bind(address)

    You can set the mode of the socket.
    -   settimeout(timeout)
    -   setblocking(flag)
    By default, a socket is created in the blocking mode.
    https://docs.python.org/3/library/socket.html#socket-timeouts
    """

    def __init__(self, rate=None, debug=True):
        super().__init__(rate=rate)
        self._rate = rate
        self.recv_from = None
        self.debug = debug
        #############################################################################
        # TODO: ADD YOUR NECESSARY ATTRIBUTES HERE                                  #
        #############################################################################
        # 是否是客户端
        self.client = None
        # 是否是可以关闭连接
        self.can_be_close = None
        # 拥塞控制
        self.cwnd = 1
        self.ssl = 0
        # 初始seq,ack
        self.ISN = 0
        self.seq = 0
        self.ack = 0
        # 连接的socket的地址
        self.to_address = None
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################

    def accept(self) -> ('RDTSocket', (str, int)):
        """
        Accept a connection. The socket must be bound to an address and listening for
        connections. The return value is a pair (conn, address) where conn is a new
        socket object usable to send and receive data on the connection, and address
        is the address bound to the socket on the other end of the connection.

        This function should be blocking.
        """
        conn, addr = RDTSocket(self._rate), None
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        while True:
            data, addr = self.recvfrom(1024)
            print('recv syn')
            check_sum, flag, seq, ack, length, content = self.from_bytes(data)
            # print(flag, seq, ack, length, content)
            # print(flag , SYN , addr , self.to_address)
            if self.check_checksum(data) and flag == SYN:
                self.client = False
                self.to_address = addr
                self.set_send_to(self.sendto, self.to_address)
                self.set_recv_from(self.recvfrom)
                self.ack = seq + 1
                SYNACK_segment = Segment(empty=True, flag=SYN + ACK, seq_num=self.seq, ack_num=self.ack,
                                         content=content)
                self.sendto(SYNACK_segment.to_bytes())
                print('send syn ack')
                break
        self.setblocking(False)
        while True:
            try:
                data, addr = self.recv_from(1024)
                check_sum, flag, seq, ack, length, content = self.from_bytes(data)
                # print(check_sum, flag, ACK, addr, self.to_address)
                if self.check_checksum(data) and flag == SYN and addr == self.to_address:
                    print('recv syn')
                # print(flag , ACK , addr , self.to_address)
                if self.check_checksum(data) and flag == ACK and addr == self.to_address:
                    print('recv ack')
                    break
            except BlockingIOError:
                self.sendto(SYNACK_segment.to_bytes())
                print('send syn ack')
                time.sleep(frequency)
                continue
        print('connection build')
        time.sleep(time_out)
        self.setblocking(True)
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        return self, self.to_address

    def connect(self, address: (str, int)):
        """
        Connect to a remote socket at address.
        Corresponds to the process of establishing a connection on the client side.
        """
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        self.client = True
        self.to_address = address
        self.set_send_to(self.sendto, self.to_address)
        self.set_recv_from(self.recvfrom)
        self.setblocking(False)
        while True:
            SYN_segment = Segment(empty=True, flag=SYN, seq_num=self.seq, ack_num=self.ack)
            self.sendto(SYN_segment.to_bytes())
            print('send syn')
            time.sleep(frequency)
            try:
                data, addr = self.recv_from(1024)
            except BlockingIOError:
                continue
            check_sum, flag, seq, ack, length, content = self.from_bytes(data)
            if self.check_checksum(data) and flag == SYN + ACK and ack == self.seq + 1 and addr == self.to_address:
                print('recv syn ack')
                break
            else:
                print('loss')
        ACK_segment = Segment(empty=True, flag=ACK, seq_num=ack, ack_num=seq + 1, content=content)
        self.sendto(ACK_segment.to_bytes())
        print('send ack')
        # 定时器防止ack包丢失
        start = time.time()
        end = time.time()
        self.setblocking(False)
        while end - start < time_out:
            end = time.time()
            try:
                data, addr = self.recv_from(1024)
                start = time.time()
                print('recv syn ack')
            except BlockingIOError:
                continue
            check_sum, flag, seq, ack, length, content = self.from_bytes(data)
            if self.check_checksum(data) and flag == SYN + ACK and ack == self.seq + 1 and addr == self.to_address:
                self.sendto(ACK_segment.to_bytes())
                print('send ack')
        print('connection build')
        self.setblocking(True)
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################

    def recv(self, bufsize: int) -> bytes:
        """
        Receive data from the socket.
        The return value is a bytes object representing the data received.
        The maximum amount of data to be received at once is specified by bufsize.

        Note that ONLY data send by the peer should be accepted.
        In other words, if someone else sends data to you from another address,
        it MUST NOT affect the data returned by this function.
        """
        data = None
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################

        data, socket = self.recv_from(1024)

        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        return data

    def send(self, bytes: bytes):
        """
        Send data to the socket.
        The socket must be connected to a remote socket, i.e. self._send_to must not be none.
        """
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################

        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################

    # 发起关闭连接请求
    def close(self):
        """
        Finish the connection and release resources. For simplicity, assume that
        after a socket is closed, neither further sends nor receives are allowed.
        """
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        if self.client:
            self.setblocking(False)
            while True:
                FIN_segment = Segment(empty=True, flag=FIN, seq_num=self.seq, ack_num=self.ack)
                self.sendto(FIN_segment.to_bytes())
                time.sleep(frequency)
                print('send fin')
                try:
                    data, addr = self.recv_from(1024)
                    check_sum, flag, seq, ack, length, content = self.from_bytes(data)
                    print('recv ack')
                    if self.check_checksum(data) and flag == ACK and addr == self.to_address:
                        break
                except BlockingIOError:
                    continue
            while True:
                try:
                    data, addr = self.recv_from(1024)
                    check_sum, flag, seq, ack, length, content = self.from_bytes(data)
                    if self.check_checksum(data) and flag == ACK and addr == self.to_address:
                        print('recv ack')
                        continue
                    if self.check_checksum(data) and flag == FIN and addr == self.to_address:
                        print('recv fin')
                        break
                except BlockingIOError:
                    continue
            start = time.time()
            end = time.time()
            while end - start < time_out:
                end = time.time()
                try:
                    data, addr = self.recv_from(1024)
                    start = time.time()
                    print('recv fin')
                    check_sum, flag, seq, ack, length, content = self.from_bytes(data)
                    ACK_segment = Segment(empty=True, flag=ACK, seq_num=ack, ack_num=seq + 1)
                    self.sendto(ACK_segment.to_bytes())
                    time.sleep(frequency)
                    print('send ack')
                except BlockingIOError:
                    continue
            print('connection close')
        if not self.client:
            # 接收到关闭连接请求
            while True:
                try:
                    data, addr = self.recv_from(1024)
                    check_sum, flag, seq, ack, length, content = self.from_bytes(data)
                    if flag == FIN:
                        ACK_segment = Segment(empty=True, flag=ACK, seq_num=self.seq, ack_num=seq + 1)
                        self.sendto(ACK_segment.to_bytes())
                        break
                except TypeError:
                    continue
            start = time.time()
            end = time.time()
            while end - start < 1:
                end = time.time()
                self.setblocking(False)
                try:
                    self.recv_from(1024)
                    start = time.time()
                    print('recv fin')
                except BlockingIOError:
                    continue
                self.sendto(ACK_segment.to_bytes())
                time.sleep(0.1)
                print('send ack')
            while True:
                FIN_segment = Segment(empty=True, flag=FIN, seq_num=self.seq, ack_num=seq + 1)
                self.sendto(FIN_segment.to_bytes())
                time.sleep(frequency)
                print('send fin')
                try:
                    data, addr = self.recv_from(1024)
                    print('recv ack')
                    check_sum, flag, seq, ack, length, content = self.from_bytes(data)
                    if flag == ACK and ack == self.seq + 1 and addr == self.to_address:
                        break
                except BlockingIOError:
                    continue
            print('connection close')
            super(RDTSocket, self).close()

        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        super().close()

    # 建立连接后重写发送方法
    def set_send_to(self, sendto, addr):
        def get_sent_to(data: bytes):
            sendto(data, addr)

        self.sendto = get_sent_to

    # 建立连接后重写接收方法
    def set_recv_from(self, recv_from):
        def get_recv_from(bufsize):
            data, addr = recv_from(1024)
            if addr != self.to_address:
                pass
            return data, addr

        self.recv_from = get_recv_from

    @staticmethod
    def from_bytes(data: bytes):
        check_sum = data[0]
        flag = data[1]
        seq = int.from_bytes(data[2:6], 'big')
        ack = int.from_bytes(data[6:10], 'big')
        length = int.from_bytes(data[10:14], 'big')
        content = data[14:]
        return check_sum, flag, seq, ack, length, content

    def check_checksum(self, data: bytes):
        i = data[0].to_bytes(1, 'big')
        j = self.generate_checksum(data[1:])
        return i == j

    @staticmethod
    def generate_checksum(data: bytes):
        s = sum(a for a in data)
        s = s % 256
        s = 0xFF - s
        return s.to_bytes(1, 'big')

    """
    You can define additional functions and classes to do thing such as packing/unpacking packets, or threading.
    """
