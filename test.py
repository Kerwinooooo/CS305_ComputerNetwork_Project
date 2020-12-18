import random


def check_sum(segment: bytes):
    i = list(iter(segment))
    if len(i) % 2 == 1:
        i.insert(0, 0)
    j = [i[x:x + 2] for x in range(0, len(i), 2)]
    bytes_sum = sum((x[0] << 8) + x[1] for x in j)
    bytes_sum = (bytes_sum & 0xFFFF) + (bytes_sum >> 16)
    bytes_sum = (bytes_sum & 0xFFFF) + (bytes_sum >> 16)
    return ~bytes_sum & 0xFFFF


if __name__ == '__main__':
    print(check_sum(b'ghe'))
