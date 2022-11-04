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
import asyncio
import logging

from decimal import Decimal


from kivy.utils import platform
from kivy.core.window import Window

from kivy.compat import unichr
from kivy.metrics import dp
from kivy.properties import NumericProperty, StringProperty, ObjectProperty
from kivy.uix.screenmanager import Screen
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

from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.button import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty

#from kivy.garden.qrcode import QRCodeWidget
from kivy_garden.qrcode import QRCodeWidget

from kivy.core.clipboard import Clipboard

#from kivy_garden.zbarcam import ZBarCam


from pycoin.key import validate
from pycoin.serialize import b2h

#import __init__  as nowallet
import nowallet

from exchange_rate import fetch_exchange_rates
from settings_json import settings_json
from functools import partial
#import asynckivy as ak
import threading
import concurrent.futures

from aiosocks import SocksConnectionError
from aiohttp.client_exceptions import ClientConnectorError


__version__ = "0.0.1"
if platform == "android":
    # NFC

    from jnius import autoclass, cast
    from android.runnable import run_on_ui_thread
    from android import activity


    NfcAdapter = autoclass('android.nfc.NfcAdapter')
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Intent = autoclass('android.content.Intent')
    IntentFilter = autoclass('android.content.IntentFilter')
    PendingIntent = autoclass('android.app.PendingIntent')
    NdefRecord = autoclass('android.nfc.NdefRecord')
    NdefMessage = autoclass('android.nfc.NdefMessage')
    Tag = autoclass('android.nfc.Tag')
    IsoDep = autoclass('android.nfc.tech.IsoDep')
    MifareClassic = autoclass('android.nfc.tech.MifareClassic')
    MifareUltralight = autoclass('android.nfc.tech.MifareUltralight')
    Ndef = autoclass('android.nfc.tech.Ndef')
    NfcA = autoclass('android.nfc.tech.NfcA')
    NfcB = autoclass('android.nfc.tech.NfcB')
    NfcF = autoclass('android.nfc.tech.NfcF')
    NfcV = autoclass('android.nfc.tech.NfcV')


    # end NFC

else:
    Window.size = (768/2, 1366/2)

from utils import get_block_height

LOG_OFF_WALLET = "Disconnect and clear wallet"

class Tab(MDFloatLayout, MDTabsBase):
    '''Class implementing content for a tab.'''
    content_text = StringProperty()
    pass


# Declare screens
class LoginScreen(Screen):
    pass


class MainScreen(Screen):
    pass


class WaitScreen(Screen):
    pass


class UTXOScreen(Screen):
    pass


class YPUBScreen(Screen):
    pass

class SeedScreen(Screen):
    pass


class PINScreen(Screen):
    pass


class ZbarScreen(Screen):
    pass


class TXReviewScreen(Screen):
    pass




# Declare custom widgets
class IconLeftSampleWidget(ILeftBodyTouch, MDIconButton):
    pass


class BalanceLabel(ButtonBehavior, MDLabel):
    pass


class PINButton(MDRaisedButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.height = dp(50)


class UTXOListItem(TwoLineListItem):
    utxo = ObjectProperty()

    def open_utxo_menu(self):
        app = MDApp.get_running_app()
        app.utxo = self.utxo
        self.utxo_menu = MDDropdownMenu(items=app.utxo_menu_items, width_mult=4, caller=self, max_height=dp(100))
        self.utxo_menu.open()
        for d in dir(app.utxo):
            try:
                print("{} -> {}".format(d, getattr(app.utxo, d)))
            except:
                pass
        logging.info("open_utxo_menu utxo > {}".format(app.utxo.as_dict))


# class MyMenuItem(MDMenuItem):
class MyMenuItem(OneLineListItem):
    pass

class ListItem(TwoLineIconListItem):
    icon = StringProperty("check-circle")
    history = ObjectProperty()

    def on_press(self):
        app = MDApp.get_running_app()
        base_url, chain = None, app.chain.chain_1209k
        txid = self.history.tx_obj.id()
        if app.explorer == "blockcypher":
            base_url = "https://live.blockcypher.com/{}/tx/{}/"
            if app.chain == nowallet.TBTC:
                chain = "btc-testnet"
        elif app.explorer == "smartbit":
            base_url = "https://{}.smartbit.com.au/tx/{}/"
            if app.chain == nowallet.BTC:
                chain = "www"
            elif app.chain == nowallet.TBTC:
                chain = "testnet"
        url = base_url.format(chain, txid)
        open_url(url)


class FloatInput(MDTextField):
    pat = re.compile('[^0-9]')

    def insert_text(self, substring, from_undo=False):
        pat = self.pat
        if '.' in self.text:
            s = re.sub(pat, '', substring)
        else:
            s = '.'.join([re.sub(pat, '', s) for s in substring.split('.', 1)])
        return super(FloatInput, self).insert_text(s, from_undo=from_undo)


class NowalletApp(MDApp):
    units = StringProperty()
    currency = StringProperty()
    current_coin = StringProperty("0")
    current_fiat = StringProperty("0")
    current_fee = NumericProperty()
    current_utxo = ObjectProperty()
    block_height = 0
    _wallet_ready = False  # is false until we can use the wallet
    _nfc_is_on = False
    _nfc_is_available = False
    def __init__(self, loop):
        self.chain = nowallet.TBTC
        self.loop = loop
        self.is_amount_inputs_locked = False
        self.fiat_balance = False
        self.bech32 = False
        self.exchange_rates = None
        self.current_tab_name = "balance"
        self.menu_items = [{"viewclass": "MyMenuItem",
                            "text": "View YPUB",
                            "on_release": lambda x="View YPUB": app.menu_item_handler(x)},
                            {"viewclass": "MyMenuItem",
                            "text": "View BIP32 Root Key (WIF)",
                            "on_release": lambda x="View BIP32 Root Key (WIF)": app.menu_item_handler(x)},
                           {"viewclass": "MyMenuItem",
                            "text": "Lock with PIN",
                            "on_release": lambda x="Lock with PIN": app.menu_item_handler(x)},
                           {"viewclass": "MyMenuItem",
                            "text": "Manage UTXOs",
                            "on_release": lambda x="Manage UTXOs": app.menu_item_handler(x)},
                           {"viewclass": "MyMenuItem",
                            "text": "Settings",
                            "on_release": lambda x="Settings": app.menu_item_handler(x)},
                           {"viewclass": "MyMenuItem",
                            "text": LOG_OFF_WALLET,
                            "on_release": lambda x=LOG_OFF_WALLET: app.menu_item_handler(x)},
                           ]
        self.utxo_menu_items = [{"viewclass": "MyMenuItem",
                                 "text": "View Private key"},
                                {"viewclass": "MyMenuItem",
                                 "text": "View Redeem script"}]
        super().__init__()

    # NFC
    def get_ndef_details(self, tag):
        # Get all the details from the tag.
        tag_details = ""
        details = {}
        try:
            #print 'id'
            tag_uid = ':'.join(['{:02x}'.format(bt & 0xff) for bt in tag.getId()])
            tag_details= "UID: "+ tag_uid
            details['uid'] = tag_uid

            #print 'technologies'
            tag_details+="\nTECH LIST: "+str(tag.getTechList())

            #print 'get NDEF tag details'
            ndefTag = cast('android.nfc.tech.Ndef', Ndef.get(tag))

            #print 'tag size'
            tag_details+="\nSIZE: "+str(ndefTag.getMaxSize())

            #print 'is tag writable?'
            tag_details+="\nWRITABLE: "+str(ndefTag.isWritable())


            #print 'tag type'
            tag_details+="\nTAG TYPE: "+str(ndefTag.getType())

            # get size of current records
            ndefMesg = ndefTag.getCachedNdefMessage()
            # check if tag is empty
            if not ndefMesg:
                tag_details+="\nNDEF MESSAGE: NO NDEF MESSAGE"
            else:
                ndefrecords =  ndefMesg.getRecords()
                length = len(ndefrecords)
                recTypes = []
                for record in ndefrecords:
                    recTypes.append({
                        'type': ''.join(map(unichr, record.getType())),
                        'payload': ''.join(map(unichr, record.getPayload()))
                        })
                tag_details+="\nREC TYPES: "+str(recTypes)
            print(tag_details)

        except Exception as err:
            print(traceback.format_exc())
            print("ERROR: "+str(err))
        return details


    def on_new_intent(self, intent):
        print ('on_new_intent(), {}'.format(intent.getAction()) )
        # get TAG details
        tag = cast('android.nfc.Tag', intent.getParcelableExtra(NfcAdapter.EXTRA_TAG))
        try:
            print("="*80)
            if intent.getAction() != NfcAdapter.ACTION_NDEF_DISCOVERED:
                return
            rawmsgs = intent.getParcelableArrayExtra(NfcAdapter.EXTRA_NDEF_MESSAGES)
            if not rawmsgs:
                return
            for message in rawmsgs:
                message = cast(NdefMessage, message)
                payload = message.getRecords()[0].getPayload()
                print ('payload: {}'.format(''.join(map(chr, payload))))
            print("S="*40)
        except Exception as err:
            print(traceback.format_exc())
            print("ERROR: "+str(err))
            print("ERR="*20)
        print ('details, {}'.format(tag))
        details = self.get_ndef_details(tag)
        print ('details, {}'.format(details))
        #self.show_snackbar('details, {}'.format(tag))
        #self.show_snackbar('details, {}'.format(details))

    def nfc_init(self):
        if platform == "android":
            activity.bind(on_new_intent=self.on_new_intent)
            self.j_context = context = PythonActivity.mActivity
            self.nfc_adapter = NfcAdapter.getDefaultAdapter(context)
            """
            PendingIntent pendingIntent = null;

            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.S) {
                pendingIntent = PendingIntent.getActivity
                       (this, 0, notificationIntent, PendingIntent.FLAG_MUTABLE);
            }
            else
            {
                 pendingIntent = PendingIntent.getActivity
                        (this, 0, notificationIntent, PendingIntent.FLAG_ONE_SHOT);
            }
            """

            #self.nfc_pending_intent = PendingIntent.getActivity(context, 0, Intent(context, context.getClass()).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP), 0)
            self.nfc_pending_intent = PendingIntent.getActivity(context, 0, Intent(context, context.getClass()).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP), PendingIntent.FLAG_MUTABLE)
            self.enable_nfc_foreground_dispatch()
            return True
        return False

    def disable_nfc_foreground_dispatch(self):
        if platform == "android":
            run_on_ui_thread(self.nfc_adapter.disableForegroundDispatch(self.j_context))


    def enable_nfc_foreground_dispatch(self):
        if platform == "android":
            run_on_ui_thread(self.nfc_adapter.enableForegroundDispatch(self.j_context, self.nfc_pending_intent, None,None))

    def nfc_enable(self):
        if platform == "android":
            if not self._nfc_is_on:
                activity.bind(on_new_intent=self.on_new_intent)
                self._nfc_is_on = True
                self.show_snackbar("NFC enabled")
        else:
            self.show_snackbar("NFC not supported")
                    
    def nfc_disable(self):
        if platform == "android":
            if self._nfc_is_on:
                activity.unbind(on_new_intent=self.on_new_intent)
                self._nfc_is_on = False
                self.show_snackbar("NFC disabled")
        else:
            self.show_snackbar("NFC not supported")
    def nfc_toggle(self):
        if not self._nfc_is_on:
            self.nfc_enable()
        elif self._nfc_is_on:
            self.nfc_disable()

    #def on_pause(self):
    #    self.disable_nfc_foreground_dispatch()
    #    return True
    #
    #def on_resume(self):
    #    self.enable_nfc_foreground_dispatch()
    # end NFC

    def give_current_tab_name(self, *args):
        self.current_tab_name = args[1].name
        print ("current_tab_name: {}".format(self.current_tab_name))
    # end NFC
    def show_snackbar(self, text):
        snackbar = Snackbar(text=text,
                            snackbar_x="8dp",
                            snackbar_y="8dp")
        snackbar.size_hint_x = (Window.width - (snackbar.snackbar_x * 2)) / Window.width
        snackbar.open()

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
        self.dialog = MDDialog(title=title,
                               content_cls=content if content else None,
                               text=message if not content else None,
                               size_hint=(.8, None),
                               height=dp(dialog_height),
                               auto_dismiss=False,
                               buttons=[
                                   MDFlatButton(
                                       text="Dismiss",
                                       on_release=partial(self.close_dialog))
                                   ]
                               )
        self.dialog.open()

    def close_dialog(self, *args):
        self.dialog.dismiss()

    def start_zbar(self):
        if platform != "android":
            snackbar_msg = "Scanning is not supported on {}.".format(platform)
            self.show_snackbar(snackbar_msg)
            return
        self.root.ids.sm.current = "zbar"
        self.root.ids.detector.start()

    def start_nfc_tap(self):
        #if platform != "android":
        #    self.show_snackbar("Tapping is not supported on {}.".format(platform))
        #    return

        #self.root.ids.sm.current = "zbar"
        #self.root.ids.detector.start()
        logging.info("start_nfc_tap")

    def qrcode_handler(self, symbols):
        try:
            address, amount = nowallet.get_payable_from_BIP21URI(symbols[0])
        except ValueError as ve:
            self.show_dialog("Error", str(ve))
            return
        self.root.ids.address_input.text = address
        self.update_amounts(text=str(amount))
        self.root.ids.detector.stop()
        self.root.ids.sm.current = "main"


    def nav_drawer_handler(self):
        if self._wallet_ready:
            self.root.ids.nav_drawer.set_state("open")
        elif self.root.ids.sm.current == "wait":
            self.show_snackbar('Loading wallet state...')
        else:
            self.show_snackbar('No active session.')

    def menu_button_handler(self, button):
        if self.root.ids.sm.current == "main":
            MDDropdownMenu(items=self.menu_items, width_mult=4, caller=button, \
            max_height=dp(250)).open()
        pass

    def navigation_handler(self, button):
        print ("navigation_handler. button={}".format(button))
        pass

    def menu_item_handler(self, text):
        # Main menu items
        if "PUB" in text:
            self.root.ids.sm.current = "ypub"
        if "BIP32" in text:
            self.root.ids.sm.current = "seed"
        elif "PIN" in text:
            self.root.ids.sm.current = "pin"
        elif "UTXO" in text:
            self.root.ids.sm.current = "utxo"
        elif "Settings" in text:
            self.open_settings()
        elif LOG_OFF_WALLET in text:
            self.logoff()
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

    def fee_button_handler(self):
        fee_input = self.root.ids.fee_input
        fee_button = self.root.ids.fee_button
        fee_input.disabled = not fee_input.disabled
        if not fee_input.disabled:
            fee_button.text = "Custom Fee"
        else:
            fee_button.text = "Normal Fee"
            fee_input.text = str(self.estimated_fee)
            self.current_fee = self.estimated_fee

    def fee_input_handler(self):
        text = self.root.ids.fee_input.text
        if text:
            self.current_fee = int(float(text))

    def set_address_error(self, addr):
        netcode = self.chain.netcode
        is_valid = addr.strip() and validate.is_address_valid(
            addr.strip(), ["address", "pay_to_script"], [netcode]) == netcode
        self.root.ids.address_input.error = not is_valid

    def set_amount_error(self, amount):
        #try:
        _amount = Decimal(amount) if amount else Decimal("0")
        #except:
        #    _amount = Decimal("0")
        is_valid = _amount / self.unit_factor <= self.wallet.balance
        self.root.ids.spend_amount_input.error = not is_valid

    async def do_spend(self, address, amount, fee_rate):
        self.spend_tuple = await self.wallet.spend(
            address, amount, fee_rate, rbf=self.rbf, broadcast=self.broadcast_tx)

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
        logging.info("Finished doing spend")

        txid, decimal_fee = self.spend_tuple[:2]

        message = "Added a miner fee of: {} {}".format(
            decimal_fee, self.chain.chain_1209k.upper())
        message += "\nTxID: {}...{}".format(txid[:13], txid[-13:])
        self.show_dialog("Transaction sent!", message)

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
        self._nfc_is_available = self.nfc_init() #TODO: maybe move to build()
        if self._nfc_is_available:
            self._nfc_is_on = True
        self._wallet_ready = True
        print("_wallet_ready=True")
        self.root.ids.sm.current = "main"
        # All methods below verify if self._wallet_ready is True.
        #self._unlock_nav_drawer()

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

        self.root.ids.sm.current = "wait"
        try:
            await self.do_login_tasks(email, passphrase)
        except (SocksConnectionError, ClientConnectorError):
            self.show_dialog("Error",
                             "Make sure Tor/Orbot is installed and running before using Brainbow.",
                             cb=lambda x: sys.exit(1))
            return
        self.update_screens()
        self.wallet_ready()
        await asyncio.gather(
            self.new_history_loop(),
            self.do_listen_task(),
            self.update_exchange_rates(),
            self.check_new_block(),
            )

    def login(self):
        task1 = asyncio.create_task(self.do_login())

    def logoff(self):
        self.show_dialog("Disconnected.","")
        MDApp.get_running_app().stop()


    async def do_listen_task(self):
        logging.info("Listening for new transactions.")
        task = asyncio.create_task(self.wallet.listen_to_addresses())

    async def do_login_tasks(self, email, passphrase):
        self.root.ids.wait_text.text = "Connecting.."
        self.root.ids.wait_text_small.text = "Getting a random server for you."
        server, port, proto = await nowallet.get_random_server(self.loop)
        self.root.ids.wait_text_small.text = "Connected to {}.".format(server)
        try:
            connection = nowallet.Connection(self.loop, server, port, proto)
        except Exception as ex:
            print("excepted")
            print(traceback.format_exc())
            logging.error("L442 {}".format(ex), exc_info=True)
            logging.info("{} {} {}".format(server, port, proto))
            await connection.do_connect()
            logging.info("{} {} {} -&gt; connected".format(server, port, proto))

        await connection.do_connect()

        self.root.ids.wait_text.text = "Deriving Keys.."
        self.root.ids.wait_text_small.text = "This will take a moment.."
        # make run in a seperate thread
        # in executor runs but gets stuck
        # wallet = await asyncio.gather(self.loop.run_in_executor(None, nowallet.Wallet, email, passphrase,
            # connection, self.loop, self.chain, self.bech32))
        self.wallet = nowallet.Wallet(email, passphrase, connection, self.loop, self.chain, self.bech32)
        self.set_wallet_fingetprint(self.wallet.fingerprint)
        self.root.ids.wait_text_small.text = "Wallet fingerprint is {}.".format(self.wallet.fingerprint)
        self.root.ids.wait_text.text = "Fetching history.."
        await self.wallet.discover_all_keys()

        self.root.ids.wait_text.text = "Fetching exchange rates.."
        # just await, but since the fetching url ruturns 403 make it anything
        try:
            self.exchange_rates = await fetch_exchange_rates(nowallet.BTC.chain_1209k)
        except:
            self.exchange_rates = False
            self.show_snackbar("Failed fetching exchange rates. Starting without...")

        self.root.ids.wait_text.text = "Getting fee estimate.."
        coinkb_fee = await self.wallet.get_fee_estimation()
        self.current_fee = self.estimated_fee = nowallet.Wallet.coinkb_to_satb(coinkb_fee)
        logging.info("Finished 'doing login tasks'")

        logging.info("all known addreses {}".format(self.wallet.get_all_known_addresses(addr=True)))

    def update_screens(self):
        self.update_balance_screen()
        self.update_send_screen()
        self.update_recieve_screen()
        self.update_ypub_screen()
        self.update_seed_screen()
        self.update_utxo_screen()

    async def new_history_loop(self):
        while True:
            await asyncio.sleep(1)
            self.check_new_history()

    #async def check_new_block(self):
    #    while True:
    #        await asyncio.sleep(10)
    #        logging.info("run chk block")

    #async def check_new_block(self):
    #    logging.info("Listening for new blocks.")
    #    await self.wallet.listen_to_blocks()

    async def check_new_block(self):
        while True:
            logging.info("run get_block_height")
            try:
                tip = get_block_height()
                if tip > self.block_height:
                    self.block_height = tip
                    logging.info("NEW self.block_height={}".format(self.block_height))
                    self.update_balance_screen()
                    self.show_snackbar("Block {} found!".format(self.block_height))
            except Exception as err:
                print(traceback.format_exc())
                logging.error(err)
                self.block_height = 0
            await asyncio.sleep(60)

    async def update_exchange_rates(self):
        while True:
            await asyncio.sleep(60)
            logging.info("run fetch_exchange_rates")
            if self.currency != "BTC" or \
                (self.currency == "BTC" and Decimal(self.get_rate()) != Decimal(1)):
                old_rates = self.exchange_rates
                try:
                    self.exchange_rates = await fetch_exchange_rates(nowallet.BTC.chain_1209k)
                except:
                    self.exchange_rates = old_rates or False
                    logging.info("Restoring exchange rates using old_rates.")
                self.update_balance_screen()
                if self.currency != "BTC":
                    self.show_snackbar("Exchange rates updated. {}".format(self.get_rate()))

    def toggle_balance_label(self):
        self.fiat_balance = not self.fiat_balance
        self.update_balance_screen()



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
        return "{} {}".format(balance.rstrip("0").rstrip("."), units)

    def set_wallet_fingetprint(self, fingerprint):
        print("set fingerprint to {}".format(fingerprint))
        self.root.ids.toolbar.title = fingerprint.upper()
        if self.chain  == nowallet.TBTC:
            self.root.ids.toolbar.title += " TESTNET"

    def update_balance_screen(self):
        self.root.ids.balance_label.text = self.balance_str(fiat=self.fiat_balance)
        self.root.ids.recycleView.data_model.data = []

        for hist in self.wallet.get_tx_history():
            logging.info("Adding history item to balance screen\n{}".format(hist))
            verb = "-" if hist.is_spend else "+"
            #if self.units.startswith("sats"):
            val = self.unit_precision.format(hist.value * self.unit_factor)
            val = val.rstrip("0").rstrip(".")
#
#            else:
#            val = hist.value * self.unit_factor
            hist_str = "{}{} {}".format(verb, val, self.units)
            self.add_list_item(hist_str, hist)

    def update_utxo_screen(self):
        self.root.ids.utxoRecycleView.data_model.data = []
        for utxo in self.wallet.utxos:
            value = Decimal(str(utxo.coin_value / nowallet.Wallet.COIN))
            utxo_str = (self.unit_precision + " {}").format(
                value * self.unit_factor, self.units)
            self.add_utxo_list_item(utxo_str, utxo)
        self.update_addresses_screen()

    def update_send_screen(self):
        self.root.ids.send_balance.text = \
            "Available balance:\n" + self.balance_str()
        self.root.ids.fee_input.text = str(self.current_fee)

    def update_recieve_screen(self):
        address = self.update_recieve_qrcode()
        encoding = "bech32" if self.wallet.bech32 else "P2SH"
        current_addr = "Current address ({}):\n{}".format(encoding, address)
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
        self.root.ids.ypub_label.text = "Extended Public Key (SegWit):\n" + ypub
        self.root.ids.ypub_qrcode.data = ypub

    def update_seed_screen(self):
        try:
            #self.root.ids.seed_label.text = "BIP39 Seed:\n"   +  self.wallet.bip39_seed
            #self.root.ids.seed_qrcode.data = self.wallet.bip39_seed
            self.root.ids.seed_label.text = \
                "BIP32 Root Key (WIF):\n" + \
                self.wallet.private_BIP32_root_key
            self.root.ids.seed_qrcode.data = self.wallet.private_BIP32_root_key
        except Exception as ex:
            print(traceback.format_exc())
            print(ex)
            self.root.ids.seed_label.text = ""
            self.root.ids.seed_qrcode.data = ""

    def update_addresses_screen(self):
        self.root.ids.addresses_recycle_view.data_model.data = []

        for address in self.wallet.get_all_known_addresses(addr=True, change=False):
            logging.info("Adding addr item to update_addresses_screen\n{}".format(address))
            self.root.ids.addresses_recycle_view.data_model.data.append({
                "text": address,
                "secondary_text": "Derivation: m{}'/{}'/{}'/{}/{}".format(
                    self.wallet.derivation.get('bip'),
                    self.wallet.derivation.get('bip44'),
                    self.wallet.derivation.get('account'),
                    0, #change
                    self.wallet.search_for_index(search=address, addr=True, change=False)),
            #    "tertiary_text": "Value: XXX XXX sats"
                })


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
            rate = self.exchange_rates[self.price_api][self.currency]
            return Decimal(str(rate))
        except:
            self.exchange_rates = False
            return Decimal(str(1))

    def copy_current_address_to_clipboard(self):
        if self.current_tab_name == "recieve":
            try:
                current_address = self.root.ids.addr_qrcode.data.replace("bitcoin:","").split("?")[0] # "bitcoin:{}?amount={}"
                Clipboard.copy(current_address)
                self.show_snackbar(text="Current address copied to clipboard.")
            except:
                self.show_snackbar(text="Can't copy to clipboard.")

    def update_amounts(self, text=None, type="coin"):
        if self.is_amount_inputs_locked:
            return
        #try:
        amount = Decimal(text) if text else Decimal("0")
        #except:
        #    amount = Decimal("0")
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
        self.theme_cls.material_style = "M2"
        """
<resources>
  <color name="primaryColor">#4d4d4d</color>
  <color name="primaryLightColor">#797979</color>
  <color name="primaryDarkColor">#252525</color>
  <color name="primaryTextColor">#ffffff</color>
</resources>

        """
        self.theme_cls.theme_style = "Light"

        self.icon = "brain.png"
        self.use_kivy_settings = False
        self.rbf = self.config.getboolean("nowallet", "rbf")
        self.units = self.config.get("nowallet", "units")
        self.update_unit()
        self.broadcast_tx = self.config.getboolean("nowallet", "broadcast_tx")
        if self.broadcast_tx:
            self.root.ids.send_button.text = 'Send TX'
        else:
            self.root.ids.send_button.text = 'Preview TX'

        self.currency = self.config.get("nowallet", "currency")
        self.explorer = self.config.get("nowallet", "explorer")
        self.set_price_api(self.config.get("nowallet", "price_api"))


    def build_config(self, config):
        config.setdefaults("nowallet", {
            "rbf": True,
            "broadcast_tx": True,
            "units": self.chain.chain_1209k.upper(),
            "currency": "BTC",
            "explorer": "blockcypher",
            "price_api": "CoinGecko",
            })
        Window.bind(on_keyboard=self.key_input)

    def build_settings(self, settings):
        coin = self.chain.chain_1209k.upper()
        #settings.add_json_panel("Settings", self.config, data=settings_json(coin))

    def on_config_change(self, config, section, key, value):
        if key == "rbf":
            self.rbf = value in [1, '1', True]
        elif key == "broadcast_tx":
            self.broadcast_tx = value in [1, '1', True]
            if self.broadcast_tx:
                self.root.ids.send_button.text = 'Send TX'
            else:
                self.root.ids.send_button.text = 'Preview TX'
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
        elif key == "price_api":
            self.set_price_api(value)
            self.update_amounts()

    def set_price_api(self, val):
        if val == "CoinGecko":
            self.price_api = "coingecko"
        elif val == "CryptoCompare":
            self.price_api = "ccomp"

    def key_input(self, window, key, scancode, codepoint, modifier):
        if key == 27:   # the back button / ESC
            return True  # override the default behaviour
        else:           # the key now does nothing
            return False

    def on_pause(self):
        self.disable_nfc_foreground_dispatch()
        print ("on_pause called")
        return True

    def on_resume(self):
        self.enable_nfc_foreground_dispatch()
        print ("on_resume called")
        return True

    def on_stop(self):
        self.disable_nfc_foreground_dispatch()
        print ("on_stop called")
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

        data.append({"text": text,
                    "secondary_text": history.tx_obj.id(),
                    "history": history,
                    "icon": icon})

    def add_utxo_list_item(self, text, utxo):
        data = self.root.ids.utxoRecycleView.data_model.data
        data.append({"text": text,
                     "secondary_text": utxo.as_dict()["tx_hash_hex"],
                     "utxo": utxo})


    #def _unlock_nav_drawer(self):
    #    if self._wallet_ready:
    #        print("wallet-ready-unlock-")
    #        self.root.ids.nav_drawer_item_gmail.text_color = "000000"
    #        self.root.ids.nav_drawer_item_gmail.selected_color: "#ff0000"

    def goto_screen(self, name, tab=None):
        if self._wallet_ready:
            self.root.ids.sm.current = name
            # TODO: allow to jump to random tab, instead of starting using the first
            #if tab and name == "main":
            #    self.root.ids.switch_tab("send")
            self.root.ids.nav_drawer.set_state("close")

def open_url(url):
    if platform == 'android':
        ''' Open a webpage in the default Android browser.  '''
        from jnius import autoclass, cast
        context = autoclass('org.kivy.android.PythonActivity').mActivity
        Uri = autoclass('android.net.Uri')
        Intent = autoclass('android.content.Intent')

        intent = Intent()
        intent.setAction(Intent.ACTION_VIEW)
        intent.setData(Uri.parse(url))
        currentActivity = cast('android.app.Activity', context)
        currentActivity.startActivity(intent)
    else:
        import webbrowser
        #webbrowser.open(url)
        webbrowser.open_new(url)


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    app = NowalletApp(loop)
    loop.run_until_complete(app.async_run())
    loop.close()
