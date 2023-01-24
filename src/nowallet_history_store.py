#from kivy.storage.jsonstore import JsonStore
from logger import logging
from pycoin.tx.Tx import Tx
import json


#for i in range(anzahl_keys im store,  anzahl_keys im store + Wallet._GAP_LIMIT):
#    for receive, change ...
#        addr = self.get_address(self.get_key(i, change))  # type: str

class HistoryStore:
    """ """
    def __init__(self, wallet):
        self.wallet = wallet
        self.name = 'brainbow-history-store-{}.json'.format(self.wallet.fingerprint)
        self.store = {}
        self.all_known_receive_addresses  = []
        self.all_known_change_addresses = []


    def save_to_file(self):
        json_object = json.dumps(self.store, indent=4)
        with open(self.name, "w") as outfile:
            outfile.write(json_object)

    def get_txo_of_tx(self, txid, index):
        tx = self.store.get(txid, None)
        if tx:
            return tx['txs_out'][index]

    def get_tx(self, txid):
        return self.store.get(txid, None)

    def store_tx(self, tx_obj: Tx, history_obj = None):
        self.store[tx_obj.id()] = {}
        self.store[tx_obj.id()]['hextx'] = tx_obj.as_hex()

        self.store[tx_obj.id()]['txs_in'] = []
        self.store[tx_obj.id()]['txs_out'] = []

        if history_obj:
            self.store[tx_obj.id()]['height'] = history_obj.height
            self.store[tx_obj.id()]['timestamp'] = str(history_obj.timestamp)


        for i, txs_in in enumerate(tx_obj.txs_in):
            self.store[tx_obj.id()]['txs_in'].append({
                'previous_hash': str(txs_in.previous_hash),
                'previous_index': int(txs_in.previous_index),
                'previous_txo': self.get_txo_of_tx(str(txs_in.previous_hash), int(txs_in.previous_index)),
                'in_index': i,

                })
        for i, txout in enumerate(tx_obj.txs_out):
            address = txout.address(self.wallet.chain.netcode)

            if address in self.all_known_receive_addresses:
                is_mine = True
                is_change = False
            elif address in self.all_known_change_addresses:
                is_mine = True
                is_change = True
            else:
                is_mine = False
                is_change = False

            self.store[tx_obj.id()]['txs_out'].append({
                'address': str(address),
                'out_index': i,
                'coin_value': int(txout.coin_value),
                'is_mine': is_mine,
                'is_change': is_change
                })

    # def mark_utxo_as_spend _in_block
    #
    #def update_tx(self, key, value):
    #    """
    #    """
    #    pass
    def get_tx_by_txid(self, txid):
        _tx = self.store.find(txid=txid)
        print(_tx)
        return _tx
        """
        is change?
        is ours ?
        is spend ?
        self.receive_addrs = self.wallet.get_all_known_addresses(change=False)
        self.change_addrs = self.wallet.get_all_known_addresses(change=True)
        """
