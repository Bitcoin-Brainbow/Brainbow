from logger import logging

from decimal import Decimal
from typing import Dict
from typing import Any

from pycoin.tx.Tx import Tx
#from pycoin.tx.TxIn import TxIn
#from pycoin.tx.TxOut import TxOut
#from pycoin.tx.Spendable import Spendable
from connectrum import ElectrumErrorResponse
from connection import Connection

from utils import get_timestamp_from_block_header

class History:
    """ History object. Holds data relevant to a piece of
    our transaction history.
    """

    def __init__(self, tx_obj: Tx, is_spend: bool, value: Decimal, height: int) -> None:
        """ History object constructor.

        :param tx_obj: a pycoin.Tx object representing the tx data
        :param is_spend: boolean, was this tx a spend from our wallet?
        :param value: the coin_value of this tx
        :param height: the height of the block this tx is included in
        :returns: A new History object
        """
        self.tx_obj = tx_obj  # type: Tx
        self.is_spend = is_spend  # type: bool
        self.value = value  # type: Decimal
        self.height = height  # type: int
        self.timestamp = None  # type: str

        print("\n\tHistory object constructor, adding {} {}".format(tx_obj.as_hex(),  self.as_dict()))


    async def get_timestamp(self, connection: Connection) -> None:
        """ Coroutine. Gets the timestamp for this Tx based on the given height.
        :param connection: a Connection object for getting a block header from the server
        """
        if self.height > 0:
            try:
                block_header = await connection.listen_rpc(
                    connection.methods["get_header"],
                    [self.height]
                )  # type: Dict[str, Any]
            except ElectrumErrorResponse as e:
                return
            self.timestamp = get_timestamp_from_block_header(block_header)
            logging.debug("Got timestamp {} for block at height {}".format(self.height, self.timestamp))
        else:
            import datetime
            self.timestamp = datetime.datetime.now()
            logging.debug("Assuming timestamp %d from block at height %s",
                          self.height, self.timestamp)

    def as_dict(self) -> Dict[str, Any]:
        """ Transforms this History object into a dictionary.
        :returns: A dictionary representation of this History object
        """
        return {
            "txid": self.tx_obj.id(),
            "is_spend": self.is_spend,
            "value": str(self.value),
            "height": self.height,
            "timestamp": self.timestamp
        }

    def __str__(self) -> str:
        """ Special method __str__()
        :returns: The string representation of this History object
        """
        return (
            "<History: TXID:{} is_spend:{} value:{} height:{} timestamp:{}>"
        ).format(self.tx_obj.id(), self.is_spend,
                 self.value, self.height, self.timestamp)

    def __repr__(self) -> str:
        return str(self)

    def __hash__(self) -> int:
        return hash(self.tx_obj.id())

    def __eq__(self, other) -> bool:
        return self.tx_obj.id() == other.tx_obj.id()
