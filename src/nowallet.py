from logger import logging

import asyncio
import io
import collections
import pprint
import time
import json
from decimal import Decimal


from typing import (
    Tuple, List, Set, Dict, KeysView, Any,
    Union, Awaitable
)

from pycoin.serialize import b2h
from pycoin.ui import standard_tx_out_script
from pycoin.tx.tx_utils import distribute_from_split_pool
from pycoin.tx.tx_utils import sign_tx
from pycoin.tx.Tx import Tx
from pycoin.tx.TxIn import TxIn
from pycoin.tx.TxOut import TxOut
from pycoin.tx.Spendable import Spendable
from connectrum.client import StratumClient
from connectrum.svr_info import ServerInfo
from connectrum import ElectrumErrorResponse

from bip49 import SegwitBIP32Node
from keys import derive_key
from utils import is_txid
from utils import log_time_elapsed
from history import History

from app import update_loading_small_text
from app import update_waiting_texts

from connection import Connection

from embit import bip32, bip39, bip85
from embit import bech32 as embit_bech32
from pycoin.tx.script import tools

from utils import is_valid_address
from utils import utxo_deduplication


Chain = collections.namedtuple("Chain", ["netcode", "chain_1209k", "bip44"])
BTC = Chain(netcode="BTC", chain_1209k="btc", bip44=0)
TBTC = Chain(netcode="XTN", chain_1209k="tbtc", bip44=1)

from nowallet_history_store import HistoryStore

class Wallet:
    """ Provides all functionality required for a fully functional and secure
    HD brainwallet based on the Warpwallet technique.
    """
    COIN = 100000000  # type: int
    _GAP_LIMIT = 20  # type: int

    def __init__(self,
                 salt: str,
                 passphrase: str,
                 bip39_mnemonic: str,
                 bip39_passphrase: str,
                 connection: Connection,
                 loop: asyncio.AbstractEventLoop,
                 chain,
                 bech32=False) -> None:
        """ Wallet object constructor.
        Use discover_keys() and listen_to_addresses() coroutine method to
        construct wallet data, and listen for new data fromthe server.

        :param salt: a string to use as a salt for key derivation
        :param passphrase: a string containing a secure passphrase
        :param bip39_mnemonic: a string containing 12 or 24 BIP39 seed words
        :param bip39_passphrase: a string containing a BIP39 passphrase
        :param connection: a Connection object
        :param loop: an asyncio event loop
        :param chain: a namedtuple containing chain-specific info
        :returns: A new, empty Wallet object
        """

        @log_time_elapsed
        def create_root_keys(salt: str = None, passphrase: str = None,
                     bip39_mnemonic: str = None, bip39_passphrase: str = None,
                     account: int = 0) -> None:
            """ Derives master key from salt/passphrase and initializes all
            master key attributes.

            :param salt: a string to use as a salt for key derivation
            :param passphrase: a string containing a secure passphrase

            :param bip39_mnemonic: a string containing 12 or 24 BIP39 seed words
            :param bip39_passphrase: a string containing a BIP39 passphrase

            :param account: account number, defaults to 0
            """
            if salt and passphrase:
                update_waiting_texts(text="Deriving\nKeys",
                    small_text="Deriving keys will take some time to complete.\nPlease wait..")
                t = derive_key(
                    salt, passphrase
                )  # type: Union[int, Tuple[int, bytes]]
                assert isinstance(t, tuple), "Should never fail"
                secret_exp, chain_code = t
                # WarpWallet master private key generation
                self.warpwallet_mpk = SegwitBIP32Node(
                    netcode=self.chain.netcode,
                    chain_code=chain_code,
                    secret_exponent=secret_exp
                )  # type: SegwitBIP32Node

                # Ready for future features, BIP85 index
                warpwallet_hwif = self.warpwallet_mpk.hwif(as_private=1)
                t_embit_mpk = bip32.HDKey.from_base58(warpwallet_hwif)
                t_mnemonic = bip85.derive_mnemonic(root=t_embit_mpk, index=0) #TODO: bip85 index
                self.bip39_mnemonic = t_mnemonic
                t_seed = bip39.mnemonic_to_seed(t_mnemonic)
            elif bip39_mnemonic:
                self.warpwallet_mpk = None # Keys not generated using WarpWallet technique
                if bip39_passphrase is None:
                    bip39_passphrase = ''
                self.bip39_mnemonic = bip39_mnemonic
                t_seed = bip39.mnemonic_to_seed(bip39_mnemonic, bip39_passphrase)

            t_deriv_embit_mpk = bip32.HDKey.from_seed(t_seed).to_string()

            # pycoin is legacy
            self.mpk = SegwitBIP32Node.from_hwif(t_deriv_embit_mpk)  # type: SegwitBIP32Node
            self.mpk._netcode = self.chain.netcode

            bip = 84 if bech32 else 49  # type: int
            path = "{}H/{}H/{}H".format(bip, self.chain.bip44, account)  # type: str       #TODO: account
            self.derivation = {'bip': bip, 'bip44': self.chain.bip44, 'account': account}  #TODO: account
            self.fingerprint = self.mpk.fingerprint().hex()
            self.account_master = self.mpk.subkey_for_path(path)  # type: SegwitBIP32Node
            self.root_spend_key = self.account_master.subkey(0)  # type: SegwitBIP32Node
            self.root_change_key = self.account_master.subkey(1)  # type: SegwitBIP32Node

        self.connection = connection  # type: Connection
        self.loop = loop  # type: asyncio.AbstractEventLoop
        self.chain = chain
        self.bech32 = bech32

        self.mpk = None  # type: SegwitBIP32Node
        self.warpwallet_mpk = None # type: SegwitBIP32Node
        self.account_master = None  # type: SegwitBIP32Node
        self.root_spend_key = None  # type: SegwitBIP32Node
        self.root_change_key = None  # type: SegwitBIP32Node
        self.fingerprint = None
        self.bip39_mnemonic = ""
        create_root_keys(salt, passphrase, bip39_mnemonic, bip39_passphrase)

        # Boolean lists, True = used / False = unused
        self.spend_indicies = []  # type: List[bool]
        self.change_indicies = []  # type: List[bool]

        # All wallet TX info. (MUST not persist!)
        self.utxos = []  # type: List[Spendable]
        self.selected_utxos = []  # type: List[Spendable]
        self.spent_utxos = []  # type: List[Spendable]

        self.history = {}  # type: Dict[Any]
        self.change_history = {}  # type: Dict[Any]

        self.balance = Decimal("0")  # type: Decimal
        self.zeroconf_balance = Decimal("0")  # type: Decimal

        self.new_history = False  # type: bool

        # New data structure to connect everything and merge multiple UTXOs from the same TX.
        self.history_store = HistoryStore(wallet=self)

    @property
    def ypub(self) -> str:
        """ Returns this account's extended public key.
        :returns: a string containing the account's XPUB.
        """
        return self.account_master.hwif()

    @property
    def private_BIP32_warpwallet_root_key(self) -> str:
        warpwallet_root_key = self.warpwallet_mpk.hwif(as_private=1)
        return warpwallet_root_key

    @property
    def private_BIP32_root_key(self) -> str:
        root_key = self.mpk.hwif(as_private=1)
        return root_key

    def get_key(self, index: int, change: bool) -> SegwitBIP32Node:
        """ Returns a specified pycoin.key object.

        :param index: The index of the desired key
        :param change: a boolean indicating which key root to use
        :returns: a key object associated with the given index
        """
        root_key = self.root_change_key if change else self.root_spend_key  # type: SegwitBIP32Node
        return root_key.subkey(index)

    def get_next_unused_key(self, change: bool = False, using: bool = False) -> SegwitBIP32Node:
        """ Returns the next unused key object in the sequence.

        :param change: a boolean indicating which key root to use
        :param using: a boolean indicating whether to mark key as used now
        :returns: a key object associated with the next unused index
        """
        indicies = self.change_indicies if change else self.spend_indicies  # type: List[bool]
        for i, is_used in enumerate(indicies):
            if not is_used:
                if using:
                    indicies[i] = True
                return self.get_key(i, change)
        return None

    def get_address(self, key: SegwitBIP32Node, addr=False) -> str:
        """ Returns the segwit address for a given key.

        :param key: any given SegwitBIP32Node key
        :returns: A segwit (P2WPKH) address, either P2SH or bech32.
        """
        if not addr:
            return key.electrumx_script_hash(bech32=self.bech32)
        return key.bech32_p2wpkh_address() if self.bech32 else key.p2sh_p2wpkh_address()

    def get_all_known_addresses(self, change: bool = False, addr: bool = False) -> List[str]:
        """
        Returns a list of all addresses currently known to us.

        :param change: a boolean indicating which key root to use
        :returns: a list of address strings containing all addresses known for the given root
        """
        indicies = self.change_indicies if change else self.spend_indicies  # type: List[bool]
        return [self.get_address(self.get_key(i, change), addr=addr)
                for i in range(len(indicies))]  # type: List[str]

    def get_all_used_addresses(self, receive: bool = True, change: bool = False, addr: bool = True) -> List[str]:
        """
        Returns all receive and/or change addresses that have been used previously.

        :param change: a boolean indicating which key root to use (receive or change)
        :returns: List of address strings containing all used addresses for the given root
        """
        all_used_addresses = []

        if receive:
            for receive_index in self.history.keys():
                receive_address = self.get_address(self.get_key(receive_index, False), addr=addr)
                print ("receive_address: {}".format(receive_address))
                all_used_addresses.append(receive_address)

        if change:
            for change_index in self.change_history.keys():
                change_address = self.get_address(self.get_key(change_index, change), addr=addr)
                print ("change_address: {}".format(change_address))
                all_used_addresses.append(change_address)

        return all_used_addresses

    def search_for_index(self, search, addr=False, change=False) -> int:
        """ Returns the index associated with a given address
        if it is currently known to us, otherwise returns None.

        :param search: the address to search for
        :returns: a key index associated with the given address.
        """
        addresses = self.get_all_known_addresses(change, addr=addr)
        for i, addr in enumerate(addresses):
            if addr == search:
                return i
        return None

    def search_for_key(self, search, addr=True, change=False) -> SegwitBIP32Node:
        """ Returns the key associated with a given address
        if it is currently known to us, otherwise returns None.

        :param search: the address to search for
        :returns: a SegWitBIP32Node associated with the given address.
        """
        index = self.search_for_index(search, addr=addr, change=change)
        if index:
            return self.get_key(index, change)
        return None

    def _update_wallet_balance(self):
        """ Updates main balance numbers in Wallet object,
        by introspection of history dicts.
        """
        balance, zeroconf_balance = Decimal(0), Decimal(0)
        for hist_dict in (self.history, self.change_history):
            balance += sum(
                map(lambda h: h["balance"]["confirmed"], hist_dict.values()))
            zeroconf_balance += sum(
                map(lambda h: h["balance"]["zeroconf"], hist_dict.values()))
        self.balance, self.zeroconf_balance = balance, zeroconf_balance

    def get_tx_history(self) -> List[History]:
        """ Returns a list of all History objects in our non-change history,
        ordered by height/timestamp.

        :returns: an ordered list of History objects.
        """
        history = []  # type: List[History]
        for value in self.history.values():
            logging.info("get_tx_history, history -> value {}".format(value))
            history.extend(value["txns"])
        for value in self.change_history.values():
            logging.info("get_tx_history, change_history -> value {}".format(value))
            history.extend(filter(lambda t: t.is_spend, value["txns"]))
        history.sort(reverse=True, key=lambda h: int(time.mktime(h.timestamp.timetuple())))
        return history

    def utxo_balance(self):
        """ Accumulate all UTXO after deduplication. """
        balance = Decimal(0)
        for utxo in utxo_deduplication(self.utxos):
            balance += Decimal(str(utxo.coin_value / Wallet.COIN))
        return balance

    def selected_utxo_balance(self):
        """ Accumulate all selected UTXO after deduplication. """
        balance = Decimal(0)
        for utxo in utxo_deduplication(self.selected_utxos):
            balance += Decimal(str(utxo.coin_value / Wallet.COIN))
        return balance

    async def _get_history(self, txids: List[str]) -> List[Tx]:
        """ Coroutine. Returns a list of pycoin.tx.Tx objects
        associated with the given txids.

        :param txids: a list of txid strings to retrieve tx histories for
        :returns: Future, a list of Tx objects
        """
        futures = [self.connection.listen_rpc(self.connection.methods["get"], [txid]) for txid in txids]  # type: str
#        results = await asyncio.gather(*futures, loop=self.loop)
        results = await asyncio.gather(*futures)
        txs = [Tx.from_hex(tx_hex) for tx_hex in results]  # type: List[Tx]
        logging.debug("Retrieved Txs: %s", txs)
        return txs

    async def _get_balance(self, address: str) -> Tuple[Decimal, Decimal]:
        """ Coroutine. Returns the current balance associated with a given address.

        :param address: an address string to retrieve a balance for
        :returns: Future, a tuple of Decimals representing the balances.
        """
        result = await self.connection.listen_rpc(self.connection.methods["get_balance"], [address])  # type: Dict[str, Any]
        print ("result of get_balance {}".format(result))
        logging.debug("Retrieved a balance for address: %s", address)
        confirmed = Decimal(str(result["confirmed"])) / Wallet.COIN  # type: Decimal
        zeroconf = Decimal(str(result["unconfirmed"])) / Wallet.COIN  # type: Decimal
        return confirmed, zeroconf


    async def _get_utxos(self, scripthash: str) -> List[Spendable]:
        """ Coroutine. Returns a list of pycoin.tx.Spendable objects for all
        UTXOS associated with the given scripthash (address)

        :param scripthash: scripthash/an address string to retrieve a balance for
        :returns: Future, a list of pycoin Spendable objects.
        """
        logging.info("Retrieving utxos for scripthash %s", scripthash)
        try:
            update_loading_small_text("Retrieving UTXOs for address/scripthash {}".format(scripthash))
        except:
            pass
        result = await self.connection.listen_rpc(self.connection.methods["listunspent"], [scripthash])  # type: Dict

        print("*"*50)
        print(result)
        print("*"*50)

        pos_map = {}
        for unspent in result:
            if pos_map.get(unspent["tx_hash"]) is None:
                pos_map[unspent["tx_hash"]] = []
            pos_map[unspent["tx_hash"]].append(unspent["tx_pos"])

        futures = [self.connection.listen_rpc(self.connection.methods["get"], [unspent["tx_hash"]])
                   for unspent in result]  # type: List[asyncio.Future]
        txs = await asyncio.gather(*futures)  # type: List[str]
        txs = list(set(txs))  # Dedupe # <-- new
        utxos = []  # type: List[Spendable]
        for tx_hex in txs:
            tmp_tx = Tx.from_hex(tx_hex)  # type: Tx
            vouts = pos_map.get(tmp_tx.id(), [])
            vouts.sort()
            for vout in vouts:
                tx = Tx.from_hex(tx_hex)  # type: Tx
                spendable = tx.tx_outs_as_spendable()[vout] # type: Spendable
                print ("spendable for vout {},  {}".format(vout, spendable))
                utxos.append(spendable)

        utxos = list(set(utxos))  # Dedupe
        utxos.sort(reverse=True, key=lambda tx: int(tx.block_index_available))
        return utxos

    def _get_spend_value(self, tx: Tx) -> int:
        """ Finds the value of the txout in the given Tx object that is
        associated with our spend.

        :param tx: A Tx object given from our transaction history
        :returns: The coin value associated with our spend output.
        """
        change_addrs = self.get_all_known_addresses(change=True)  # type: List[str]
        chg_vout = None  # type: int
        for i, txout in enumerate(tx.txs_out):
            address = txout.address(netcode=self.chain.netcode)  # type: str
            if address in change_addrs:
                chg_vout = i
        # spend_vout = 0 if chg_vout == 1 else 1  # type: int
        # for debugging purposes
        spend_vout = 1 if chg_vout == 1 else 0 # type: int
        return tx.txs_out[spend_vout].coin_value


    async def _process_history(self, history: Tx, address: str, height: int) -> History:
        """ Coroutine. Creates a _History namedtuple from a given Tx object.

        :param history: A Tx object given from our transaction history
        :param address: The address of ours that is associated with the given transaction
        :returns: A new _History namedtuple for our history
        """
        value = None  # type: int
        is_spend = False  # type: bool
        for txout in history.txs_out:
            if txout.address(netcode=self.chain.netcode) == address:
                # Accumulate the value of all outputs
                if value is None:
                    value = txout.coin_value
                else:
                    value += txout.coin_value
        if not value:
            is_spend = True
            value = self._get_spend_value(history)

        decimal_value = Decimal(str(value)) / Wallet.COIN  # type: Decimal, in BTC.
        history_obj = History(tx_obj=history,
                              is_spend=is_spend,
                              value=decimal_value,
                              height=height)  # type: History
        await history_obj.get_timestamp(self.connection)
        logging.debug("Processed history object: %s", history_obj)
        # add to new storage structure
        self.history_store.store_tx(tx_obj=history, history_obj=history_obj)
        return history_obj

    async def _interpret_history(self, statuses: List[str], change: bool = False) -> bool:
        """ Populates the wallet's data structures based on a list of tx histories.
        Should only be called by discover_keys(),

        :param statuses: a list of address statuses from the server
        :param change: a boolean indicating which key index list to use
        :returns: A boolean that is true if all given histories were empty
        """
        indicies = self.change_indicies if change else self.spend_indicies  # type: List[bool]
        history_dict = self.change_history if change else self.history  # type: Dict[Any]

        is_empty = True  # type: bool
        # Each iteration represents one key index
        for status in statuses:
            if not status:
                # Mark this index as unused
                indicies.append(False)
                continue

            index = len(indicies)
            # Get key/address for current index
            key = self.get_key(index, change)  # type: SegwitBIP32Node
            scripthash = self.get_address(key)  # type: str
            address = self.get_address(key, addr=True)  # type: str

            history = await self.connection.listen_rpc(self.connection.methods["get_history"], [scripthash])  # type: List[Any]

            # Reassign historic info for this index
            txids = [tx["tx_hash"] for tx in history]  # type: List[str]
            heights = [tx["height"] for tx in history]  # type: List[int]

            # Get Tx objects
            print("\tGet Tx objects for txids={}".format(txids))
            this_history = await self._get_history(txids)  # type: List[Tx]

            # Process all Txs into our History objects
            futures = [self._process_history(hist, address, heights[i])
                       for i, hist in enumerate(this_history)]  # type: List[Awaitable[History]]

            processed_history = await asyncio.gather(
#                 *futures, loop=self.loop)  # type: List[History]
                *futures)  # type: List[History]

            if processed_history:
                # Get balance information
                t = await self._get_balance(scripthash)  # type: Tuple[Decimal, Decimal]
                confirmed, zeroconf = t

                history_dict[index] = {
                    "balance": {
                        "confirmed": confirmed,
                        "zeroconf": zeroconf
                    },
                    "txns": processed_history
                }

            # Add utxos to our list
            self.utxos.extend(await self._get_utxos(scripthash))

            self.utxos = list(set(self.utxos)) # Dedupe <- new

            # Mark this index as used since it has a history
            indicies.append(True)
            is_empty = False

        # Adjust our balances
        self._update_wallet_balance()

        return is_empty

    async def _interpret_new_history(self, scripthash: str, history: Dict[str, Any]) -> bool:
        """ Coroutine, Populates the wallet's data structures based on a new
        new tx history. Should only be called by _dispatch_result(),

        :param address/scripthash: the address associated with this new tx history
        :param history: a history message from the server
        :param change: a boolean indicating which key index list to use
        :returns: A boolean that is true if all given histories were empty
        """
        change = False  # type: bool
        is_empty = True  # type: bool

        if history:
            logging.info("Interpreting new history..")
            index = self.search_for_index(scripthash)  # type: int
            if index is None:
                change = True
                index = self.search_for_index(scripthash, change=change)
                assert index is not None, "Recieving to unknown address. CRITICAL ERROR"
            address = self.get_address(self.get_key(index, change), addr=True)

            logging.info("New history is for address: {}".format(address))
            logging.info("New history is for change: {}".format(change))

            indicies = self.change_indicies if change \
                else self.spend_indicies  # type: List[int]
            hist_dict = self.change_history if change \
                else self.history  # type: Dict[str, Any]
            address = self.get_address(self.get_key(index, change), addr=True)  # type: str

            # Reassign historic info for new history
            txid = history["tx_hash"]  # type: str
            height = history["height"]  # type: int

            # Get Tx object and process into our History object
            tx_list = await self._get_history([txid])  # type: List[Tx]
            new_history = await self._process_history(tx_list.pop(), address, height)  # type: History

            # Add History object to our history dict
            if index in hist_dict:
                hist_list = hist_dict[index]["txns"]
                did_match = False
                for i, hist in enumerate(hist_list):
                    if str(new_history.tx_obj) == str(hist.tx_obj):
                        hist_list[i] = new_history
                        did_match = True
                if not did_match:
                    hist_list.append(new_history)
            else:
                hist_dict[index] = {
                    "balance": {
                        "confirmed": None,
                        "zeroconf": None
                    },
                    "txns": [new_history]
                }

            # Get/update balance for this index, then for the wallet
            conf, zconf = await self._get_balance(scripthash)
            current_balance = hist_dict[index]["balance"]
            current_balance["confirmed"] = conf
            current_balance["zeroconf"] = zconf
            self._update_wallet_balance()

            # Add new utxo to our list if not already spent
            # type: List[Spendable]
            new_utxos = await self._get_utxos(scripthash)
            spents_str = [str(spent) for spent in self.spent_utxos]
            for utxo in new_utxos:
                if str(utxo) not in spents_str:
                    self.utxos.append(utxo)

            # Mark this index as used
            indicies[index] = True

            self.utxos = list(set(self.utxos))  # Dedupe <- new

            is_empty = False
        return is_empty

    async def _discover_keys(self, change: bool = False) -> None:
        """ Iterates through key indicies (_GAP_LIMIT) at a time and retrieves tx
        histories from the server, then populates our data structures using
        _interpret_history, Should be called once for each key root.

        :param change: a boolean indicating which key index list to use
        """
        logging.info("Discovering transaction history. change=%s", change)
        current_index = 0  # type: int
        quit_flag = False  # type: bool
        while not quit_flag:
            futures = []  # type: List[Awaitable]
            for i in range(current_index, current_index + Wallet._GAP_LIMIT):
                addr = self.get_address(self.get_key(i, change))  # type: str
                futures.append(self.connection.listen_subscribe(self.connection.methods["subscribe"], [addr]))

            result = await asyncio.gather(*futures) # type: List[Dict[str, Any]]
            quit_flag = await self._interpret_history(result, change)
            current_index += Wallet._GAP_LIMIT
        self.new_history = True

    # @log_time_elapsed  TODO: Figure out how to use a decorator on a coroutine method
    async def discover_all_keys(self) -> None:
        """ Calls discover_keys for change and spend keys. """
        logging.info("Begin discovering tx history...")
        for change in (False, True):
            await self._discover_keys(change=change)

    async def listen_to_addresses(self) -> None:
        """ Coroutine, adds all known addresses to the subscription queue, and
        begins consuming the queue so we can receive new tx histories from
        the server asynchronously.
        """
        logging.debug("Listening for updates involving any known address...")
        await self.connection.consume_queue(self._dispatch_result)

    async def _dispatch_result(self, result: List[str]) -> None:
        """ Gets called by the Connection's consume_queue method when a new TX
        history is sent from the server, then populates data structures using
        _interpret_new_history().

        :param result: an address that has some new tx history
        """
        addr = result[0]  # type: str
        history = await self.connection.listen_rpc(self.connection.methods["get_history"], [addr])  # type: List[Dict[str, Any]]
        for tx in history:
            empty_flag = await self._interpret_new_history(addr, tx) # type: bool
            if not empty_flag:
                self.new_history = True
                logging.info("Dispatched a new history for address %s", addr)


#    async def listen_to_headers(self) -> None:
#        """ Coroutine,  waiting for new blocks / block_info
#        """
#
#        logging.info("block_info, listen s")
#
#        ans = await self.connection.listen_subscribe(self.connection.methods["subscribe_headers"])
#        logging.info("block_info, listen e {} {}".format(ans, []))

    async def listen_to_headers(self) -> None:
        """ Coroutine, adds all known addresses to the subscription queue, and
        begins consuming the queue so we can receive new tx histories from
        the server asynchronously.
        """
        logging.debug("Listening for updates involving any known address...")
        await self.connection.consume_queue(self._dispatch_result2)

    async def _dispatch_result2(self, result: List[str]) -> None:
        """ Gets called by the Connection's consume_queue method when a new TX
        history is sent from the server, then populates data structures using
        _interpret_new_history().

        :param result: an address that has some new tx history
        """
        lst = []
        ans = await self.connection.listen_subscribe(self.connection.methods["subscribe_headers"], lst)  # type: List[Dict[str, Any]]
        print("ans {}".format(ans))



    @staticmethod
    def _calculate_vsize(tx: Tx) -> int:
        """ Calculates the virtual size of tx in bytes.

        :param tx: a Tx object that we need to get the vsize for
        :returns: An int representing the vsize of the given Tx
        """
        def _total_size(tx: Tx) -> int:
            ins = len(tx.txs_in)  # type: int
            outs = len(tx.txs_out)  # type: int
            return (ins * 180 + outs * 34) + (10 + ins)

        def _base_size(tx: Tx) -> int:
            buffer = io.BytesIO()  # type: io.BytesIO
            tx.stream(buffer)
            return len(buffer.getvalue())

        weight = 3 * _base_size(tx) + _total_size(tx)  # type: int
        return weight // 4

    @staticmethod
    def satb_to_coinkb(satb: int) -> float:
        """ Converts a fee rate from satoshis per byte to coins per KB.

        :param satb: An int representing a fee rate in satoshis per byte
        :returns: A float representing the rate in coins per KB
        """
        return (satb * 1000) / Wallet.COIN

    @staticmethod
    def coinkb_to_satb(coinkb: float) -> int:
        """ Converts a fee rate from coins per KB to satoshis per byte.

        :param coinkb: A float representing a fee rate in coins per KB
        :returns: An int representing the rate in satoshis per byte
        """
        return int((coinkb / 1000) * Wallet.COIN)

    async def get_fee_estimation(self, blocks=6):
        """ Gets a fee estimate from server.

        :returns: A float representing the appropriate fee in coins per KB
        :raise: Raises a base Exception when the server returns -1

        Return the estimated transaction fee per kilobyte for a transaction
        to be confirmed within a certain number of blocks - 6 in this case.

        """
        coin_per_kb = await self.connection.listen_rpc(
            self.connection.methods["estimatefee"], [blocks])  # type: float
        if coin_per_kb < 0:
            raise Exception("Cannot get a fee estimate from server")
        logging.info("Fee estimate from server is %f %s/KB",
                     coin_per_kb, self.chain.chain_1209k.upper())
        return coin_per_kb

    async def get_relayfee(self):
        """ Gets relayfee from server.

        :returns: A float representing the appropriate fee in coins per KB
        :raise: Raises a base Exception when the server returns -1

        Return the minimum fee a low-priority transaction must pay
        in order to be accepted to the daemon’s memory pool.
        """
        coin_per_kb = await self.connection.listen_rpc(
            self.connection.methods["relayfee"], [])  # type: float
        if coin_per_kb < 0:
            raise Exception("Cannot get relayfee from server")
        logging.info("Relayfee from server is %f %s/KB",
                     coin_per_kb, self.chain.chain_1209k.upper())
        return coin_per_kb


    @staticmethod
    def _get_fee(tx, coin_per_kb: float) -> Tuple[int, int]:
        """ Calculates the size of tx based on a given estimate from the server.

        :param tx: a Tx object that we need to estimate a fee for
        :param coin_per_kb: Fee estimation in whole coins per KB
        :returns: An Tuple with two ints representing the appropriate fee
            in satoshis, and the tx's virtual size
        :raise: Raises a ValueError if given fee rate is over 1000 satoshi/B
        """
        if coin_per_kb > Wallet.satb_to_coinkb(2000):
            raise ValueError("Given fee rate is extraordinarily high.")
        tx_vsize = Wallet._calculate_vsize(tx)  # type: int
        tx_kb_count = tx_vsize / 1000  # type: float
        int_fee = int((tx_kb_count * coin_per_kb) * Wallet.COIN)  # type: int

        # Make sure our fee is at least the default minrelayfee
        # https://bitcoin.org/en/developer-guide#transaction-fees-and-change
        MINRELAYFEE = 1000  # type: int
        fee = int_fee if int_fee < MINRELAYFEE else MINRELAYFEE
        return fee, tx_vsize

    def _mktx(self, out_addr: str, dec_amount: Decimal,
              is_high_fee: bool, rbf: bool = False) -> Tuple[Tx, Set[str], int]:
        """
        Builds a standard Bitcoin transaction - in the most naive way.
        Coin selection is basically random.
        Uses one output and one change address.
        Takes advantage of our subclasses to implement BIP69.

        :param out_addr: an address to send to
        :param amount: a Decimal amount in whole BTC
        :param is_high_fee: A boolean which tells whether the current fee rate
            is above a certain threshold
        :param rbf: A boolean that says whether to mark Tx as replaceable
        :returns: A not-fully-formed and unsigned Tx object
        """
        amount = int(dec_amount * Wallet.COIN)  # type: int
        fee_highball = 100000  # type: int
        total_out = 0  # type: int

        spendables = []  # type: List[Spendable]
        in_addrs = set()  # type: Set[str]
        del_indexes = []  # type: List[int]
        del_utxo_candidates = []
        # Sort utxos based on current fee rate before coin selection
        self.utxos.sort(key=lambda utxo: utxo.coin_value, reverse=not is_high_fee)

        # Collect enough UTXOs for this spend.
        # Add them to spent list and delete them from UTXO list later.
        # If we have selected UTXOs, than only take from those.
        for i, utxo in enumerate(self.utxos):
            if total_out < amount + fee_highball:
                if self.selected_utxos and utxo in self.selected_utxos \
                    or not self.selected_utxos:
                    self.spent_utxos.append(utxo)
                    #if utxo not in spendables: <-- #FIXME
                    #    spendables.append(utxo)
                    spendables.append(utxo)
                    in_addrs.add(utxo.address(self.chain.netcode))
                    del_indexes.append(i)
                    total_out += utxo.coin_value
        # Do not remove them now.
        # We will remove them from the UTXOs as soon as we broadcast the TX.
        #self.utxos = [utxo for i, utxo in enumerate(self.utxos) if i not in del_indexes]

        #for spendable_utxos in self.spent_utxos:
        #    print (spendable_utxos)
        for i, utxo in enumerate(self.utxos):
            for d_i in del_indexes:
                if i == d_i:
                    print("Remove candidate, index: {}, utxo: {} ".format(d_i, utxo))
                    del_utxo_candidates.append(utxo)

        # Get change address, mark index as used, and create payables list
        change_key = self.get_next_unused_key(change=True, using=True)  # type: SegwitBIP32Node
        change_addr = self.get_address(change_key, addr=True)  # type: str
        payables = []  # type: List[Tuple[str, int]]
        payables.append((out_addr, amount))
        payables.append((change_addr, 0))

        tx = Wallet._create_bip69_tx(spendables, payables, rbf)  # type: Tx
        print ("\n"*5)
        print (tx)
        print (dir(tx))
        # Search for change output index after lex sort
        chg_vout = None  # type: int
        for i, txout in enumerate(tx.txs_out):
            if txout.address(self.chain.netcode) == change_addr:
                chg_vout = i
                break
        #decoded_tx = decodetx(tx.as_hex())
        #print("create_bip69_tx {}".format( decoded_tx.get('hash', '')))
        # Create pycoin Tx object from inputs/outputs
        return tx, in_addrs, chg_vout, del_utxo_candidates

    @staticmethod
    def _create_bip69_tx(spendables: List[Spendable], payables: List[Tuple[str, int]],
                         rbf: bool, version: int = 1) -> Tx:
        """ Create tx inputs and outputs from spendables and payables.
        Sort lexicographically and return unsigned Tx object.

        :param spendables: A list of Spendable objects
        :param payables: A list of payable tuples
        :param rbf: Replace by fee flag
        :param version: Tx format version
        :returns: Fully formed but unsigned Tx object
        """
        spendables.sort(key=lambda utxo: (utxo.as_dict()["tx_hash_hex"],
                                          utxo.as_dict()["tx_out_index"]))

        # Create input list from utxos
        # Set sequence numbers to zero if using RBF.
        txs_in = [spendable.tx_in() for spendable in spendables]  # type: List[TxIn]
        if rbf:
            logging.info("Spending with opt-in Replace by Fee! (RBF)")
            for txin in txs_in:
                txin.sequence = 0

        # Create output list from payables
        txs_out = []  # type: List[TxOut]
        for payable in payables:
            bitcoin_address, coin_value = payable
            try:
                script = standard_tx_out_script(bitcoin_address)  # type: bytes
            except:
                # Handle bech32 using embit.
                # Our pycoin 0.8 is not able to do it directly.
                addr = bitcoin_address.lower()
                hrp = addr.split("1")[0]
                ver, prog = embit_bech32.decode(hrp, addr)
                # Convert the witness program (prog) to bytes
                decoded_prog = bytes(prog)
                # Construct the scriptPubKey for P2WPKH
                script = bytes([0x00, len(decoded_prog)]) + decoded_prog

            txs_out.append(TxOut(coin_value, script))
        txs_out.sort(key=lambda txo: (txo.coin_value, b2h(txo.script)))

        tx = Tx(version=version, txs_in=txs_in, txs_out=txs_out)  # type: Tx
        tx.set_unspents(spendables)
        return tx

    def _signtx(self, unsigned_tx: Tx, in_addrs: Set[str], fee: int) -> None:
        """ Signs Tx and redistributes outputs to include the miner fee.

        :param unsigned_tx: an unsigned Tx to sign and add fee to
        :param in_addrs: a list of our addresses that have recieved coins
        :param fee: an int representing the desired Tx fee
        """
        redeem_scripts = {}  # type: Dict[bytes, bytes]
        wifs = []  # type: List[str]

        # Search our indicies for keys used, given in in_addrs list
        # Populate lists with our privkeys and redeemscripts
        for change in (True, False):
            addresses = self.get_all_known_addresses(change, addr=True)
            for i, addr in enumerate(addresses):
                key = self.get_key(i, change)  # type: SegwitBIP32Node
                if addr in in_addrs:
                    p2aw_script = key.p2wpkh_script()  # type: bytes
                    script_hash = key.p2wpkh_script_hash()  # type: bytes
                    redeem_scripts[script_hash] = p2aw_script
                    wifs.append(key.wif())
        # Include our total fee and sign the Tx
        distribute_from_split_pool(unsigned_tx, fee)
        sign_tx(unsigned_tx, wifs=wifs,
                netcode=self.chain.netcode,
                p2sh_lookup=redeem_scripts)

    def _create_replacement_tx(self, hist_obj: History,
                               version: int = 1) -> Tuple[Tx, Set[str], int]:
        """ Builds a replacement Bitcoin transaction based on a given History
        object in order to implement opt in Replace-By-Fee.

        :param hist_obj: a History object from our tx history data
        :param version: an int representing the Tx version
        :returns: A not-fully-formed and unsigned replacement Tx object,
            a list of addresses used as inputs, and the index of the change output
        :raise: Raises a ValueError if tx not a spend or is already confirmed
        """
        if hist_obj.height == 0 and hist_obj.is_spend:
            old_tx = hist_obj.tx_obj  # type: Tx
            spendables = old_tx.unspents  # type: List[Spendable]
            chg_vout = None  # type: int

            in_addrs = set()  # type: Set[str]
            for utxo in spendables:
                in_addrs.add(utxo.address(self.chain.netcode))

            txs_out = []  # type: List[TxOut]
            for i, txout in enumerate(old_tx.txs_out):
                value = None  # type: int
                if txout.coin_value / Wallet.COIN == hist_obj.value:
                    value = txout.coin_value
                else:
                    value = 0
                    chg_vout = i
                txs_out.append(TxOut(value, txout.script))

            new_tx = Tx(version=version,
                        txs_in=old_tx.txs_in,
                        txs_out=txs_out)  # type: Tx
            new_tx.set_unspents(spendables)
            return new_tx, in_addrs, chg_vout
        else:
            raise ValueError("This transaction is not replaceable")

    async def spend(self, address: str, amount: Decimal, coin_per_kb: float,
                    rbf: bool = False) -> Tuple[Any]:
        """ Gets a new tx from _mktx() and sends it to the server to be broadcast,
        then inserts the new tx into our tx history and includes our change
        utxo, which is currently assumed to be the last output in the Tx.

        :param address: an address to send to
        :param amount: a Decimal amount in whole BTC
        :param coin_per_kb: a fee rate given in whole coins per KB
        :param rbf: a boolean saying whether to mark the tx as replaceable
        :returns: Our new Tx, the index of the change output, the total fee,
                    the vsize and a list of UTXOs that
                    would be consumed by braodcasting the Tx.
        :raise: Raises a base Exception if we can't afford the fee
        """
        spend_all = amount == self.utxo_balance() # do we spend the full available balance?

        is_high_fee = Wallet.coinkb_to_satb(coin_per_kb) > 100


        # type: Tuple[Tx, Set[str], int]
        t1 = self._mktx(address, amount, is_high_fee, rbf=rbf)
        tx, in_addrs, chg_vout, del_utxo_candidates = t1
        t2 = self._get_fee(tx, coin_per_kb)  # type: Tuple[int, int]
        fee, tx_vsize = t2
        print ("fee, tx_vsize: {} {}".format(fee, tx_vsize))
        decimal_fee = Decimal(str(fee)) / Wallet.COIN  # type: Decimal
        total_out = amount + decimal_fee
        if total_out > self.balance:
            #if not spend_all:
            print("total_out {:.8f} = amount {:.8f} + decimal_fee {:.8f}".format(total_out, amount, decimal_fee))
            raise Exception("Insufficient funds.")
            #else:
            #    amount -= decimal_fee
            #    print ("amount {}".format(amount))
            #    # type: Tuple[Tx, Set[str], int]
            #    t1 = self._mktx(address, amount, is_high_fee, rbf=rbf)
            #    tx, in_addrs, chg_vout, del_utxo_candidates = t1
            #    t2 = self._get_fee(tx, coin_per_kb)  # type: Tuple[int, int]
            #    fee, tx_vsize = t2
            #    print ("fee, tx_vsize: {} {}".format(fee, tx_vsize))
            #    decimal_fee = Decimal(str(fee)) / Wallet.COIN  # type: Decimal
            #    total_out = amount + decimal_fee
        logging.info("unsigned_tx {}".format(tx) )
        self._signtx(tx, in_addrs, fee)

        #if broadcast:
        #    logging.info("broadcast TX")
        #    chg_out = tx.txs_out[chg_vout]  # type: TxOut
        #    txid = await self.broadcast(tx.as_hex(), chg_out)  # type: str
        #    return txid, decimal_fee, tx_vsize

        logging.info("Not broadcasting TX {}".format(tx.as_hex()))
        return tx, chg_vout, decimal_fee, tx_vsize, del_utxo_candidates


    async def broadcast(self, tx_hex: str, chg_out: TxOut) -> str:
        txid = await self.connection.listen_rpc(self.connection.methods["broadcast"], [tx_hex])  # type: str
        if is_txid(txid):
            change_address = chg_out.address(netcode=self.chain.netcode)  # type:str
            change_key = self.search_for_key(change_address, change=True)
            scripthash = self.get_address(change_key)
            print("broadcast -> txid = await .., txid=".format(txid))
            logging.info("Subscribing to new change address...")
            self.connection.listen_subscribe(self.connection.methods["subscribe"], [scripthash])
            logging.info("Finished subscribing to new change address...")
            return (txid, None) # Success; txid, None
        else:
            return (None, txid) # Failure, None, txid as exception

    async def replace_by_fee(self, hist_obj: History, coin_per_kb: float) -> str:
        """ Gets a replacement tx from _create_replacement_tx() and sends it to
        the server to be broadcast, then replaces the tx in our tx history and
        subtracts the difference in fees from our balance.

        :param hist_obj: a History object from our tx history data
        :param coin_per_kb: a new fee rate given in whole coins per KB
        :returns: The txid of our new tx, given after a successful broadcast
        """
        t = self._create_replacement_tx(
            hist_obj)  # type: Tuple[Tx, Set[str], int]
        tx, in_addrs = t[:2]
        new_fee = self._get_fee(tx, coin_per_kb)[0]  # type: int

        self._signtx(tx, in_addrs, new_fee)
        txid = await self.connection.listen_rpc(self.connection.methods["broadcast"], [tx.as_hex()])  # type: str

        fee_diff = new_fee - hist_obj.tx_obj.fee()  # type: int
        self.balance -= fee_diff
        hist_obj.tx_obj = tx
        return txid

    def __str__(self) -> str:
        """ Special method __str__()
        :returns: The string representation of this wallet object
        """
        pprinter = pprint.PrettyPrinter(indent=4)  # type: pprint.PrettyPrinter
        str_ = []  # type: List[str]
        str_.append("\nYPUB: {}".format(self.ypub))
        str_.append("\nHistory:\n{}".format(
            pprinter.pformat(self.get_tx_history())))
        str_.append("\nUTXOS:\n{}".format(
            pprinter.pformat(self.utxos)))
        str_.append("\nBalance: {} ({} unconfirmed) {}".format(
            float(self.balance), float(self.zeroconf_balance),
            self.chain.chain_1209k.upper()))
        str_.append("\nYour current address: {}".format(
            self.get_address(self.get_next_unused_key(), addr=True)))
        return "".join(str_)
