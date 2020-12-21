import time

from USocket import UnreliableSocket
from segment import *
import math


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
        self._send_to = None
        self._recv_from = None
        self.debug = debug
        #############################################################################
        # TODO: ADD YOUR NECESSARY ATTRIBUTES HERE                                  #
        #############################################################################
        # 是否是客户端
        self.client = None
        # 是否是发起关闭连接
        self.begin_close = None
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
            self.setblocking(True)
            data, addr = self.recvfrom(1024)
            print('recv syn')
            self.client = False
            self.to_address = addr
            flag, seq, ack, length, content = self.from_bytes(data)
            # print(flag, seq, ack, length, content)
            self.setblocking(False)
            # print(flag , SYN , addr , self.to_address)
            if flag == SYN and addr == self.to_address:
                self.ack = seq + 1
                SYNACK_segment = Segment(empty=True, flag=SYN + ACK, seq_num=self.seq, ack_num=self.ack, content=content)
                self.sendto(SYNACK_segment.to_bytes(), addr)
                print('send syn ack')
                break
        print('out')
        while True:
            self.setblocking(False)
            try:
                data, addr = self.recvfrom(1024)
                flag, seq, ack, length, content = self.from_bytes(data)
                # print(flag , ACK , addr , self.to_address)
                if flag == SYN and addr == self.to_address:
                    print('recv syn')
                # print(flag , ACK , addr , self.to_address)
                if flag == ACK and addr == self.to_address:
                    print('recv ack')
                    break
            except BlockingIOError:
                self.sendto(SYNACK_segment.to_bytes(), addr)
                print('send syn ack')
                time.sleep(0.1)
                continue
        print('connection build')
        self.set_send_to(self.sendto, self.to_address)
        self.set_recv_from(self.recvfrom)
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        return self

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
        while True:
            self.setblocking(False)
            SYN_segment = Segment(empty=True, flag=SYN, seq_num=self.seq, ack_num=self.ack)
            self.sendto(SYN_segment.to_bytes(), address)
            print('send syn')
            time.sleep(0.1)
            try:
                data, addr = self.recvfrom(1024)
            except BlockingIOError:
                continue
            flag, seq, ack, length, content = self.from_bytes(data)
            if flag == SYN + ACK and ack == self.seq + 1 and addr == self.to_address:
                print('recv syn ack')
                break
            else:
                print('loss')
        ACK_segment = Segment(empty=True, flag=ACK, seq_num=ack, ack_num=seq + 1, content=content)
        self.sendto(ACK_segment.to_bytes(), self.to_address)
        print('send ack')
        # 定时器防止ack包丢失
        start = time.time()
        end = time.time()
        while end - start < 3:
            end = time.time()
            self.setblocking(False)
            try:
                data, addr = self.recvfrom(1024)
                print('recv syn ack')
            except BlockingIOError:
                continue
            flag, seq, ack, length, content = self.from_bytes(data)
            if flag == SYN + ACK and ack == self.seq + 1 and addr == self.to_address:
                self.sendto(ACK_segment.to_bytes(), addr)
                print('send ack')
        print('connection build')
        self.set_send_to(self.sendto, self.to_address)
        self.set_recv_from(self.recvfrom)
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
        assert self._recv_from, "Connection not established yet. Use recvfrom instead."
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################

        data, socket = self.recvfrom(1024)

        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        return data

    def send(self, bytes: bytes):
        """
        Send data to the socket.
        The socket must be connected to a remote socket, i.e. self._send_to must not be none.
        """
        assert self._send_to, "Connection not established yet. Use sendto instead."
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
        self.begin_close = True
        FIN_segment = Segment(empty=True, flag=FIN, seq_num=self.seq, ack_num=self.ack)
        self._send_to(FIN_segment.to_bytes())
        self._recv_from(1024)
        data, addr = self._recv_from(1024)
        flag, seq, ack, length, content = self.from_bytes(data)
        ACK_segment = Segment(empty=True, flag=FIN, seq_num=ack, ack_num=seq + 1)
        self._send_to(ACK_segment.to_bytes())

        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        super().close()

    # 建立连接后重写send方法
    def set_send_to(self, sendto, addr):
        def get_sent_to(data: bytes):
            sendto(data, addr)

        self._send_to = get_sent_to

    # 建立连接后重写recv方法
    def set_recv_from(self, recv_from):
        def get_recv_from(bufsize):
            data, addr = recv_from(1024)
            if addr != self.to_address:
                pass
            else:
                flag, seq, ack, length, content = self.from_bytes(data)
                # 接收到关闭连接请求
                if flag == FIN and self.begin_close is None:
                    self.begin_close = False
                    ACK_segment = Segment(empty=True, flag=ACK, seq_num=self.seq, ack_num=seq + 1)
                    self._send_to(ACK_segment.to_bytes())
                    FIN_segment = Segment(empty=True, flag=FIN, seq_num=self.seq, ack_num=seq + 1)
                    self._send_to(FIN_segment.to_bytes())
                    self._recv_from(1024)
                    super(RDTSocket, self).close()
                return data, addr

        self._recv_from = get_recv_from

    @staticmethod
    def from_bytes(data: bytes):
        if len(data) < 17:
            pass
        else:
            flag = int.from_bytes(data[0:5], 'big')
            seq = int.from_bytes(data[5:9], 'big')
            ack = int.from_bytes(data[9:13], 'big')
            length = int.from_bytes(data[13:17], 'big')
            content = data[17:]
            return flag, seq, ack, length, content

    """
    You can define additional functions and classes to do thing such as packing/unpacking packets, or threading.
    
    """
