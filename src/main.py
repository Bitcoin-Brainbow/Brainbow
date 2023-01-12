# -*- coding: utf-8 -*-
import sys, traceback

# Monkey patch based on https://github.com/kivy/python-for-android/issues/1866#issuecomment-927157780
import ctypes
try:
    ctypes.pythonapi = ctypes.PyDLL("libpython%d.%d.so" % sys.version_info[:2])   # replaces ctypes.PyDLL(None)
except:
    pass
# End patch

import re

from asyncio import create_task as asyncio_create_task
from asyncio import gather as asyncio_gather
from asyncio import sleep as asyncio_sleep


import logging

from decimal import Decimal


from kivy.utils import platform
from kivy.core.window import Window

from kivy.compat import unichr
from kivy.metrics import dp
from kivy.properties import NumericProperty, StringProperty, ObjectProperty
from kivy.uix.screenmanager import Screen
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout


from kivy.uix.behaviors import ButtonBehavior

from kivymd.app import MDApp
from kivymd.theming import ThemeManager
from kivymd.uix.list import TwoLineListItem
from kivymd.uix.list import TwoLineIconListItem
from kivymd.uix.list import ILeftBodyTouch
from kivymd.uix.list import OneLineListItem
from kivymd.uix.button import MDIconButton
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.button import MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.tab import MDTabsBase
from kivymd.uix.snackbar import Snackbar
from kivy.uix.modalview import ModalView

#from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.button import ButtonBehavior
#from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty

from kivy_garden.qrcode import QRCodeWidget

from kivy.core.clipboard import Clipboard
from kivy.core.text import LabelBase
from kivymd.uix.relativelayout import MDRelativeLayout

from pycoin.serialize import b2h

import nowallet

from electrum_servers import get_random_server
from exchange_rate import fetch_exchange_rates
from fee_estimate import fetch_fee_estimate
from settings_json import settings_json
from wallet_alias import wallet_alias
from functools import partial
import threading
import concurrent.futures

from aiosocks import SocksConnectionError
from aiohttp.client_exceptions import ClientConnectorError

from passphrase import entropy_bits

from utils import utxo_deduplication
from utils import is_valid_address
from utils import get_payable_from_BIP21URI

from bottom_screens_signed_tx import open_tx_preview_bottom_sheet

from camera4kivy import Preview
from qrreader import QRReader


top_blk = {'height', 0}

#import os



__version__ = "0.1.145"

if platform == "android":
    Window.softinput_mode = "below_target"
else:
    Window.size = (768/2, 1366/2)



class IconLeftConfirmationWidget(ILeftBodyTouch, MDIconButton):
    pass

class Tab(MDFloatLayout, MDTabsBase):
    content_text = StringProperty()
    pass

# Declare screens
class WelcomeScreen(Screen):
    pass


class LoginScreen(Screen):
    pass


class MainScreen(Screen):
    pass


class WaitScreen(Screen):
    pass

class YPUBScreen(Screen):
    pass

class SeedScreen(Screen):
    pass


class PINScreen(Screen):
    pass

class ExchangeRateScreen(Screen):
    pass

class BlockHeightScreen(Screen):
    pass

class TXReviewScreen(Screen):
    pass


class BalanceLabel(ButtonBehavior, MDLabel):
    pass


class PassphraseControlField(MDRelativeLayout):
    text = StringProperty()
    hint_text = StringProperty()


class QRScanAddressField(MDRelativeLayout):
    text = StringProperty()
    helper_text = StringProperty()

class UTXOListItem(TwoLineListItem):
    """ """
    utxo = ObjectProperty()

    def open_utxo_menu(self):
        app = MDApp.get_running_app()
        app.utxo = self.utxo
        app.utxo_menu = MDDropdownMenu(items=app.utxo_menu_items,
                                        width_mult=6,
                                        caller=self,
                                        max_height=0,)
        app.utxo_menu.open()





class AddressListItem(TwoLineIconListItem):
    icon = StringProperty("database-marker-outline")


class BalanceListItem(TwoLineIconListItem):
    icon = StringProperty("check-circle")
    history = ObjectProperty()
    app = MDApp.get_running_app()
    def on_press(self):
        print(self.history.as_dict)
        print(self.history.value)
        print(dir(self.history.tx_obj))
        open_tx_preview_bottom_sheet(self.history.tx_obj, self.history, app.wallet)


class FloatInput(MDTextField):
    pat = re.compile('[^0-9]')

    def insert_text(self, substring, from_undo=False):
        pat = self.pat
        if '.' in self.text:
            s = re.sub(pat, '', substring)
        else:
            s = '.'.join([re.sub(pat, '', s) for s in substring.split('.', 1)])
        return super(FloatInput, self).insert_text(s, from_undo=from_undo)


class BrainbowApp(MDApp):
    units = StringProperty()
    currency = StringProperty()
    current_coin = StringProperty("0")
    current_fiat = StringProperty("0")
    current_fee = NumericProperty()
    current_utxo = ObjectProperty()
    block_height = 0
    _wallet_ready = False  # is false until we can use the wallet


    def __init__(self, loop):
        self.chain = nowallet.TBTC # TBTC
    #    self.chain = nowallet.BTC
        self.loop = loop
        self.is_amount_inputs_locked = False
        self.fiat_balance = False
        self.bech32 = False
        self.exchange_rates = None
        self.current_tab_name = "balance"
        self.spend_tuple = None # Holds a tuple (signed Tx ready to broadcast, chg_vout, decimal_fee, tx_vsize, del_utxo_candidates) or None
        self.tx_btm_sheet = None
        self.current_fee = 1
        self.mempool_recommended_fees = None
        # for QR code reading UX
        self._qrreader = None
        self._fiat_fields_hidden = True

        self._qr_preview_modal = None
        self._dialog = None # generic dialog
        self._disconnect_dialog = None

        # class MyMenuItem(MDMenuItem):
        class MyMenuItem(OneLineListItem):
            pass

        self.menu_items = [{"viewclass": "MyMenuItem",
                            "text": "View YPUB",
                            "on_release": lambda x="View YPUB": app.menu_item_handler(x)},
                            {"viewclass": "MyMenuItem",
                            "text": "View BIP32 Root Key (WIF)",
                            "on_release": lambda x="View BIP32 Root Key (WIF)": app.menu_item_handler(x)},
                           {"viewclass": "MyMenuItem",
                            "text": "Manage UTXOs",
                            "on_release": lambda x="Manage UTXOs": app.menu_item_handler(x)},
                           {"viewclass": "MyMenuItem",
                            "text": "Settings",
                            "on_release": lambda x="Settings": app.menu_item_handler(x)},
                           ]

        self.utxo_menu_items = [{"viewclass": "MyMenuItem",
                                 "on_release": lambda x="view-address": self.utxo_menu_callback(self, x),
                                 "text": "View Address"},

                                {"viewclass": "MyMenuItem",
                                 "on_release": lambda x="copy-address": self.utxo_menu_callback(self, x),
                                 "text": "TODO:Copy Address"},

                                {"viewclass": "MyMenuItem",
                                 "on_release": lambda x="Sign Message": self.utxo_menu_callback(self, x),
                                 "text": "TODO:Sign/Verify Message" },


                                {"viewclass": "MyMenuItem",
                                 "on_release": lambda x="View Private Key": self.utxo_menu_callback(self, x),
                                 "text": "TODO:View Private Key"},

                                {"viewclass": "MyMenuItem",
                                 "on_release": lambda x="View Redeem Script": self.utxo_menu_callback(self, x),
                                 "text": "TODO:View Redeem Script"},


                                ]

        self.fee_preset_items = [{"viewclass": "MyMenuItem",
                                    "on_release": lambda x="fastestFee": self.fee_select_callback(x),
                                    "text": "High Priority"},
                                 {"viewclass": "MyMenuItem",
                                    "on_release": lambda x="halfHourFee": self.fee_select_callback(x),
                                    "text": "Normal Transaction"},
                                 {"viewclass": "MyMenuItem",
                                    "on_release": lambda x="economyFee": self.fee_select_callback(x),
                                    "text": "Low Priority"},
                                 {"viewclass": "MyMenuItem",
                                    "on_release": lambda x="minimumFee": self.fee_select_callback(x),
                                    "text": "Unfairly Cheap"},
                                 {"viewclass": "MyMenuItem",
                                    "on_release": lambda x="custom": self.fee_select_callback(x),
                                    "text": "Custom Fee"},
                                ]
        super().__init__()



    def utxo_menu_callback(self, cls, x):
        print("menu_callback: {} {}".format( cls.utxo.address(netcode="XTN"), x))
        #print ("352 {}".format(dir(cls)))
        app.utxo_menu.dismiss()

        if x == "view-address":
            self.open_address_bottom_sheet_callback(address=cls.utxo.address(netcode="XTN"))

    def current_slide(self, index):
        print("current_slide {} ".format(index))
        pass


    def give_current_tab_name(self, *args):
        self.current_tab_name = args[1].name
        print ("current_tab_name: {}".format(self.current_tab_name))
        # DEBUGGING, REMOVE LATER
        if self.current_tab_name == "utxos":
            self.update_utxo_screen()


    def _hide_fiat_fields(self):
        print("_hide_fiat_fields")
        for widget_btc, widget_fiat in [
            (self.root.ids.spend_amount_input, self.root.ids.spend_amount_input_fiat),
            (self.root.ids.receive_amount_input, self.root.ids.receive_amount_input_fiat)]:
            widget_btc.size_hint_x = 1
            widget_btc.width = 1
            widget_fiat.size_hint_x = None
            widget_fiat.disabled = True
            widget_fiat.opacity = 0
            widget_fiat.height = 0
            widget_fiat.width = 0
        self._fiat_fields_hidden = True

    def _show_fiat_fields(self):
        print("_show_fiat_fields")
        for widget_btc, widget_fiat in [
            (self.root.ids.spend_amount_input, self.root.ids.spend_amount_input_fiat),
            (self.root.ids.receive_amount_input, self.root.ids.receive_amount_input_fiat)]:
            widget_btc.size_hint_x = 0.5
            widget_btc.width = 0.5
            widget_fiat.size_hint_x = 0.5
            widget_fiat.disabled = False
            widget_fiat.opacity = 1
            widget_fiat.height = widget_btc.height
            widget_fiat.width = 0.5
            self.update_amounts(widget_btc.text, "coin")
        self._fiat_fields_hidden = False

    def on_exchange_rate_switch_active(self, switch, on_off):
        if on_off:
            self.currency = "USD"
            self.root.ids.current_btc_exchange_rate.text = "1 BTC = ... {}".format(self.currency)
            if self.exchange_rates in [None, False] and self.get_rate() > Decimal(0):
                self.root.ids.current_btc_exchange_rate.text = \
                    "Rates will be available within a few seconds."
            self._show_fiat_fields()
        else:
            self.currency = "BTC"
            self.root.ids.current_btc_exchange_rate.text = "1 BTC = 1 BTC"
            self._hide_fiat_fields()

        self.update_balance_screen()

    def on_offline_switch_active(self, switch, on_off):
        if on_off:
            print("OFFLINE MODE ")
            self.root.ids.startup_offline_mode_image_source.source = "assets/dark-offline.png"
        else:
            print("NOT OFFLINE MODE")
            self.root.ids.startup_offline_mode_image_source.source = "assets/dark-online.png"
    def show_snackbar(self, text):
        snackbar = Snackbar(text=text,
                            snackbar_x="8dp",
                            snackbar_y="8dp")
        snackbar.size_hint_x = (Window.width - (snackbar.snackbar_x * 2)) / Window.width
        snackbar.open()
        return snackbar

    def show_dialog(self, title, message, qrdata=None, cb=None):
        if qrdata:
            dialog_height = 300
            content = QRCodeWidget(data=qrdata,
                                   size=(dp(150), dp(150)),
                                   size_hint=(None, None))
        else:
            dialog_height = 200
            content = ""
            # content = MDLabel(font_style='Body1',
            #                   theme_text_color='Secondary',
            #                   text=message,
            #                   size_hint_y=None,
            #                   valign='top')
            # content.bind(texture_size=content.setter('size'))
        self._dialog = MDDialog(title=title,
                               content_cls=content if content else None,
                               text=message if not content else "",
                               size_hint=(.8, None),
                               height=dp(dialog_height),
                               auto_dismiss=False,
                               buttons=[
                                   MDFlatButton(
                                       text="DISMISS",
                                       on_release=partial(self.close_dialog))
                                   ]
                               )
        self._dialog.open()

    def close_dialog(self, *args):
        if self._dialog:
            self._dialog.dismiss()

    def close_disconnect_dialog(self, *args):
        if self._disconnect_dialog:
            self._disconnect_dialog.dismiss()
    def close_disconnect_dialog_and_reconnect(self, *args):
        if self._disconnect_dialog:
            self._disconnect_dialog.dismiss()
        print("close_disconnect_dialog_and_reconnect")

    def close_preview_modal(self, *args):
        if self._qr_preview_modal:
            self._qr_preview_modal.dismiss()
        self.qrreader_release()

    def qrreader_release(self, *args):
        if self._qrreader:
            self._qrreader.disconnect_camera()
            self._qrreader = None
        if self._qr_preview_modal:
            self._qr_preview_modal = None




    def show_preview_modal(self):
        self._qr_preview_modal = ModalView(size_hint=(None, None), size=(480, 640))
        self._qr_preview_modal.add_widget(self._qrreader)
        self._qr_preview_modal.on_pre_dismiss = partial(self.qrreader_release)
        self._qr_preview_modal.open()
        self._qrreader.connect_camera(analyze_pixels_resolution = 640, enable_analyze_pixels = True)


    def zbar_cb(self, qrcode):
        self.close_preview_modal()
        address = None
        try:
            address, amount = get_payable_from_BIP21URI(qrcode, netcode=self.chain.netcode)
            self.root.ids.address_input.text = str(address)
            if amount:
                self.root.ids.spend_amount_input.text = str(amount)
        except ValueError as ve:

            self.show_dialog("Error", str(ve))
        if address:
            self.show_snackbar("Found {}..{}".format(address[:11], address[-11:]))

    def start_qr_scanner(self):
        if not self._qrreader:
            self._qrreader = QRReader(letterbox_color='black', aspect_ratio='4:3', cb=self.zbar_cb)
            self.show_preview_modal()
        else:
            self.qrreader_release()





    def qrcode_handler(self, symbols):
        try:
            address, amount = get_payable_from_BIP21URI(symbols[0])
        except ValueError as ve:
            self.show_dialog("Error", str(ve))
            return
        self.root.ids.address_input.text = address
        self.update_amounts(text=str(amount))
        self.root.ids.detector.stop()
        self.root.ids.sm.current = "main"


    def switch_theme_handler(self):
        if self.is_darkmode:
            self.theme_cls.theme_style = "Light"
        else:
            self.theme_cls.theme_style = "Dark"
        self.is_darkmode = not self.is_darkmode

    def onboarding_menu_handler(self):
        if not self._wallet_ready:
            self.root.ids.onboarding_drawer.set_state("open")


    def nav_drawer_handler(self):
        if self._wallet_ready:
            self.root.ids.nav_drawer.set_state("open")
        elif self.root.ids.sm.current == "wait":
            self.show_snackbar('Loading wallet state...')
        else:
            self.show_snackbar('No active session.')




    def navigation_handler(self, button):
        print ("navigation_handler. button={}".format(button), button)
        #app.root.ids.sm.current = "main"
        self.root.ids.sm.current = "main"
        pass

    # START EXPORT #####

    def download_prv(self):
        """ """
        from os.path import join as os_path_join
        from kivymd.uix.filemanager import MDFileManager

        Window.bind(on_keyboard=self.file_manager_events)
        self.manager_open = False
        self._xpriv_file = None
        print("download_prv")
        self.file_manager = MDFileManager(
            exit_manager=self.exit_manager,
            select_path=self.select_path,
            #background_color_toolbar= [1.0, 1.0, 1.0, 1.0],
            selector="folder",
        )
        try:
            from android.storage import primary_external_storage_path
            ext_path = primary_external_storage_path()
        except ModuleNotFoundError:
            from os.path import expanduser
            ext_path = expanduser("~")
        storage_path = os_path_join(ext_path, 'Downloads')
        self.file_manager.show(storage_path)
        self.manager_open = True


    def _export_xpriv_file(self, *args):
        print(self._xpriv_file)
        #print (path)
        #print(self.wallet.private_BIP32_root_key)
        if self.export_xprv_dialog:
            self.export_xprv_dialog.dismiss()
            self.export_xprv_dialog = None
        self.show_snackbar("xpriv saved as {}".format(self._xpriv_file))

    def _cancel_xpriv_file(self, *args):
        self._xpriv_file = None
        if self.export_xprv_dialog:
            self.export_xprv_dialog.dismiss()
            self.export_xprv_dialog = None
        print ("self._xpriv_file = {}".format(self._xpriv_file))

    def select_path(self, path: str):
        '''
        It will be called when you click on the file name
        or the catalog selection button.

        :param path: path to the selected directory or file;

        Export XPRV w/ Coldcard compatibility

        Exports a cleartext file with the BIP-32 base58-serialized extended master private key.
        This is also known as Wallet Import Format, WIF.

        Copy friendly borrowed from Coldcard due to export/import compatibility:

        Please note there is no encryption for this method, and therefore, it is very hazardous and only recommended for testing purposes.

        Please note that a cleartext file is exported without encryption or protection.
        This is dangerous and is recommended for testing purposes only.
        This is dangerous and only recommended for testing purposes.
        This is only recommended for testing purposes.

        '''

        self.exit_manager()



        self._xpriv_file = "{}/xprv-{}".format(path, self.wallet.fingerprint)

        self.export_xprv_dialog = MDDialog(
                title="Export BIP32 Root Key (WIF)",
                text="Please note that a cleartext file is exported without encryption or protection.\n\nThis is dangerous and is recommended for testing purposes only.",
                buttons=[
                    MDFlatButton(
                        text="CANCEL",
                        on_release = partial(self._cancel_xpriv_file)
                    ),
                    MDFlatButton(
                        text="OK, EXPORT",
                        on_release= partial(self._export_xpriv_file)
                    ),
                ],

            )
        self.export_xprv_dialog.open()



    def exit_manager(self, *args):
        '''Called when the user reaches the root of the directory tree.'''

        self.manager_open = False
        self.file_manager.close()

    def file_manager_events(self, instance, keyboard, keycode, text, modifiers):
        '''Called when buttons are pressed on the mobile device.'''

        if keyboard in (1001, 27):
            if self.manager_open:
                self.file_manager.back()
        return True
    # END EXPORT #####


    def close_wallet_context_view(self, current="main"):
        """
        Used for settings and wallet mechanics, not transactions.
        """
        self.root.ids.toolbar.left_action_items = [["menu", lambda x: self.nav_drawer_handler()], ["theme-light-dark", lambda x: app.switch_theme_handler()]]
        self.root.ids.toolbar.right_action_items = []
        app.root.ids.sm.current = current

    def load_seed_view(self):
        self.root.ids.toolbar.left_action_items = [["close", lambda x: self.close_wallet_context_view()]]
        self.root.ids.toolbar.right_action_items = [["file-download-outline", lambda x: self.download_prv()]]
        self.root.ids.nav_drawer.set_state("close")
        self.root.ids.sm.current = "seed"

    def load_bip39_mnemonic_view(self):
        self.root.ids.toolbar.left_action_items = [["close", lambda x: self.close_wallet_context_view()]]
        #self.root.ids.toolbar.right_action_items = [["file-download-outline", lambda x: self.download_prv()]]
        self.root.ids.nav_drawer.set_state("close")
        self.root.ids.sm.current = "bip39_mnemonic_screen"


    def load_pubkey_view(self):
        self.root.ids.toolbar.left_action_items = [["close", lambda x: self.close_wallet_context_view()]]
        self.root.ids.nav_drawer.set_state("close")
        self.root.ids.sm.current = "ypub"

    def load_exchangerate_view(self):
        self.root.ids.toolbar.left_action_items = [["close", lambda x: self.close_wallet_context_view()]]
        self.root.ids.nav_drawer.set_state("close")
        self.root.ids.sm.current = "exchangerate"

    def load_blockheight_view(self):
        self.root.ids.toolbar.left_action_items = [["close", lambda x: self.close_wallet_context_view()]]
        self.root.ids.nav_drawer.set_state("close")
        self.root.ids.sm.current = "blockheightscreen"

    def check_entropy(self):
        """ Update entropy hint. Aim for 128+ bits """
        passphrase_entropy_bits = entropy_bits(self.root.ids.pass_field.text)
        print(passphrase_entropy_bits)
        self.root.ids.pass_progress.set_norm_value(passphrase_entropy_bits/128.)
        if passphrase_entropy_bits >= 128:
            self.root.ids.passphrase_hint.text = ""
            self.root.ids.pass_progress.color = "green"
        else:
            if passphrase_entropy_bits >= 128/3*2:
                self.root.ids.pass_progress.color = "orange"
            elif passphrase_entropy_bits >= 128/2:
                self.root.ids.pass_progress.color = "#DD6E0F"
            else:
                self.root.ids.pass_progress.color = "red"
            self.root.ids.passphrase_hint.color = "red"
            self.root.ids.passphrase_hint.text = "WARNING: Use a better passphrase!"
        if int(passphrase_entropy_bits) >= 128:
            self.root.ids.passphrase_hint.color = "black"
            self.root.ids.passphrase_hint.text = "~{} bits of entropy".format(int(passphrase_entropy_bits))




    def menu_item_handler(self, text):
        # Main menu items
        if "PUB" in text:
            self.root.ids.sm.current = "ypub"
        if "BIP32" in text:
            self.root.ids.sm.current = "seed"
        elif self.root.ids.sm.current == "utxo": # UTXO menu items
            addr = self.utxo.address(self.chain.netcode)
            key = self.wallet.search_for_key(addr)
            if not key:
                key = self.wallet.search_for_key(addr, change=True)

            if "Private" in text:
                self.show_dialog("Private key", "", qrdata=key.wif())
            if "Redeem" in text:
                if self.bech32:
                    return
                script = b2h(key.p2wpkh_script())
                self.show_dialog("Redeem script", "", qrdata=script)


    def fee_select_callback(self, selected_fee="custom"):

        """mempool_recommended_fees = {  "fastestFee": 5,
                                      "halfHourFee": 4,
                                      "hourFee": 3,
                                      "economyFee": 2,
                                      "minimumFee": 1
                                    }
        """
        if selected_fee == "custom":
            # We are setting minimum fee as inital value to prevent that the Tx
            # will be dropped out of the mempool. Can be overwritten in the UI.
            selected_fee = "minimumFee"
        if self.mempool_recommended_fees:
            chosen_fee = self.mempool_recommended_fees.get(selected_fee, 1)
        else:
            chosen_fee = 1
        self.root.ids.fee_input.text = str(chosen_fee)
        self.current_fee = chosen_fee
        self.fee_selection.dismiss()

    def fee_input_handler(self):
        text = self.root.ids.fee_input.text
        if text:
            self.current_fee = int(float(text))
        self.fee_selection.dismiss()

    def set_address_error(self, addr):
        netcode = self.chain.netcode
        is_valid = is_valid_address(addr, netcode)
        self.root.ids.address_input.error = not is_valid

    def set_amount_error(self, amount):
        _amount = Decimal(amount) if amount else Decimal("0")
        is_valid = _amount / self.unit_factor <= self.wallet.balance
        self.root.ids.spend_amount_input.error = not is_valid

    async def do_spend(self, address, amount, fee_rate):
        self.spend_tuple = await self.wallet.spend(address,
                                                    amount,
                                                    fee_rate,
                                                    rbf=self.rbf)

    async def do_broadcast(self):
        if self.spend_tuple:
            tx, chg_vout, decimal_fee, tx_vsize, del_utxo_candidates = self.spend_tuple
            chg_out = tx.txs_out[chg_vout]  # type: TxOut
            txid, exception = await self.wallet.broadcast(tx.as_hex(), chg_out)  # type: str
            if txid:
                # successfully broadcasted
                # remove UTXOs once broadcasted
                self.wallet.utxos = []
                for i, utxo in enumerate(self.wallet.utxos):
                    if i not in del_utxo_candidates and utxo not in self.wallet.utxos:
                        self.wallet.utxos.append(utxo)
                self.update_screens()
                self.goto_screen('main', 'TRANSACTIONS')
                if self.tx_btm_sheet:
                    self.tx_btm_sheet.dismiss()
                    self.tx_btm_sheet = None

                # Reset last used values in send tab
                self.fee_select_callback()
                self.root.ids.address_input.text = ""
                self.root.ids.address_input.error = False
                self.root.ids.spend_amount_input_fiat.text = "0"
                self.root.ids.spend_amount_input.text = "0"

                self.show_snackbar("Transaction {}..{} sent.".format(txid[:11],txid[-11:]))
            else:
                try:
                    error_message = str(exception).split("[")[0]
                    _, error_message = error_message.split("'message': '")
                    if error_message.startswith("'"):
                        error_message = error_message[1:]
                    if error_message.endswith("'"):
                        error_message = error_message[:-1]
                    error_message = error_message.replace("\n", " ")
                except Exception as ex:
                    error_message = "An error occurred. \n\n{}".format(ex)

                self.show_dialog("Error", error_message)
                self.tx_btm_sheet.dismiss()
                self.show_snackbar("Failed to broadcast transaction!")



        else:
            self.show_snackbar("No transaction to broadcast.")

    async def send_button_handler(self):
        addr_input = self.root.ids.address_input
        address = addr_input.text.strip()
        logging.info("send_button_handler: address={}".format(address))
        amount_str = self.root.ids.spend_amount_input.text
        amount = Decimal(amount_str) / self.unit_factor

        if addr_input.error or not address:
            self.show_dialog("Error", "Invalid address.")
            return
        elif amount > self.wallet.balance:
            self.show_dialog("Error", "Insufficient funds.")
            return
        elif not amount:
            self.show_dialog("Error", "Amount cannot be zero.")
            return

        fee_rate_sat = int(Decimal(self.current_fee))
        fee_rate = nowallet.Wallet.satb_to_coinkb(fee_rate_sat)
        await self.do_spend(address, amount, fee_rate)
        logging.info("Finished doing TX")

        tx, chg_vout, decimal_fee, tx_vsize, del_utxo_candidates = self.spend_tuple

        message = "Added a miner fee of: {} {}".format(
            decimal_fee, self.chain.chain_1209k.upper())
    #    message += "\nTxID: {}...{}".format(txid[:13], txid[-13:])
        #if self.broadcast_tx:
        #    self.show_dialog("Transaction sent!", message)
        #else:
            #self.show_dialog("Transaction ready!", message)
        self.tx_btm_sheet = open_tx_preview_bottom_sheet(signed_tx=tx)

    def check_new_history(self):
        if self.wallet.new_history:
            logging.info("self.wallet.new_history=True")
            self.update_screens()
            self.show_snackbar("Transaction history updated.")
            self.wallet.new_history = False

    def wallet_ready(self):
        """
        Wallet is ready.
        - load main screen
        - unlock nav
        """

        self._wallet_ready = True
        print("_wallet_ready=True")
        self.root.ids.sm.current = "main"
        self.root.ids.active_wallet_version.text = "Version {}".format(__version__)
        # All methods below verify if self._wallet_ready is True.
        #self._unlock_nav_drawer()
        #self.show_dialog("Loaded for the first time?", "If you are loading this wallet for the first time, it is recommended to close it and reload it.\n\This way you can make sure that you did not make a typo.\n\nIf the wallet is ___ again, then everything is fine.")
        #  in your salt or passphrase
        if len(self.wallet.get_tx_history()) == 0:
            self.show_dialog("New wallet?",
                    "To make sure that you did not make a typo, it is recommended to close the wallet now and reloading it.\n\nIf the wallet name is '{}' after reloading it, everything is fine.".format(
                    wallet_alias(self.wallet.fingerprint[0:2], self.wallet.fingerprint[2:4])))
    @property
    def pub_char(self):
        if self.chain == nowallet.BTC:
            return "z" if self.bech32 else "y"
        elif self.chain == nowallet.TBTC:
            return "v" if self.bech32 else "u"

    async def do_login(self):
        email = self.root.ids.email_field.text
        passphrase = self.root.ids.pass_field.text
        confirm = self.root.ids.confirm_field.text
        if not email or not passphrase or not confirm:
            self.show_dialog("Error", "All fields are required.")
            return
        if passphrase != confirm:
            self.show_dialog("Error", "Passwords did not match.")
            return
        self.bech32 = self.root.ids.bech32_checkbox.active
        self.menu_items[0]["text"] = "View {}PUB".format(self.pub_char.upper())

        self.close_wallet_context_view(current="wait")

        try:
            await self.do_login_tasks(email, passphrase)
        except (SocksConnectionError, ClientConnectorError):
            self.show_dialog("Error",
                             "Make sure Tor/Orbot is installed and running before using Brainbow.",
                             cb=lambda x: sys.exit(1))
            return
        self.update_screens()
        self.wallet_ready()
        await asyncio_gather(
            self.new_history_loop(),
            self.do_listen_to_headers(), # <--
            self.do_listen_task(),
            self.update_exchange_rates(),
            self.check_new_block(),
            )



    async def do_bip39_login(self):
        #TODO: Check for seed validity
        #TODO: Check pasphase

        bip39_mnemonic = self.root.ids.bip39_mnemonic.text
        """
        passphrase = self.root.ids.pass_field.text
        confirm = self.root.ids.confirm_field.text
        if not email or not passphrase or not confirm:
            self.show_dialog("Error", "All fields are required.")
            return
        if passphrase != confirm:
            self.show_dialog("Error", "Passwords did not match.")
            return

        self.bech32 = self.root.ids.bech32_checkbox.active
        """
        self.menu_items[0]["text"] = "View {}PUB".format(self.pub_char.upper())

        self.close_wallet_context_view(current="wait")

        try:
            await self.do_login_tasks(bip39_mnemonic=bip39_mnemonic, bip39_passphrase=None)
        except (SocksConnectionError, ClientConnectorError):
            self.show_dialog("Error",
                             "Make sure Tor/Orbot is installed and running before using Brainbow.",
                             cb=lambda x: sys.exit(1))
            return
        self.update_screens()
        self.wallet_ready()
        await asyncio_gather(
            self.new_history_loop(),
            self.do_listen_to_headers(), # <--
            self.do_listen_task(),
            self.update_exchange_rates(),
            self.check_new_block(),
            )

    def bip39_login(self):
        """
        Alternative BIP39 login routine
        """
        task1 = asyncio_create_task(self.do_bip39_login())

    def login(self):
        task1 = asyncio_create_task(self.do_login())



    def logoff(self, *args, **kwargs):
        #self.show_dialog("Disconnected.","")
        try:
            MDApp.get_running_app().stop()
        except:
            pass
        sys.exit(0)

    #
    def disconnect_callback(self, *args, **kwargs ):
        dialog_height = 200
        self._disconnect_dialog = MDDialog(title="Electrum server connection lost!",
                   text="Please quit and reopen Brainbow", # , or try to reconnect.
                   size_hint=(.8, None),
                   height=dp(dialog_height),
                   auto_dismiss=False,
                   buttons=[
                      # MDFlatButton(
                        #   text="TYR RECONNECT",
                        #   on_release=partial(self.close_disconnect_dialog_and_reconnect))
                       #,
                       MDFlatButton(
                           text="QUIT",
                           on_release=partial(self.logoff))
                       ,
                       MDFlatButton(
                           text="DISMISS",
                           on_release=partial(self.close_disconnect_dialog))
                       ]
                   )
        self._disconnect_dialog.open()
        # exit wallet, continue offline

    async def track_top_block(self):
        global top_blk
        fut, Q = self.wallet.connection.client.subscribe('blockchain.headers.subscribe') # listen_subscribe
        top_blk = await fut
        while 1:
            top_blk = max(await Q.get())
            print("new top-block: %r" % (top_blk,))

    #
    async def do_listen_to_headers(self):
        logging.info("Listening for new headers, do_listen_to_headers.")
        #task = asyncio_create_task(self.wallet.listen_to_headers())
        task1 = asyncio_create_task(self.track_top_block())

    #

    async def do_listen_task(self):
        logging.info("Listening for new transactions.")
        task = asyncio_create_task(self.wallet.listen_to_addresses())

    async def do_login_tasks(self, email=None, passphrase=None, bip39_mnemonic=None, bip39_passphrase=None):
        self.root.ids.wait_text.text = "Connecting".upper()
        self.root.ids.wait_text_small.text = "Getting a random server for you."
        try:
            server, port, proto = await get_random_server(self.loop)
            print ("server, port, proto = {} {} {} ".format(server, port, proto))
            self.root.ids.wait_text_small.text = "Connected to {}.".format(server)
        except:
            pass
        try:
            connection = nowallet.Connection(self.loop, server, port, proto, disconnect_callback=self.disconnect_callback)
        except Exception as ex:
            print(traceback.format_exc())
            await connection.do_connect()
        await connection.do_connect()

        if email and passphrase:
            self.root.ids.wait_text.text = "Deriving\nKeys".upper()
            self.root.ids.wait_text_small.text = "Deriving keys will take some time to complete."
            self.wallet = nowallet.Wallet(salt=email, passphrase=passphrase,
                                bip39_mnemonic=None, bip39_passphrase=None,
                                connection=connection, loop=self.loop,
                                chain=self.chain, bech32=self.bech32)
        elif bip39_mnemonic:
            self.root.ids.wait_text.text = "Loading\nBIP39\nmnemonic".upper()
            self.wallet = nowallet.Wallet(salt=None, passphrase=None,
                                bip39_mnemonic=bip39_mnemonic,
                                bip39_passphrase=bip39_passphrase,
                                connection=connection, loop=self.loop,
                                chain=self.chain, bech32=self.bech32)
        else:
            self.show_dialog("Error",
                             "Please provide either your salt and passphrase or your BIP39 mnemonic to use Brainbow.",
                             cb=lambda x: sys.exit(1))
            return
        self.set_wallet_fingetprint(self.wallet.fingerprint)
        self.root.ids.wait_text_small.text = \
                "Wallet fingerprint is {}.\n{}\n".format(
                        self.wallet.fingerprint,
                        wallet_alias(self.wallet.fingerprint[0:2],
                                self.wallet.fingerprint[2:4]))
        self.root.ids.wait_text.text = "Fetching\nhistory".upper()
        await self.wallet.discover_all_keys()

        # For future compatibility - currently it's initialized with "BTC" so this is a no-op.
        if self.currency != "BTC":
            self.root.ids.wait_text.text = "Fetching\nexchange\nrates".upper()
            # just await, but since the fetching url ruturns 403 make it anything
            try:
                self.exchange_rates = await fetch_exchange_rates(nowallet.BTC.chain_1209k)
            except:
                self.exchange_rates = False
                self.show_snackbar("Failed fetching exchange rates. Starting without...")

        self.root.ids.wait_text.text = "Getting\nfee\nestimate".upper()

        coinkb_fee = await self.wallet.get_fee_estimation(6)
        self.current_fee = nowallet.Wallet.coinkb_to_satb(coinkb_fee)

        #self.root.ids.wait_text_small.text = "Wating for fee estimate .."

        coinkb_fee = await self.wallet.get_relayfee()
        relayfee = nowallet.Wallet.coinkb_to_satb(coinkb_fee)

        print("fee {} relay {}".format(self.current_fee, relayfee))

        self.mempool_recommended_fees = {}
        if self.current_fee == relayfee:
            self.mempool_recommended_fees = {
                "fastestFee": self.current_fee,
                "halfHourFee": self.current_fee,
                "hourFee": self.current_fee,
                "economyFee": self.current_fee,
                "minimumFee": relayfee
            }
        else:
            coinkb_fee = await self.wallet.get_fee_estimation(3)
            halfHourFee = nowallet.Wallet.coinkb_to_satb(coinkb_fee)

            coinkb_fee = await self.wallet.get_fee_estimation(1)
            fastestFee = nowallet.Wallet.coinkb_to_satb(coinkb_fee)

            self.mempool_recommended_fees = {
                "fastestFee": fastestFee,
                "halfHourFee": halfHourFee,
                "hourFee": self.current_fee,
                "economyFee": relayfee,
                "minimumFee": relayfee
            }
        logging.info("Finished 'doing login tasks'")
        logging.info("all known addreses {}".format(self.wallet.get_all_known_addresses(addr=True)))

    def update_screens(self):
        self.update_balance_screen()
        self.update_send_screen()
        self.update_recieve_screen()
        self.update_ypub_screen()
        self.update_seed_screen() # BIP32
        self.update_bip39_mnemonic_screen() # BIP39
        self.update_utxo_screen()

    async def new_history_loop(self):
        while True:
            await asyncio_sleep(1)
            self.check_new_history()

    async def check_new_block(self):
        while True:
            await asyncio_sleep(1)
            try:
                tip = top_blk.get('height', 0)
                if tip > self.block_height:
                    self.block_height = tip
                    self.root.ids.blockheight_lbl.text = "[b]{}[/b]".format(tip)
                    logging.info("NEW self.block_height={}".format(self.block_height))
                    self.update_balance_screen()
                    self.show_snackbar("Block {} found!".format(self.block_height))
            except Exception as err:
                print(traceback.format_exc())
                logging.error(err)
                self.block_height = 0


    async def update_exchange_rates(self):
        sleep_time = 15
        while True:
            await asyncio_sleep(sleep_time)
            if self.currency != "BTC" or \
                (self.currency == "BTC" and Decimal(self.get_rate()) > Decimal(0)):
                logging.info("run fetch_exchange_rates")
                sleep_time = 60
                old_rates = self.exchange_rates
                try:
                    self.exchange_rates = await fetch_exchange_rates(nowallet.BTC.chain_1209k)
                except:
                    self.exchange_rates = old_rates or False
                    logging.info("Restoring exchange rates using old_rates.")
                self.update_balance_screen()
                #if self.currency != "BTC":
                #    self.show_snackbar("Exchange rates updated. {}".format(self.get_rate()))

    def toggle_balance_label(self):
        #self.dump_history_to_fs()
        if self._fiat_fields_hidden is False:
            self.fiat_balance = not self.fiat_balance
            self.update_balance_screen()
        else:
            pass




    def balance_str(self, fiat=False):
        balance, units = None, None
        if not fiat:
            balance = self.unit_precision.format(self.wallet.balance * self.unit_factor)
            #if self.units == "sats (BTC)":
            #    units = "sats"  # Testnet will be displayed as "sats (TBTC)"
            #else:
            units = self.units
        else:
            if self.currency == "BTC":
                balance = "{:.8f}".format(self.wallet.balance)
            else:
                balance = "{:.2f}".format(self.wallet.balance * self.get_rate())
            units = self.currency
        return "{} {}".format(balance, units)

    def set_wallet_fingetprint(self, fingerprint):
        walias = wallet_alias(fingerprint[0:2], fingerprint[2:4])
        self.root.ids.toolbar.title = walias
        self.root.ids.active_wallet_alias.text = "{} ({})".format(walias, fingerprint)
        #self.root.ids.toolbar.title = fingerprint.upper()
        if self.chain  == nowallet.TBTC:
            self.root.ids.toolbar.title += " TESTNET"

    #def total_wallet_tx_count(self):
    #    return len(self.wallet.get_tx_history())

    def dump_history_to_fs(self):
        """
        return {
            "txid": self.tx_obj.id(),
            "is_spend": self.is_spend,
            "value": str(self.value),
            "height": self.height,
            "timestamp": self.timestamp
        }
        """
        f = open("dump_history.csv", 'w')
        for hist in self.wallet.get_tx_history():
            f.write("{}, {}, {}, {}\n".format(hist.value, hist.is_spend, hist.tx_obj.id(), hist.tx_obj.as_hex()))
        f.close()


    def update_balance_screen(self):
        self.root.ids.balance_label.text = self.balance_str(fiat=self.fiat_balance)
        self.root.ids.recycleView.data_model.data = []
        tx_counter = 0
        for hist in self.wallet.get_tx_history():
            verb = "-" if hist.is_spend else "+"
            #if self.units.startswith("sats"):
            val = self.unit_precision.format(hist.value * self.unit_factor)
            hist_str = "{}{} {}".format(verb, val, self.units)
            self.add_list_item(hist_str, hist)
            tx_counter += 1
        self.root.ids.nav_drawer_item_transactions.right_text = "{}".format(tx_counter)
        self.root.ids.nav_drawer_item_transactions.size_hint_x = None
        try:
            if self.currency in ["BTC", "TBTC"]:
                rate = "1"
            else:
                rate = "{:.2f}".format(self.get_rate())
            self.root.ids.current_btc_exchange_rate.text = \
                "1 BTC = {} {}".format(rate, self.currency)
        except Exception as ex:
            print (ex)
            pass

    def update_utxo_screen(self):
        balance = Decimal(0)
        self.root.ids.utxoRecycleView.data_model.data = []
        self.wallet.utxos = utxo_deduplication(self.wallet.utxos)
        for utxo in self.wallet.utxos:
            #print("*"*30)
            #print(dir(utxo))
            value = Decimal(str(utxo.coin_value / nowallet.Wallet.COIN))
            balance += value
            utxo_str = (self.unit_precision + " {}").format(value * self.unit_factor, self.units)
            _utxo = {"text": utxo_str,
                     "secondary_text": "{}....{}:{}".format(
                        str(utxo.tx_hash)[:19],
                        str(utxo.tx_hash)[-19:],
                        utxo.tx_out_index),  #Spendable
                     "utxo": utxo,
                     "tertiary_text": "{}".format(utxo.address("XTN")),

                     }
            self.root.ids.utxoRecycleView.data_model.data.append(_utxo)
        self.update_addresses_screen()
        print ("Computed balance: {}".format(balance))

    def update_send_screen(self):
        self.root.ids.send_balance.text = \
            "Available balance:\n" + self.balance_str()
        self.root.ids.fee_input.text = str(self.current_fee)

    def update_recieve_screen(self):
        address = self.update_recieve_qrcode()
        encoding = "bech32" if self.wallet.bech32 else "P2SH"
        current_addr = "\nCurrent receive address ({}):\n\n{}\n\n".format(encoding, address)
        #TODO: add derivation path, eg. m/49'/1'/0'/0/5
        self.root.ids.addr_label.text = "{}".format(current_addr)

    def update_recieve_qrcode(self):
        address = self.wallet.get_address(
            self.wallet.get_next_unused_key(), addr=True)
        # address = self.wallet.get_address(
        #         self.wallet.get_key(index=0, change=False),
        #         addr=True
        #         )
        logging.info("Current address: {}".format(address))
        amount = Decimal(self.current_coin) / self.unit_factor
        self.root.ids.addr_qrcode.data = \
            "bitcoin:{}?amount={}".format(address, amount)
        return address

    def update_ypub_screen(self):
        ypub = self.wallet.ypub
        ypub = self.pub_char + ypub[1:]
        self.root.ids.ypub_label.text = "{}".format(ypub)
        self.root.ids.ypub_qrcode.data = ypub

    def update_seed_screen(self):
        try:
            self.root.ids.seed_label.text = \
                "{}".format(self.wallet.private_BIP32_root_key)
            self.root.ids.seed_qrcode.data = self.wallet.private_BIP32_root_key
        except Exception as ex:
            print(traceback.format_exc())
            print(ex)
            self.root.ids.seed_label.text = ""
            self.root.ids.seed_qrcode.data = ""

    def update_bip39_mnemonic_screen(self):
        try:
            self.root.ids.bip39_mnemonic_label.text = "{}".format(self.wallet.bip39_mnemonic)
            self.root.ids.bip39_mnemonic_qrcode.data = "{}".format(self.wallet.bip39_mnemonic)
        except Exception as ex:
            print(traceback.format_exc())
            print(ex)
            self.root.ids.bip39_mnemonic_label.text = ""
            self.root.ids.bip39_mnemonic_qrcode.data = ""


    def open_address_bottom_sheet_callback(self, address):
        from bottom_screens_address import open_address_bottom_sheet
        open_address_bottom_sheet(address=address)

    def _update_addresses_screen(self, change=False):
        all_used_addresse = self.wallet.get_all_used_addresses(receive=not change, change=change)
        for address in self.wallet.get_all_known_addresses(addr=True, change=change):
            item = {
                "icon": 'database-marker' if address in all_used_addresse else 'database-marker-outline',
                "text": address,
                "secondary_text": "Derivation: m{}'/{}'/{}'/{}/{} {}".format(
                    self.wallet.derivation.get('bip'),
                    self.wallet.derivation.get('bip44'),
                    self.wallet.derivation.get('account'),
                    '1' if change else '0',
                    self.wallet.search_for_index(search=address, addr=True, change=change),
                    'already used' if address in all_used_addresse else ''),
                    "on_release": lambda address=address: self.open_address_bottom_sheet_callback(address)
                }
            if change:
                self.root.ids.changeaddresses_recycle_view.data_model.data.append(item)
            else:
                self.root.ids.addresses_recycle_view.data_model.data.append(item)



    def update_addresses_screen(self):
        self.root.ids.addresses_recycle_view.data_model.data = []
        self.root.ids.changeaddresses_recycle_view.data_model.data = []
        self._update_addresses_screen(change=False)
        self._update_addresses_screen(change=True)

    """

    THIS IS BUGGY AS FUCK!

    all_used_addresse = self.wallet.get_all_used_addresses()

    this returns the index used of both, the receiving and the change addresses

    can't do something meaningful without knowing if an index is change or not .


        def _update_addresses_screen(self, change=False):
            if change:
                self.root.ids.changeaddresses_recycle_view.data_model.data = []
            else:
                self.root.ids.addresses_recycle_view.data_model.data = []
                all_used_addresse = self.wallet.get_all_used_addresses()
            for address in self.wallet.get_all_known_addresses(addr=True, change=False):
                addr_index = self.wallet.search_for_index(search=address, addr=True, change=False)
                self.root.ids.addresses_recycle_view.data_model.data.append({
                    "icon": 'database-marker' if addr_index in all_used_addresse else 'database-marker-outline',
                    "text": address,
                    "secondary_text": "Derivation: m{}'/{}'/{}'/{}/{} {}".format(
                        self.wallet.derivation.get('bip'),
                        self.wallet.derivation.get('bip44'),
                        self.wallet.derivation.get('account'),
                        0, # not 'change'
                        addr_index,
                        'already used' if addr_index in all_used_addresse else ''),
                        "on_release": lambda address=address: self.open_address_bottom_sheet_callback(address)
                    })


    """

    def lock_UI(self, pin):
        if not pin:
            self.show_dialog("Error", "PIN field is empty.")
            return
        self.pin = pin
        self.root.ids.pin_back_button.disabled = True
        self.root.ids.lock_button.text = "unlock"

    def unlock_UI(self, attempt):
        if not attempt or attempt != self.pin:
            self.show_dialog("Error", "Bad PIN entered.")
            return
        self.root.ids.pin_back_button.disabled = False
        self.root.ids.lock_button.text = "lock"

    def update_pin_input(self, char):
        pin_input = self.root.ids.pin_input
        if char == "clear":
            pin_input.text = ""
        elif char == "lock":
            self.lock_UI(pin_input.text)
            pin_input.text = ""
        elif char == "unlock":
            self.unlock_UI(pin_input.text)
            pin_input.text = ""
        else:
            pin_input.text += char

    def update_unit(self):
        self.unit_factor = 1
        self.unit_precision = "{:.8f}"
        if self.units[0] == "s": # sats
            self.unit_factor = 100000000
            self.unit_precision = "{:.1f}"
        coin = Decimal(self.current_coin) / self.unit_factor
        fiat = Decimal(self.current_fiat) / self.unit_factor
        self.update_amount_fields(coin, fiat)

    def get_rate(self):
        try:
            rate = self.exchange_rates[self.currency]
            return Decimal(str(rate))
        except:
            self.exchange_rates = False
            return Decimal(str(0))

    def copy_something_to_clipboard(self, something, message=""):
        Clipboard.copy(something)
        if message:
            self.show_snackbar(text=message)

    def copy_current_address_to_clipboard(self):
        if self.current_tab_name == "receive":
            try:
                current_address = self.root.ids.addr_qrcode.data.replace("bitcoin:","").split("?")[0] # "bitcoin:{}?amount={}"
                Clipboard.copy(current_address)
                self.show_snackbar(text="Copied {}...{} to clipboard.".format(current_address[:8], current_address[-8:]))
            except:
                self.show_snackbar(text="Can't copy to clipboard.")

    def update_amounts(self, text=None, type="coin"):
        if self.is_amount_inputs_locked:
            return
        try:
            amount = Decimal(text) if text else Decimal("0")
        except:
            #amount = Decimal("0.0")
            return
        rate = self.get_rate() / self.unit_factor
        new_amount = None
        if type == "coin":
            new_amount = amount * rate
            self.update_amount_fields(amount, new_amount)
        elif type == "fiat":
            new_amount = amount / rate
            self.update_amount_fields(new_amount, amount)
        self.update_recieve_qrcode()

    def update_amount_fields(self, coin, fiat):
        self.is_amount_inputs_locked = True
        _coin = self.unit_precision.format(coin)
        self.current_coin = _coin.rstrip("0").rstrip(".")
        #if self.currency == "BTC":
        #    _fiat = "{:.8f}".format(fiat)
        #    self.current_fiat = _fiat
        #else:
        _fiat = "{:.2f}".format(fiat)
        self.current_fiat = _fiat.rstrip("0").rstrip(".")
        #
        self.is_amount_inputs_locked = False

    def on_start(self):
        pass

    def build(self):
        """ """
        self.title = 'Brainbow'
        self.is_darkmode = False
        self.icon = "brain.png"

        if platform =='android':
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.CAMERA])
            request_permissions([Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])

            #from android_utils import dark_mode
            #self.is_darkmode = dark_mode()

        self.is_darkmode = True # Force dark mode for all

        # Theme settings
        self.theme_cls.material_style = "M2"
        if self.is_darkmode:
            self.theme_cls.theme_style = "Dark"
        else:
            self.theme_cls.theme_style = "Light"
        print (self.theme_cls)
        print (dir(self.theme_cls))
        #self.theme_cls.primary_hue = "200"  # "500"
        #self.theme_cls.secondary_palette = "Red"
        #self.theme_cls.primary_hue = "200"  # "500"
        #self.theme_cls.theme_style_switch_animation = True
        #self.theme_cls.theme_style_switch_animation_duration = 0.8

        self.use_kivy_settings = False
        self.rbf = self.config.getboolean("brainbow", "rbf")
        self.units = self.config.get("brainbow", "units")
        self.update_unit()
        self.currency = "BTC"# disable by default self.config.get("brainbow", "currency")
        self._hide_fiat_fields()
        self.explorer = self.config.get("brainbow", "explorer")

        LabelBase.register(name='RobotoMono', fn_regular='assets/RobotoMono-Regular.ttf')

        self.fee_selection = MDDropdownMenu(items=self.fee_preset_items,
                                            width_mult=3,
                                            caller=self.root.ids.fee_input,
                                            max_height=dp(250)
                                            )

    def build_config(self, config):
        config.setdefaults("brainbow", {
            "rbf": True,
        #    "broadcast_tx": False,
            "units": self.chain.chain_1209k.upper(),
            "currency": "USD",
            "explorer": "mempool.space",
            })
        Window.bind(on_keyboard=self.key_input)


    def build_settings(self, settings):
        coin = self.chain.chain_1209k.upper()
        #settings.add_json_panel("Settings", self.config, data=settings_json(coin))

    def on_config_change(self, config, section, key, value):
        print("on_config_change {} {} {} {}".format(config, section, key, value))
        if key == "rbf":
            self.rbf = value in [1, '1', True]
        #elif key == "broadcast_tx":
        #    self.broadcast_tx = value in [1, '1', True]
        elif key == "units":
            self.units = value
            self.update_unit()
            self.update_amounts()
            self.update_balance_screen()
            self.update_send_screen()
            self.update_utxo_screen()
        elif key == "currency":
            self.currency = value
            self.update_amounts()
        elif key == "explorer":
            self.explorer = value


    def key_input(self, window, key, scancode, codepoint, modifier):
        if key == 27:   # the back button / ESC
            return True  # override the default behaviour
        else:           # the key now does nothing
            return False


    def on_pause(self):
        if self._qrreader:
            self._qrreader.disconnect_camera()
        return True

    def on_resume(self):
        return True

    def on_stop(self):
        if self._qrreader:
            self._qrreader.disconnect_camera()
        return True

    def add_list_item(self, text, history):
        #if self.block_height:
        #    chain_tip = self.block_height
        #else:
        #    chain_tip = 0
        data = self.root.ids.recycleView.data_model.data
        if history.height == 0:
            icon = "timer-sand"
        elif abs(self.block_height-history.height)+1 < 6:
            icon = "numeric-{}-circle".format( abs(self.block_height- history.height)+1  ) # confirmation count
        else:
            icon = "check-circle"

        data.append({   "text": text,
                        "secondary_text": history.tx_obj.id(),
                        "history": history,
                        "icon": icon })

    def goto_slide(self, name):
        self.root.ids.onboarding_drawer.set_state("close")
        for i in app.root.ids.caraousel.slides:
            print(i.name == name)
            if i.name == name:
                app.root.ids.caraousel.load_slide(i)
                return

    def goto_screen(self, name, tab=None):
        if self._wallet_ready:
            self.root.ids.nav_drawer.set_state("close")
            self.root.ids.sm.current = name
            if tab and name == "main":
                self.root.ids.main_tabs.switch_tab(tab, search_by="title")



if __name__ == "__main__":
    from asyncio import new_event_loop
    loop = new_event_loop()
    app = BrainbowApp(loop)
    loop.run_until_complete(app.async_run())
    loop.close()
