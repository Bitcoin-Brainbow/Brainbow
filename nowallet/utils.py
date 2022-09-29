import binascii
import datetime

import json
import blockcypher
BLOCK_CYPHER_TOKEN = "2ae45fa90753473bb2b40c56f062bf80"
BLOCK_CYPHER_COIN = 'btc-testnet' # 'btc' #


def get_timestamp_from_block_header(block_header):
    """ https://en.bitcoin.it/wiki/Protocol_documentation#Block_Headers
    """
    raw_timestamp = block_header[(4+32+32)*2:(4+32+32+4)*2]
    byte_timestamp = bytes(raw_timestamp,'utf-8')
    ba = binascii.a2b_hex(byte_timestamp)
    int_timestamp = int.from_bytes(ba, byteorder='little', signed=True)
    return datetime.datetime.fromtimestamp(int_timestamp)




def decodetx(tx, sort_keys=True):
    """
    # Successfully installed bitcoin-1.1.39 blockcypher-1.0.93 python-dateutil-2.8.2
    https://www.blockcypher.com/dev/bitcoin/?python#push-raw-transaction-endpoint
    """
    parsed = blockcypher.decodetx(tx_hex=tx, coin_symbol=BLOCK_CYPHER_COIN,
                                            api_key=BLOCK_CYPHER_TOKEN)
    try:
        ans = json.dumps(parsed, indent=4, sort_keys=sort_keys)
        print(ans)
        print(parsed)
    except:
        print(parsed)

def get_block_height():
    return blockcypher.get_latest_block_height(coin_symbol=BLOCK_CYPHER_COIN,
                                                   api_key=BLOCK_CYPHER_TOKEN)
