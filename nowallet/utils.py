import binascii
import datetime

def get_timestamp_from_block_header(block_header):
    """ https://en.bitcoin.it/wiki/Protocol_documentation#Block_Headers
    """
    raw_timestamp = block_header[(4+32+32)*2:(4+32+32+4)*2]
    byte_timestamp = bytes(raw_timestamp,'utf-8')
    ba = binascii.a2b_hex(byte_timestamp)
    int_timestamp = int.from_bytes(ba, byteorder='little', signed=True)
    return datetime.datetime.fromtimestamp(int_timestamp)
