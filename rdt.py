from USocket import UnreliableSocket
import threading
import time
from segment import *
import math
import logging
import queue
import struct
from threading import Lock
import numpy as np

logging.basicConfig(level=logging.NOTSET)

# 超时时间
time_out = 1
# 发送间隔
frequency = 0.05


class RDTSocket(UnreliableSocket):
    """
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
    seq: int
    seqack: int
    max_data_length: int = 2000
    header_length: int = 14
    len_length: int = 4
    seq_length: int = 4
    seqack_length: int = 4
    window_size: int = 10
    lock = Lock()
    END: bool = False

    def __init__(self, rate=None, debug=True):
        super().__init__(rate=rate)
        self._rate = rate
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
        self.seqack = 0  # it is used by zhb
        # 连接的socket的地址
        self.address = None
        self.to_address = None
        self.port = None

        self.TIMEOUT = 0.2
        self.rtt_list = []
        # 连接池的情况
        self.belong_to = None
        self.max_conn = 10
        self.use = []
        for i in range(self.max_conn):
            self.use.append(False)
        self.use_seq = None

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
        conn = RDTSocket(self._rate)
        i = 0
        while self.use[i]:
            i += 1
        conn.bind((self.address[0], self.address[1] + i + 1))
        self.use[i] = True
        conn.use_seq = i
        conn.belong_to = self
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        while True:
            data, addr = self.recvfrom(1024)
            check_sum, flag, seq, ack, length, content = conn.from_bytes(data)
            # print(flag, seq, ack, length, content)
            # print(flag , SYN , addr , self.to_address)
            if conn.check_checksum(data) and flag == SYN:
                print('recv syn')
                conn.client = False
                print(conn.to_address)
                conn.to_address = addr
                conn.ack = seq + 1
                SYNACK_segment = Segment(empty=True, flag=SYN + ACK, seq_num=conn.seq, ack_num=conn.ack,
                                         content=content)
                conn.sendto(SYNACK_segment.to_bytes(), conn.to_address)
                print('send syn ack')
                break
        conn.setblocking(False)
        while True:
            try:
                data, addr = conn.recvfrom(1024)
                check_sum, flag, seq, ack, length, content = conn.from_bytes(data)
                # print(check_sum, flag, ACK, addr, self.to_address)
                if conn.check_checksum(data) and flag == SYN and addr == conn.to_address:
                    print('recv syn')
                # print(flag , ACK , addr , self.to_address)
                if conn.check_checksum(data) and flag == ACK and addr == conn.to_address:
                    print('recv ack')
                    break
            except BlockingIOError:
                conn.sendto(SYNACK_segment.to_bytes(), conn.to_address)
                print('send syn ack')
                time.sleep(frequency)
                continue
        print('connection build')
        time.sleep(time_out)
        conn.setblocking(True)
        conn.seq = 0
        conn.seqack = 0
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        return conn, conn.address

    def connect(self, address: (str, int)):
        """
        Connect to a remote socket at address.
        Corresponds to the process of establishing a connection on the client side.
        """
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        self.client = True
        self.setblocking(False)
        while True:
            SYN_segment = Segment(empty=True, flag=SYN, seq_num=self.seq, ack_num=self.ack)
            self.sendto(SYN_segment.to_bytes(), address)
            print('send syn')
            time.sleep(frequency)
            try:
                data, addr = self.recvfrom(1024)
            except BlockingIOError:
                continue
            check_sum, flag, seq, ack, length, content = self.from_bytes(data)
            if self.check_checksum(data) and flag == SYN + ACK and ack == self.seq + 1:
                self.to_address = addr
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
        self.setblocking(False)
        while end - start < time_out:
            end = time.time()
            try:
                data, addr = self.recvfrom(1024)
                start = time.time()
                print('recv syn ack')
            except BlockingIOError:
                continue
            check_sum, flag, seq, ack, length, content = self.from_bytes(data)
            if self.check_checksum(data) and flag == SYN + ACK and ack == self.seq + 1 and addr == self.to_address:
                self.sendto(ACK_segment.to_bytes(), self.to_address)
                start = time.time()
                print('send ack')
        print('connection build')
        self.setblocking(True)
        self.seq = 0
        self.seqack = 0
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################

    def recv(self, bufsize: int) -> bytes:
        """
        Receive data from the socket.
        The return value is a bytes object representing the data received.
        The maximum amount of data to be received at once is specified by bufsize.
        """
        data_receive = b''

        self.setblocking(False)
        # CLEAR BUFFER
        while True:
            try:
                temp = self.recvfrom(bufsize)
            except Exception as e:
                break
        if self.debug: logging.info("RECEIVE BUFFER CLEAR: recv()")

        seq = self.seq
        seqack = self.seqack
        while True:
            # RECEIVE PACKET
            self.setblocking(False)
            try:
                segment_received, address = self.receive_something(bufsize=bufsize)
                if self.END:
                    return b''
            except Exception as e:
                continue

            # PRINT WHAT RECEIVE
            if self.debug:
                logging.info('recv(): RECEIVE A PACKET FROM {}: MAGICAL_BIT: {}, '
                             'SYN: {}, FIN: {}, ACK: {}, '
                             'SEQ: {}, SEQACK: {}, LEN: {}'.format(
                                address,
                                segment_received.magical_bit, segment_received.syn,
                                segment_received.fin, segment_received.ack,
                                segment_received.seq, segment_received.seqack,
                                segment_received.LEN))

            if seqack != segment_received.seq:  # TODO: 可以发以前seq的回包
                if self.debug: logging.error(
                    'recv(): RECEIVE WRONG SEQ SEQ: {}, LASTSEQACK: {}'.format(segment_received.seq, seqack))
                if seqack > segment_received.seq:
                    rep = RdtSegment(ack=1, seq=seq, seqack=segment_received.LEN + segment_received.seq)
                    self.sendto(rep.encode(), self.to_address)
                continue

            if segment_received.LEN == 0:
                if segment_received.magical_bit == 1 and segment_received.ack == 0:  # send() WANT TO END
                    magical_segment_ack = RdtSegment(magical_bit=1, ack=1)
                    self.setblocking(False)
                    self.sendto(magical_segment_ack.encode(), self.to_address)
                    time_send = time.time()
                    while time.time() - time_send < 2 * self.TIMEOUT:
                        try:
                            sr, _ = self.receive_something(4096)
                            if self.END:
                                return b''
                            if sr.magical_bit == 1 and sr.ack == 0:
                                self.sendto(magical_segment_ack.encode(), self.to_address)
                                time_send = time.time()
                            continue
                        except Exception as e:
                            continue
                    break
                continue

            if segment_received.LEN + len(data_receive) <= bufsize:  # RECEIVE SOME DATA
                data_receive += segment_received.paylaod
                # SEND PACKET WITH SEQACK
                seqack += len(segment_received.paylaod)
                rep = RdtSegment(ack=1, seq=seq, seqack=seqack)
                # TIMER TO MAKE SURE ACK IS RECEIVED
                self.setblocking(False)
                self.sendto(rep.encode(), self.to_address)
                time_send = time.time()
                while time.time() - time_send < 2 * self.TIMEOUT:
                    try:
                        sr, _ = self.receive_something(4096)
                        if self.END:
                            return b''
                        if sr.LEN != 0 and seqack - len(segment_received.paylaod) == sr.seq:
                            self.sendto(rep.encode(), self.to_address)
                            time_send = time.time()
                        continue
                    except Exception as e:
                        continue
            else:  # recv() WANT TO END
                if self.debug: logging.info('recv() end first')
                if bufsize > len(data_receive):
                    data_receive += segment_received.paylaod[:bufsize - len(data_receive)]
                # SEND A PACKET WITH INFORMATION OF END TRANSMISSION AND SEQACK
                rep = RdtSegment(magical_bit=1, ack=1, seq=seq, seqack=seqack)
                self.settimeout(self.TIMEOUT)
                while True:
                    self.sendto(rep.encode(), self.to_address)
                    try:
                        sr, _ = self.receive_something(4096)
                        if self.END:
                            return b''
                        if sr.magical_bit == 1:
                            break
                    except Exception as e:
                        continue

                seqack += len(segment_received.paylaod)
                break

        self.seqack = seqack  # UPDATE SEQACK
        if self.debug: logging.info('recv() END')
        return data_receive

    def send(self, bytes: bytes):
        """
        Send data to the socket.
        The socket must be connected to a remote socket, i.e. self._send_to must not be none.
        """

        self.setblocking(False)
        # CLEAR BUFFER
        while True:
            try:
                temp = self.recvfrom(4096)
            except Exception as e:
                break
        if self.debug: logging.info("RECEIVE BUFFER CLEAR: send()")

        seq = self.seq
        seqack = self.seqack
        payload_list = get_data_chunks(bytes, self.max_data_length)
        segment_num = len(payload_list)

        seq_list = []
        for i in range(segment_num):
            seq_list.append(seq)
            seq += len(payload_list[i])
        seq_list.append(seq)

        recv_END = False
        count = 0
        while True:
            data_segment = RdtSegment(seq=seq_list[count], seqack=seqack, payload=payload_list[count])
            while True:
                self.sendto(data_segment.encode(), self.to_address)
                time_send = time.time()

                # PRINT WHAT SEND
                if self.debug:
                    logging.info('send(): SEND A PACKET: MAGICAL_BIT: {}, '
                                 'SYN: {}, FIN: {}, ACK: {}, '
                                 'SEQ: {}, SEQACK: {}, LEN: {}'.format(
                                    data_segment.magical_bit, data_segment.syn,
                                    data_segment.fin, data_segment.ack,
                                    data_segment.seq, data_segment.seqack,
                                    data_segment.LEN))
                    logging.info('PAYLOAD: {}'.format(data_segment.paylaod))

                try:  # TRY TO RECEIVE ACK PACKET
                    ack, address = self.receive_something()

                    # PRINT WHAT RECEIVE
                    if self.debug:
                        logging.info('send(): RECEIVE A PACKET FROM {}: MAGICAL_BIT: {}, '
                                     'SYN: {}, FIN: {}, ACK: {}, '
                                     'SEQ: {}, SEQACK: {}, LEN: {}'.format(
                                        address,
                                        ack.magical_bit, ack.syn,
                                        ack.fin, ack.ack,
                                        ack.seq, ack.seqack,
                                        ack.LEN))
                        logging.info('PAYLOAD: {}'.format(ack.paylaod))

                    if ack.ack != 1:
                        if self.debug: logging.warning('send(): RECEIVE A REPLY WITH NO ACK')
                        if ack.LEN == 0 and ack.magical_bit == 1:
                            if self.debug: logging.warning('send(): THERE IS TOO MANY PACKET LOSS(the timer in recv() may broke down)')
                            timeout_process = RdtSegment(magical_bit=1, ack=1)
                            self.sendto(timeout_process.encode(), self.to_address)
                        raise Exception

                    if ack.seqack == seq_list[count + 1]:
                        if ack.magical_bit == 1:  # have received magical_bit from recv()
                            recv_END = True
                        self.seq = seq_list[count + 1]  # UPDATE SEQ
                        break
                    else:
                        if self.debug: logging.error('send(): RECEIVE WRONG SEQACK '
                                                     'SEQACK: {}, ACK+LEN: {}'.format(ack.seqack, seq_list[count + 1]))
                except Exception as e:
                    continue

            # rtt_1 = time.time() - time_send
            # self.rtt_list.append(rtt_1)

            if recv_END:  # recv()已进入结束状态
                if self.debug: logging.info('send(): recv want to end first')
                break

            count += 1
            if count >= segment_num:
                break

        if not recv_END:
            # 发标识包让recv关闭——send()发送标识包，收到recv()返回的标识ack即可退出
            magical_segment = RdtSegment(magical_bit=1, seq=seq_list[-1])
            self.settimeout(self.TIMEOUT)
            while True:
                self.sendto(magical_segment.encode(), self.to_address)
                try:
                    sr, _ = self.receive_something(4096)
                    if self.END:
                        return
                    if sr.magical_bit == 1 and sr.ack == 1:
                        break
                except Exception as e:
                    continue
        elif recv_END:
            # recv()已进入结束状态--send()发送标识包并等待timeout
            mb_ack = RdtSegment(magical_bit=1, seq=seq_list[count + 1], seqack=seqack)
            self.setblocking(False)
            self.sendto(mb_ack.encode(), self.to_address)
            time_send = time.time()
            while time.time() - time_send < 2 * self.TIMEOUT:
                try:
                    sr, _ = self.receive_something(4096)
                    if self.END:
                        return b''
                    if sr.ack == 1 and sr.magical_bit == 1:
                        self.sendto(mb_ack.encode(), self.to_address)
                        time_send = time.time()
                    continue
                except Exception as e:
                    continue

        if self.debug: logging.info('send() END')
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################

    def receive_something(self, bufsize: int = 4096):
        """
            RECEVIE A PACKET
            CHECK ADDRESS & LENGTH && CHECKSUM
            RETURN A 'RDTSEGMENT'
        """
        data, address = self.recvfrom(bufsize)

        # CHECK SEGMENT SOURCE
        if address[0] != self.to_address[0] or address[1] != self.to_address[1]:
            raise Exception('Packet from Unknown Source')

        # CHECK SEGMENT LENGTH
        if len(data) < self.header_length:
            raise Exception('Received segment is too short')

        segment_received = RdtSegment.decode(data)
        # CHECK CHECKSUM
        if not segment_received.check_checksum():
            raise Exception('checksum is wrong')

        if segment_received.fin == 1:
            self.END = True

        return segment_received, address

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
                self.sendto(FIN_segment.to_bytes(), self.to_address)
                time.sleep(frequency)
                print('send fin')
                try:
                    data, addr = self.recvfrom(1024)
                    check_sum, flag, seq, ack, length, content = self.from_bytes(data)
                    print('recv ack')
                    if self.check_checksum(data) and flag == ACK and addr == self.to_address:
                        break
                except BlockingIOError:
                    continue
            while True:
                try:
                    data, addr = self.recvfrom(1024)
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
                    data, addr = self.recvfrom(1024)
                    start = time.time()
                    print('recv fin')
                    check_sum, flag, seq, ack, length, content = self.from_bytes(data)
                    ACK_segment = Segment(empty=True, flag=ACK, seq_num=ack, ack_num=seq + 1)
                    self.sendto(ACK_segment.to_bytes(), self.to_address)
                    time.sleep(frequency)
                    print('send ack')
                except BlockingIOError:
                    continue
            print('connection close')
        if not self.client:
            # 接收到关闭连接请求
            while True:
                try:
                    data, addr = self.recvfrom(1024)
                    check_sum, flag, seq, ack, length, content = self.from_bytes(data)
                    if flag == FIN:
                        ACK_segment = Segment(empty=True, flag=ACK, seq_num=self.seq, ack_num=seq + 1)
                        self.sendto(ACK_segment.to_bytes(), self.to_address)
                        break
                except Exception as e:
                    continue
            start = time.time()
            end = time.time()
            while end - start < 1:
                end = time.time()
                self.setblocking(False)
                try:
                    self.recvfrom(1024)
                    start = time.time()
                    print('recv fin')
                except BlockingIOError:
                    continue
                self.sendto(ACK_segment.to_bytes(), self.to_address)
                time.sleep(0.1)
                print('send ack')
            while True:
                FIN_segment = Segment(empty=True, flag=FIN, seq_num=self.seq, ack_num=seq + 1)
                self.sendto(FIN_segment.to_bytes(), self.to_address)
                time.sleep(frequency)
                print('send fin')
                try:
                    data, addr = self.recvfrom(1024)
                    print('recv ack')
                    check_sum, flag, seq, ack, length, content = self.from_bytes(data)
                    if flag == ACK and ack == self.seq + 1 and addr == self.to_address:
                        break
                except BlockingIOError:
                    continue
            print('connection close')
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        self.setblocking(True)
        if not self.client:
            self.belong_to.use[self.use_seq] = False
        super().close()

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

    def bind(self, address: (str, int)):
        self.address = address
        super(RDTSocket, self).bind(address)


def get_data_chunks(data: bytes, max_data_length: int):
    try:
        chunks = [data[i: i + max_data_length] for i in range(0, len(data), max_data_length)]
    except Exception as e:
        logging.error('get_data_chunks ERROR: {}'.format(e))
        chunks = []
    return chunks


class RdtSegment:
    magical_bit: int = 0  # 用于确认传输结束
    syn: int = 0
    fin: int = 0
    ack: int = 0
    seq: int = 0
    seqack: int = 0
    LEN: int = 0
    paylaod: bytes = b''
    checksum: int = None
    header_length: int = 14

    def __init__(self, magical_bit: int = 0, syn: int = 0, fin: int = 0, ack: int = 0,
                 seq: int = 0, seqack: int = 0, LEN: int = -1,
                 payload: bytes = b'', checksum: int = None):
        self.magical_bit = magical_bit
        self.syn = syn
        self.fin = fin
        self.ack = ack
        self.seq = seq
        self.seqack = seqack
        self.paylaod = payload
        if LEN == -1:
            self.LEN = len(self.paylaod)
        else:
            self.LEN = LEN
        if checksum:
            self.checksum = checksum
        else:
            self.checksum = self.generate_checksum()  # 自己算

    def set_status(self, syn=None, fin=None, ack=None, seq=None, seqack=None):
        if ack:
            self.ack = ack
        if syn:
            self.syn = syn
        if ack:
            self.fin = fin
        if seq:
            self.seq = seq
        if seqack:
            self.seqack = seqack

    def get_status(self) -> tuple:
        return self.magical_bit, self.syn, self.fin, self.ack, self.seq, self.seqack

    def generate_checksum(self) -> int:
        s = sum(a for a in self.paylaod)
        s = s + (self.magical_bit << 3) + (self.syn << 2) + (self.fin << 1) + self.ack
        s = s + ((self.seq & 0xFF000000) >> 24) + ((self.seq & 0x00FF0000) >> 16) + \
            ((self.seq & 0x0000FF00) >> 8) + (self.seq & 0x000000FF)
        s = s + ((self.seqack & 0xFF000000) >> 24) + ((self.seqack & 0x00FF0000) >> 16) + \
            ((self.seqack & 0x0000FF00) >> 8) + (self.seqack & 0x000000FF)
        s = s + ((self.LEN & 0xFF000000) >> 24) + ((self.LEN & 0x00FF0000) >> 16) + \
            ((self.LEN & 0x0000FF00) >> 8) + (self.LEN & 0x000000FF)
        s = s % 256
        s = 0xFF - s
        return s

    def check_checksum(self) -> bool:
        return self.checksum == self.generate_checksum()

    def header_encode(self) -> bytes:
        onebyte = 0x00
        if self.magical_bit == 1:
            onebyte = onebyte | 0x08
        if self.syn == 1:
            onebyte = onebyte | 0x04
        if self.fin == 1:
            onebyte = onebyte | 0x02
        if self.ack == 1:
            onebyte = onebyte | 0x01

        header = int(self.checksum).to_bytes(1, 'big') + \
                 int(onebyte).to_bytes(1, 'big') + \
                 int(self.seq).to_bytes(4, 'big') + \
                 int(self.seqack).to_bytes(4, 'big') + \
                 int(self.LEN).to_bytes(4, 'big')
        return header

    def encode(self) -> bytes:
        if isinstance(self.paylaod, bytes):
            return self.header_encode() + self.paylaod
        else:
            return self.header_encode() + int(self.paylaod).to_bytes(1, 'big')

    @classmethod
    def decode(cls, data: bytes) -> 'RdtSegment':  # 调用之前确保data长于14bytes
        checksum = data[0]
        magical_bit = (data[1] & 0x08) >> 3
        syn = (data[1] & 0x04) >> 2
        fin = (data[1] & 0x02) >> 1
        ack = data[1] & 0x01
        seq, = struct.unpack('!L', data[2:6])
        seqack, = struct.unpack('!L', data[6:10])
        LEN, = struct.unpack('!L', data[10:14])
        payload = data[14:]
        return cls(magical_bit=magical_bit, syn=syn, fin=fin, ack=ack,
                   seq=seq, seqack=seqack, LEN=LEN,
                   payload=payload, checksum=checksum)
