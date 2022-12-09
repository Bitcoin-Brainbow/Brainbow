from logger import logging
import binascii
import datetime
import time
import json
import blockcypher
from functools import wraps
from typing import Callable
BLOCK_CYPHER_TOKEN = "2ae45fa90753473bb2b40c56f062bf80"
BLOCK_CYPHER_COIN = 'btc-testnet' # 'btc' #


def utxo_deduplication(utxos):
    dedup_utxos_text = []
    dedup_utxos = []
    for spendable in utxos:
        if spendable.as_text() not in dedup_utxos_text:
            dedup_utxos_text.append(spendable.as_text())
            dedup_utxos.append(spendable)
    return dedup_utxos # type: pycoin.tx.Spendable.Spendable 

def log_time_elapsed(func: Callable) -> Callable:
    """ Decorator. Times completion of function and logs at level INFO. """
    @wraps(func)
    def inner(*args, **kwargs) -> None:
        """ Decorator inner function. """
        start_time = time.time()  # type: float
        func(*args, **kwargs)
        end_time = time.time()  # type: float
        seconds = end_time - start_time  # type: float
        logging.info("Operation completed in {0:.3f} seconds".format(seconds))
    return inner

def get_timestamp_from_block_header(block_header):
    """ https://en.bitcoin.it/wiki/Protocol_documentation#Block_Headers
    """
    raw_timestamp = block_header[(4+32+32)*2:(4+32+32+4)*2]
    byte_timestamp = bytes(raw_timestamp,'utf-8')
    ba = binascii.a2b_hex(byte_timestamp)
    int_timestamp = int.from_bytes(ba, byteorder='little', signed=True)
    return datetime.datetime.fromtimestamp(int_timestamp)


def decodetx(tx, sort_keys=True, as_string=False):
    """
    # Successfully installed bitcoin-1.1.39 blockcypher-1.0.93 python-dateutil-2.8.2
    https://www.blockcypher.com/dev/bitcoin/?python#push-raw-transaction-endpoint
    """
    parsed = blockcypher.decodetx(tx_hex=tx, coin_symbol=BLOCK_CYPHER_COIN,
                                            api_key=BLOCK_CYPHER_TOKEN)
    return parsed
    #try:
    #    return json.dumps(parsed, indent=4, sort_keys=sort_keys)
    #except Exception as ex:
    #    parsed = {"error": "{}".format(ex) }
    #    return json.dumps(parsed, indent=4, sort_keys=sort_keys)


def get_block_height():
    """
    """
    return blockcypher.get_latest_block_height(coin_symbol=BLOCK_CYPHER_COIN,
                                                   api_key=BLOCK_CYPHER_TOKEN)
