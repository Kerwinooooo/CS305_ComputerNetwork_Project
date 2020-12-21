"""
segment format:
Hamming_code | blank | SYN  | FIN | ACK | SEQ   | SEQ_ACK | LEN   | PAYLOAD
33bits       | 4bit  | 1bit | 1bit| 1bit| 4bytes| 4bytes  |4bytes | LEN bytes
"""

SYN = (1 << 2)
FIN = (1 << 1)
ACK = (1 << 0)


class Segment(object):

    def __init__(self, empty: bool, flag: int, seq_num: int, ack_num: int, content: bytes = ""):
        self.hamming_code = None
        self.empty = empty
        self.flag: int = flag
        self.seq_num: int = seq_num
        self.ack_num: int = ack_num
        self.length: int = len(content)
        self.content: bytes = content

    def Hamming_code(self):
        pass

    def to_bytes(self):
        # assert self.hamming_code is not None
        if self.empty:
            data: bytes = self.flag.to_bytes(5, 'big') + self.seq_num.to_bytes(4, 'big') + \
                          self.ack_num.to_bytes(4, 'big') + self.length.to_bytes(4, 'big')
        else:
            data: bytes = self.flag.to_bytes(5, 'big') + self.seq_num.to_bytes(4, 'big') + \
                          self.ack_num.to_bytes(4, 'big') + self.length.to_bytes(4, 'big') + \
                          self.content
        return data
