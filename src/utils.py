from logger import logging
import binascii
import datetime
import time
import json
from functools import wraps
from typing import Callable
from urllib import parse
from pycoin.key import validate
from embit import bech32 as embit_bech32

from decimal import Decimal



from typing import (
    Tuple, List, Set, Dict, KeysView, Any,
    Union, Awaitable
)

"""
from pycoin.tx.Tx import Tx
tx = Tx.from_hex(hextx)

"""

def format_txid(txid):
    return "{}...{}".format(txid[:11], txid[-11:])

def is_valid_address(addr, netcode):
    """
    :param addr: "address" or "pay_to_script"
    :param netcode: BTC or XTN
    """
    try:
        is_valid = addr.strip() and \
            validate.is_address_valid(
                addr.strip(), ["address", "pay_to_script"], [netcode]) == netcode
        if not is_valid:
            addr = addr.lower()
            hrp = addr.split("1")[0]
            ver, prog = embit_bech32.decode(hrp, addr)
            if ver is not None:
                if 0 <= ver <= 16 and prog:
                    is_valid = True
    except:
        is_valid = False
    return is_valid


def get_payable_from_BIP21URI(uri: str, proto: str = "bitcoin", netcode="BTC") -> Tuple[str, Decimal]:
    """ Computes a 'payable' tuple from a given BIP21 encoded URI.

    :param uri: The BIP21 URI to decode
    :param proto: The expected protocol/scheme (case insensitive)
    :param netcode: BTC or XTN
    :returns: A payable (address, amount) corresponding to the given URI
    :raise: Raises s ValueError if there is no address given or if the
        protocol/scheme doesn't match what is expected
    """
    obj = parse.urlparse(uri)  # type: parse.ParseResult
    if not obj.path or obj.scheme.upper() != proto.upper():
        try:
            if is_valid_address(uri, netcode):
                return uri, None
        except:
            pass
        raise ValueError("Malformed URI")
    if not obj.query:
        return obj.path, None
    query = parse.parse_qs(obj.query)  # type: Dict
    return obj.path, Decimal(query["amount"][0])


def is_txid(txid):
    """ Quick and dirty check if this is a txid. """
    if type(txid) == type("") and len(txid) == 64:
        return True
    return False

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
