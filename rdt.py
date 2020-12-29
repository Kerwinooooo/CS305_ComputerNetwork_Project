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
        self.to_address = None
        self.port = None

        self.TIMEOUT = 1
        self.rtt_list = []
        # self.receive_list = queue.Queue(maxsize=-1)  # TODO: delete
        # queue.empty()
        # queue.put(block=False)
        # queue.get(block=False)
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
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        while True:
            data, addr = self.recvfrom(1024)
            check_sum, flag, seq, ack, length, content = self.from_bytes(data)
            # print(flag, seq, ack, length, content)
            # print(flag , SYN , addr , self.to_address)
            if self.check_checksum(data) and flag == SYN:
                print('recv syn')
                self.client = False
                print(self.to_address)
                self.to_address = addr
                self.ack = seq + 1
                SYNACK_segment = Segment(empty=True, flag=SYN + ACK, seq_num=conn.seq, ack_num=self.ack,
                                         content=content)
                self.sendto(SYNACK_segment.to_bytes(), self.to_address)
                print('send syn ack')
                break
        self.setblocking(False)
        while True:
            try:
                data, addr = self.recvfrom(1024)
                check_sum, flag, seq, ack, length, content = self.from_bytes(data)
                # print(check_sum, flag, ACK, addr, self.to_address)
                if self.check_checksum(data) and flag == SYN and addr == self.to_address:
                    print('recv syn')
                # print(flag , ACK , addr , self.to_address)
                if self.check_checksum(data) and flag == ACK and addr == self.to_address:
                    print('recv ack')
                    break
            except BlockingIOError:
                self.sendto(SYNACK_segment.to_bytes(), self.to_address)
                print('send syn ack')
                time.sleep(frequency)
                continue
        print('connection build')
        time.sleep(time_out)
        self.setblocking(True)
        self.seq = 0
        self.seqack = 0
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
        self.setblocking(False)
        while True:
            SYN_segment = Segment(empty=True, flag=SYN, seq_num=self.seq, ack_num=self.ack)
            self.sendto(SYN_segment.to_bytes(), self.to_address)
            print('send syn')
            time.sleep(frequency)
            try:
                data, addr = self.recvfrom(1024)
            except BlockingIOError:
                continue
            check_sum, flag, seq, ack, length, content = self.from_bytes(data)
            if self.check_checksum(data) and flag == SYN + ACK and ack == self.seq + 1 and addr == self.to_address:
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
                start = time.time()  # TODO: timer更新的时机可能不太对
                print('recv syn ack')
            except BlockingIOError:
                continue
            check_sum, flag, seq, ack, length, content = self.from_bytes(data)
            if self.check_checksum(data) and flag == SYN + ACK and ack == self.seq + 1 and addr == self.to_address:
                self.sendto(ACK_segment.to_bytes(), self.to_address)
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

        Note that ONLY data send by the peer should be accepted.
        In other words, if someone else sends data to you from another address,
        it MUST NOT affect the data returned by this function.
        """
        data_receive = b''
        # TODO: detect whether connection is established
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
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
        count = 0
        while True:
            # RECEIVE SEGMENT
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

            if seqack != segment_received.seq:
                if self.debug: logging.error(
                    'recv(): RECEIVE WRONG SEQ SEQ: {}, LASTSEQACK: {}'.format(segment_received.seq, seqack))
                continue

            if segment_received.LEN == 0:
                if segment_received.magical_bit == 1:  # send先结束
                    magical_segment_ack = RdtSegment(magical_bit=1, ack=1)
                    self.sendto(magical_segment_ack.encode(), self.to_address)
                    timer_start = time.time()
                    while True:
                        if time.time() - timer_start >= self.TIMEOUT:
                            break
                        try:
                            sr, _ = self.receive_something(4096)
                            if self.END:
                                return b''
                            if sr.magical_bit == 1 and sr.ack == 0:
                                self.sendto(magical_segment_ack.encode(), self.to_address)
                                timer_start = time.time()
                        except Exception as e:
                            continue
                    break
                continue
            if segment_received.LEN + len(data_receive) <= bufsize:  # RECEIVE SOME DATA
                data_receive += segment_received.paylaod
                # 回一个包 带seqack
                seqack += len(segment_received.paylaod)
                rep = RdtSegment(ack=1, seq=seq, seqack=seqack)
                print(seq, seqack)
                self.sendto(rep.encode(), self.to_address)

            else:  # recv先结束
                if self.debug: logging.info('recv() end first')
                if bufsize > len(data_receive):
                    data_receive += segment_received.paylaod[:bufsize - len(data_receive)]
                # 回一个特殊标识包 带seqack
                rep = RdtSegment(magical_bit=1, ack=1, seq=seq, seqack=seqack)
                self.sendto(rep.encode(), self.to_address)

                timer_start = time.time()
                while True:  # BIGPROBLEM HOLYSHIT
                    if time.time() - timer_start >= self.TIMEOUT:
                        break
                    try:
                        sr, _ = self.receive_something(4096)
                        if self.END:
                            return b''
                        if sr.magical_bit == 1:
                            # 重发标识包 带seqack
                            self.sendto(rep.encode(), self.to_address)
                            timer_start = time.time()
                    except Exception as e:
                        continue
                seqack += len(segment_received.paylaod)
                break
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        self.seqack = seqack  # UPDATE SEQACK
        return data_receive

    def send(self, bytes: bytes):
        """
        Send data to the socket.
        The socket must be connected to a remote socket, i.e. self._send_to must not be none.
        """
        # assert self._send_to, "Connection not established yet. Use sendto instead."
        # TODO: detect whether connection is established
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
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

        window_left = 0
        window_right = self.window_size
        start_time_list = [time.time() * segment_num]

        recv_END = False
        count = 0
        while True:
            if self.debug:
                logging.info('count: {}'.format(count))
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

                try:  # receive ACK
                    ack, address = self.receive_something()
                    if address[1] == -1:
                        raise Exception('send')

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
                        if self.debug: logging.error('send(): RECEIVE A REPLY WITH NO ACK')
                        raise Exception
                    if ack.seqack == seq_list[count + 1]:
                        # logging.info('ack.seqack == seq_list[count+1] {}  {}'.format(ack.seqack, seq_list[count+1]))
                        # time.sleep(1000)
                        if ack.magical_bit == 1:  # have received magical_bit from recv()
                            recv_END = True
                        self.seq = seq_list[count + 1]  # update seq
                        break
                    else:
                        if self.debug: logging.error('send(): RECEIVE WRONG SEQACK '
                                                     'SEQACK: {}, ACK+LEN: {}'.format(ack.seqack, seq_list[count + 1]))
                except Exception as e:
                    continue

            rtt_1 = time.time() - time_send  # TODO: 是否debug分别处理
            self.rtt_list.append(rtt_1)
            # if len(self.rtt_list) >= 30:
            #     self.rtt_list.pop(__index=0)

            if recv_END:  # recv()已进入结束状态
                logging.error('BBBBBBBBBBBBBBIG PROBLEM')
                # TODO: 定时器

            count += 1
            if count >= segment_num:
                break

        # 发标识包让recv关闭——send()发送标识包，收到recv()返回的标识ack即可退出
        magical_segment = RdtSegment(magical_bit=1, seq=seq_list[-1])
        sr = RdtSegment()
        while True:
            self.sendto(magical_segment.encode(), self.to_address)
            # time.sleep(self.TIMEOUT)  # ################################################################################
            while True:  # TODO: NEED TO UPDATE
                try:
                    sr, _ = self.receive_something(4096)
                    if _[1] == -1:
                        raise Exception('send2')
                    if sr.magical_bit == 1 and sr.ack == 1:
                        break
                except Exception as e:
                    continue  # Original: continue
            if sr.magical_bit == 1 and sr.ack == 1:
                break

        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################

    def receive_something(self, bufsize: int = 4096):
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
        if self.client:
            super().close()

    # def keep_receive(self):
    #     while True:
    #         try:
    #             data, address = super().recvfrom(4096)
    #             data = RdtSegment.decode()
    #             if len(data.payload) != 0 and data.fin != 1:
    #                 self.receive_list.put(data, block=False)
    #             else:
    #                 pass
    #         except Exception as e:
    #             logging.error(e)
    #             continue

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

    # @staticmethod
    # def check_sum(segment: bytes):
    #     i = list(iter(segment))
    #     for x in i:
    #         print(x)
    #     bytes_sum = sum(int.from_bytes(x, 'big') for x in i)
    #     if len(segment) % 2 == 1:
    #         bytes_sum += segment[-1] << 8
    #     bytes_sum = (bytes_sum & 0xFFFF) + (bytes_sum >> 16)
    #     bytes_sum = (bytes_sum & 0xFFFF) + (bytes_sum >> 16)
    #     return ~bytes_sum & 0xFFFF


def get_data_chunks(data: bytes, max_data_length: int):
    try:
        chunks = [data[i: i + max_data_length] for i in range(0, len(data), max_data_length)]
    except Exception as e:
        logging.error('get_data_chunks ERROR: {}'.format(e))
        chunks = []
    return chunks


class RdtSegment:
    magical_bit: int = 0
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
