from USocket import UnreliableSocket
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
        # True:client ,False:server
        self.client = None
        self.begin_close = None
        self.sockets = {}
        self.socket_use = []
        self.ssl = 0
        self.ISN = 0
        self.port = None
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
        data, addr = self.recvfrom(1024)
        new_socket = RDTSocket()
        new_socket.client = False
        new_socket.bind(('127.0.0.1', 81))
        new_socket.sendto(b'ack syn', addr)
        data, addr = new_socket.recvfrom(1024)
        if data == b'ack':
            pass
        new_socket.set_send_to(new_socket.sendto, addr)
        new_socket.set_recv_from(new_socket.recvfrom)
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        return new_socket

    def connect(self, address: (str, int)):
        """
        Connect to a remote socket at address.
        Corresponds to the process of establishing a connection on the client side.
        """
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        new_socket = RDTSocket()
        new_socket.client = True
        new_socket.bind(('127.0.0.1', 61))
        new_socket.sendto(b'syn', address)
        data, addr = new_socket.recvfrom(1024)
        if data == b'ack syn':
            new_socket.sendto(b'ack', addr)
        new_socket.set_send_to(new_socket.sendto, addr)
        new_socket.set_recv_from(new_socket.recvfrom)
        # raise NotImplementedError()
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        return new_socket

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
        segments = self.segment(bytes, 1000)
        for i in segments:
            self._send_to(segments)
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################

    def close(self):
        """
        Finish the connection and release resources. For simplicity, assume that
        after a socket is closed, neither further sends nor receives are allowed.
        """
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        if self.begin_close is None:
            self.begin_close = True
            self._send_to(b'fin')
            self._recv_from(1024)
            self._recv_from(1024)
            self._send_to(b'ack')
        else:
            self._send_to(b'ack')
            self._send_to(b'fin')
            self._recv_from(1024)

        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        super().close()

    def set_send_to(self, sendto, addr):
        def get_sent_to(data: bytes):
            sendto(data, addr)

        self._send_to = get_sent_to

    def set_recv_from(self, recv_from):
        def get_recv_from(bufsize):
            data, addr = recv_from(1024)
            if data == b'fin' and self.begin_close is None:
                self.begin_close = False
                self.close()
            return data, addr

        self._recv_from = get_recv_from

    '''
    segment format:
    blank SYN  FIN  ACK  SEQ    SEQACK LEN    CHECKSUM PAYLOAD
    5bit  1bit 1bit 1bit 4bytes 4bytes 4bytes 2bytes   LEN bytes
    '''

    def segment(self, data: bytes, packet_size):
        segments = []
        cnt = math.ceil(len(data) / packet_size)
        for i in (0, cnt + 1):
            segments[i] = data[packet_size * i: packet_size * (i + 1)]
            segments[i] = int(0b001).to_bytes(1, 'big') + int(i).to_bytes(4, 'big') + int(0).to_bytes(4, 'big') + \
                          self.check_sum(segments[i]).to_bytes(2, 'big') + packet_size.to_bytes(4, 'big') + segments[i]
        return segments

    @staticmethod
    def check_sum(segment: bytes):
        i = list(iter(segment))
        for x in i:
            print(x)
        bytes_sum = sum(int.from_bytes(x, 'big') for x in i)
        if len(segment) % 2 == 1:
            bytes_sum += segment[-1] << 8
        bytes_sum = (bytes_sum & 0xFFFF) + (bytes_sum >> 16)
        bytes_sum = (bytes_sum & 0xFFFF) + (bytes_sum >> 16)
        return ~bytes_sum & 0xFFFF



"""
You can define additional functions and classes to do thing such as packing/unpacking packets, or threading.

"""
