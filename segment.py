"""
hamming code 有点不切实际， 生成hamming code需要遍历 2^35个bits， 所以我改成了checksum.
rdt.py中的from_bytes我一并改了
segment format:
Checksum| blank | magical_bit | SYN  | FIN | ACK | SEQ   | SEQ_ACK | LEN   | PAYLOAD
1bytes  | 4bit  |     1bit    | 1bit | 1bit| 1bit| 4bytes| 4bytes  |4bytes | LEN bytes
"""

SYN = (1 << 2)
FIN = (1 << 1)
ACK = (1 << 0)


class Segment(object):

    def __init__(self, empty: bool, flag: int, seq_num: int, ack_num: int, content: bytes = ""):
        self.empty = empty
        self.flag: int = flag
        self.seq_num: int = seq_num
        self.ack_num: int = ack_num
        self.length: int = len(content)
        self.content: bytes = content

    @staticmethod
    def Generate_checksum(data: bytes):
        s = sum(a for a in data)
        s = s % 256
        s = 0xFF - s
        return s.to_bytes(1, 'big')

    def Generate_Hamming_code(self):
        pass

    def Check_Hamming_code(self):
        pass

    def error_recovery(self):
        pass

    @staticmethod
    def find_i_number(index: int, data_list: list):
        row = int(index / 8)
        col = index % 8
        if col == 0:
            r_ed = data_list[row][-1]
        else:
            r_ed = data_list[row + 1][col]
        return r_ed

    @staticmethod
    def bitstring_to_bytes(input_str):
        return int(input_str, 2).to_bytes((len(input_str) + 7) // 8, byteorder='big')

    def to_bytes(self):
        # assert self.hamming_code is not None
        if self.empty:
            data: bytes = self.flag.to_bytes(1, 'big') + self.seq_num.to_bytes(4, 'big') + \
                          self.ack_num.to_bytes(4, 'big') + self.length.to_bytes(4, 'big')
        else:
            data: bytes = self.flag.to_bytes(1, 'big') + self.seq_num.to_bytes(4, 'big') + \
                          self.ack_num.to_bytes(4, 'big') + self.length.to_bytes(4, 'big') + \
                          self.content
        data = self.Generate_checksum(data) + data
        return data
