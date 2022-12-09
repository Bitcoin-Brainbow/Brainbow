#from kivy.lang import Builder
#screen = Builder.load_string(""" ... """)
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDLabel
from kivy.core.window import Window
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.bottomsheet import MDCustomBottomSheet
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.tab import MDTabsBase, MDTabs
import asyncio
from kivymd.app import MDApp

from utils import decodetx

"""
{'block_height': -1,
'block_index': -1,
'hash': '4e8d53d1dc65ac294281662cecf77c22534923a6b52c0c70dc8f6ec3f419be84',
'addresses': ['2Mx48Vzupaog8EBx8JEBorQMddYSnornBdN', '2NACN885dF5NhH23CoXmU1FUdhJoS4ifxZB', '2N75SLnN7D4D1GocUH6VQiw55kFTr99Ew2k', '2MtbzwpmdHNgUwn79EZKLuvfNhuKChX7Vsh', '2N6j1gY6ikkBspmhxMZyskiHTsx6aE5wx9F', '2MvQGQuxaaVdtMYgYsREYsJ7DKgL4xgrFeS', '2N6VnHJmBHAe4qx1uoSzi6zwL7rihgyDb4w'],
'total': 5220175,
'fees': 455,
'size': 932,
'vsize': 529,
'preference': 'low',
'relayed_by': '194.230.160.94',
'received': '2022-11-27T22:07:36.975044567Z',
'ver': 1,
'double_spend': False,
'vin_sz': 5, 'vout_sz': 2,
'opt_in_rbf': True,
'confirmations': 0,

'inputs': [{'prev_hash': '4b7bec3c96c0fcb5e9757c8254c8f686fb6054b79e37f975a50bcf9524f24623', 'output_index': 0, 'script': '160014c41defa6125d90d74af306aed7670f3fe4dc9f05', 'output_value': 111483, 'sequence': 0, 'addresses': ['2N6VnHJmBHAe4qx1uoSzi6zwL7rihgyDb4w'], 'script_type': 'pay-to-script-hash', 'age': 2405104}, {'prev_hash': '6f4f9442b7d5dbaa3fbf23927f4d918e4b80d7ac6fc263db64ff52cfba220f13', 'output_index': 0, 'script': '160014ed3b259de7ccb5f4db5bd30b8eeafc9b844f5b96', 'output_value': 1102147, 'sequence': 0, 'addresses': ['2Mx48Vzupaog8EBx8JEBorQMddYSnornBdN'], 'script_type': 'pay-to-script-hash', 'age': 2406140}, {'prev_hash': '7aacf80085bbdd64a6e371664f39588eee9c709697a21ab85e1036858e74be09', 'output_index': 0, 'script': '160014814d657da8fe1ab1435a291cc1a189af483932c5', 'output_value': 1009000, 'sequence': 0, 'addresses': ['2NACN885dF5NhH23CoXmU1FUdhJoS4ifxZB'], 'script_type': 'pay-to-script-hash', 'age': 2407952}, {'prev_hash': '9cbb4bbdf028e4785970166efe5aaaea08e18d2551783e7842e958c2d38fa25e', 'output_index': 1, 'script': '160014a0ee1a55f6e30d7c9a8944baa60bc9896298628d', 'output_value': 1000000, 'sequence': 0, 'addresses': ['2N75SLnN7D4D1GocUH6VQiw55kFTr99Ew2k'], 'script_type': 'pay-to-script-hash', 'age': 2405563}, {'prev_hash': 'a135324d1e13f8dbf99979056cd8818351aada1f745036ee802ba905df40dc3f', 'output_index': 0,
'script': '160014dea54b746a2e28eec53fe651d2d1eea95c5da2c7',
'output_value': 1998000,
'sequence': 0,

'addresses': ['2MtbzwpmdHNgUwn79EZKLuvfNhuKChX7Vsh'],

'script_type': 'pay-to-script-hash',
'age': 2408431}],

'outputs': [
{'value': 120175, 'script': 'a91493db02755454c82062b6574eb36eb73f2ca29dbe87', 'addresses': ['2N6j1gY6ikkBspmhxMZyskiHTsx6aE5wx9F'], 'script_type': 'pay-to-script-hash'},
{'value': 5 100 000, 'script': 'a914229e251f299309504aa3aad2add8c7340c6ce20687', 'addresses': ['2MvQGQuxaaVdtMYgYsREYsJ7DKgL4xgrFeS'], 'script_type': 'pay-to-script-hash'}]}
"""
class BroadcastButton(MDRaisedButton):
    def do_broadcast_current_signed_tx(self):
        task1 = asyncio.create_task(MDApp.get_running_app().do_broadcast())

    def __init__(self, **kwargs):
        self.on_release = self.do_broadcast_current_signed_tx
        return super(BroadcastButton, self).__init__(**kwargs)



class DetailTab(MDFloatLayout, MDTabsBase):
    pass


class TxDetailInfo(MDGridLayout):
    def __init__(self, signed_tx, **var_args):
        super(TxDetailInfo, self).__init__(**var_args)
        self.cols = 1
        self.col_default_width = Window.width
        self.col_width = Window.width

        self.height = "520dp"
        self.width = Window.width
        self.size_hint_y = None
        self.minimum_height = self.height
        self.md_bg_color = "#fafafa"

        tabs = MDTabs()
        tabs.background_color = "#fafafa"
        tabs.text_color_normal = "#000000"
        tabs.text_color_active = "#000000"


        overview_tab = DetailTab(title="OVERVIEW")
        overview_tab.background_color = "#fafafa"


        txid = signed_tx.id()
        txid_short = "{}..{}".format(txid[:13], txid[-13:])
        decoded_tx = decodetx(signed_tx.as_hex())
        print(decoded_tx)
        overview_box = MDBoxLayout()

        overview_box.orientation = "vertical"
        overview_box.background_color = "#fea0f0" #"#fafafa"

        lbl1 = MDLabel(text ='Amount')
        lbl1.text_color: "#000000"
        lbl1.halign = "center"
        lbl1.font_size = '24sp'
        lbl1.theme_text_color = "Primary" #color: "#000000"
        lbl1.valign = "top"
        lbl1.bold = True
        overview_box.add_widget(lbl1)

        #'fees': 455


        lbl2 = MDLabel(text = "{} sats".format(decoded_tx.get('total')))
        lbl2.text_color: "#000000"
        lbl2.halign = "center"
        lbl2.font_name = "RobotoMono"
        lbl2.valign = "top"
        overview_box.add_widget(lbl2)

        lbl3 = MDLabel(text = "{} {}".format(0, 0))
        lbl3.text_color: "#000000"
        lbl3.halign = "center"
        lbl3.font_name = "RobotoMono"
        lbl3.valign = "top"
        overview_box.add_widget(lbl3)



###




        lbl12 = MDLabel(text ='Transaction ID')
        lbl12.text_color: "#000000"
        lbl12.halign = "center"
        lbl12.font_size = '24sp'
        lbl12.theme_text_color = "Primary" #color: "#000000"
        lbl12.valign = "top"
        lbl12.bold = True
        overview_box.add_widget(lbl12)

        lbl22 = MDLabel(text = txid_short)
        lbl22.text_color: "#000000"
        lbl22.halign = "center"
        lbl22.font_name = "RobotoMono"
        lbl22.valign = "top"
        overview_box.add_widget(lbl22)


        btn_box = MDBoxLayout()
        #btn_box.orientation = "horiziontal"
        btn_box.size_hint_x = 1
        #btn_box.size_hint_y = 0.6
        btn_box.spacing = 5
        btn_box.padding = ["42dp", 0, "42dp", "42dp"]



        broadcast_btn = BroadcastButton()
        broadcast_btn.text = "Broadcast"
        #broadcast_btn.size_hint_x = None
        broadcast_btn.size_hint_x = 0.5
        broadcast_btn.font_size = '18sp'
        broadcast_btn.md_bg_color = "#252525"



        broadcast_btn_dl = MDRaisedButton(text="Download")
        #broadcast_btn_dl.size_hint_x = None
        broadcast_btn_dl.size_hint_x = 0.5
        broadcast_btn_dl.font_size = '18sp'
        broadcast_btn_dl.md_bg_color = "#252525"

        """

            id: login_button

            on_release: app.login()

            spacer = MDBoxLayout()
        spacer.add_widget(lbl2)
        spacer.padding = ["42dp", 0, "42dp", 0]
        self.add_widget(spacer)

        """
        btn_box.add_widget(broadcast_btn_dl)
        btn_box.add_widget(broadcast_btn)
        overview_box.add_widget(btn_box)
        overview_tab.add_widget(overview_box)
        tabs.add_widget(overview_tab)
        tabs.add_widget(DetailTab(title="Inputs/UTXOs"))
        tabs.add_widget(DetailTab(title="Outputs"))
        tabs.add_widget(DetailTab(title="Miner Fee"))
        self.add_widget(tabs)



def open_tx_preview_bottom_sheet(signed_tx):
    screen_box = MDBoxLayout()
    #screen_box.md_bg_color = "#fafafa"
    screen_box.orientation = "vertical"
    screen_box.size_hint_y = None
    screen_box.add_widget(TxDetailInfo(signed_tx))

    tx_btm_sheet = MDCustomBottomSheet(screen=screen_box)
    tx_btm_sheet.open()
    return tx_btm_sheet
