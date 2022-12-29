#from kivy.lang import Builder
#screen = Builder.load_string(""" ... """)
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDLabel
from kivy.core.window import Window
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.bottomsheet import MDCustomBottomSheet
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.tab import MDTabsBase
from kivymd.uix.tab import MDTabs
from kivymd.uix.recycleview import MDRecycleView
from kivy.uix.recycleboxlayout import RecycleBoxLayout
import asyncio
from kivymd.app import MDApp

from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.list import TwoLineIconListItem
from kivymd.uix.list import TwoLineAvatarIconListItem
from kivymd.uix.list import IconLeftWidget
from kivymd.uix.list import IconRightWidget

from kivymd.uix.list import MDList


from utils import decodetx
from kivy_utils import open_url
import nowallet



class BroadcastButton(MDRaisedButton):
    def do_broadcast_current_signed_tx(self):
        task1 = asyncio.create_task(MDApp.get_running_app().do_broadcast())

    def __init__(self, **kwargs):
        self.on_release = self.do_broadcast_current_signed_tx
        return super(BroadcastButton, self).__init__(**kwargs)



class ExplorerViewButton(MDRaisedButton):
    """ """
    def do_view_txid_in_explorer(self):
        app = MDApp.get_running_app()
        base_url, chain = None, app.chain.chain_1209k
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
        elif app.explorer == "mempool.space":
            base_url = "https://mempool.space/{}tx/{}"
            if app.chain == nowallet.BTC:
                chain = ""
            elif app.chain == nowallet.TBTC:
                chain = "testnet/"
        url = base_url.format(chain, self.txid)
        open_url(url)

    def __init__(self, txid, **kwargs):
        self.txid = txid
        self.on_release = self.do_view_txid_in_explorer
        return super(ExplorerViewButton, self).__init__(**kwargs)





class DetailTab(MDFloatLayout, MDTabsBase):
    pass


class TxDetailInfo(MDGridLayout):
    def __init__(self, signed_tx, history=None, wallet=None, **var_args):
        super(TxDetailInfo, self).__init__(**var_args)
        in_out_sats_tx_value = 0.0
        if wallet:
            addrs = wallet.get_all_used_addresses()
            print("addrs, wallet all used addr: {}".format(addrs))
            for tx_out in signed_tx.txs_out:
                if tx_out.address(netcode="XTN") in addrs:
                    print("found my addr: {} value: {}".format(tx_out.address(netcode="XTN"), tx_out.coin_value))
                    in_out_sats_tx_value += tx_out.coin_value


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



        lbl2 = MDLabel(text = "{} sats or {} USD".format(in_out_sats_tx_value, "0.00" ))
        lbl2.text_color: "#000000"
        lbl2.halign = "center"
        #lbl2.font_name = "RobotoMono"
        lbl2.valign = "top"
        overview_box.add_widget(lbl2)

        #lbl3 = MDLabel(text = "{} {}".format("", "USD"))
        #lbl3.text_color: "#000000"
        #lbl3.halign = "center"
        #lbl3.font_name = "RobotoMono"
        #lbl3.valign = "top"
        #overview_box.add_widget(lbl3)


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

        if history and history.height > 0:

            lbl31 = MDLabel(text ='Block')
            lbl31.text_color: "#000000"
            lbl31.halign = "center"
            lbl31.font_size = '24sp'
            lbl31.theme_text_color = "Primary" #color: "#000000"
            lbl31.valign = "top"
            lbl31.bold = True
            overview_box.add_widget(lbl31)

            lbl32 = MDLabel(text = "{}".format(history.height))
            lbl32.text_color: "#000000"
            lbl32.halign = "center"
            lbl32.valign = "top"
            overview_box.add_widget(lbl32)


        btn_box = MDBoxLayout()
        #btn_box.orientation = "horiziontal"
        btn_box.size_hint_x = 1
        #btn_box.size_hint_y = 0.6
        btn_box.spacing = 5
        btn_box.padding = ["42dp", 0, "42dp", "42dp"]


        if not history:
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
        else:
            explorer_btn = ExplorerViewButton(txid)
            explorer_btn.text = "View on mempool.space"
            explorer_btn.size_hint_x = 1
            explorer_btn.font_size = '18sp'
            explorer_btn.md_bg_color = "#252525"

            btn_box.add_widget(explorer_btn)
            overview_box.add_widget(btn_box)

        overview_tab.add_widget(overview_box)
        tabs.add_widget(overview_tab)

        # Tab Inputs
        inputs_tab = DetailTab(title="Inputs/UTXOs")
        #inputs_tab.background_color = "#fafafa"
        inputs_box = MDBoxLayout()
        inputs_box.orientation = "vertical"
        #inputs_box.background_color = "#fea0f0" #"#fafafa"

        """
        lbl1 = MDLabel(text ='Amount/total_in')
        lbl1.text_color: "#000000"
        lbl1.halign = "center"
        lbl1.font_size = '24sp'
        lbl1.theme_text_color = "Primary"
        lbl1.valign = "top"
        lbl1.bold = True
        inputs_box.add_widget(lbl1)
        """

        scroll_input_list = MDList(id="scroll_view_list")
        scroll_input_view = MDScrollView(scroll_input_list)
        scroll_input_view.minimum_height = self.height
        for input in signed_tx.txs_in:
            scroll_input_list.add_widget(
                TwoLineIconListItem(
                    IconLeftWidget(
                        icon="arrow-right-circle-outline" # = UTXO was spent (empty)
                    ),
                    text="{}".format(input),
                    secondary_text="secondary_text",
                ))
        inputs_box.add_widget(scroll_input_view)
        """
        print(signed_tx.total_in)
        lbl2x = MDLabel(text = "Total Inputs: {}".format(len(signed_tx.txs_in)))
        lbl2x.text_color: "#000000"
        lbl2x.halign = "center"
        #lbl2.font_name = "RobotoMono"
        lbl2x.valign = "top"
        inputs_box.add_widget(lbl2x)
        """


        inputs_tab.add_widget(inputs_box)
        tabs.add_widget(inputs_tab)

        # Tab Outputs
        outputs_tab = DetailTab(title="Outputs")
        outputs_box = MDBoxLayout()
        outputs_box.orientation = "vertical"

        scroll_output_list = MDList(id="scroll_output_list")
        scroll_output_view = MDScrollView(scroll_output_list)
        scroll_output_view.minimum_height = self.height
        for tx_out in signed_tx.txs_out:
            print(dir(tx_out))
            scroll_output_list.add_widget(
                TwoLineAvatarIconListItem(
                    None,
                    IconRightWidget(
                        icon="arrow-right-circle-outline" # = UTXO was spent (empty)
                    ),
                    text=str(tx_out.address(netcode="XTN")),
                    secondary_text=str(tx_out.coin_value/100000000.),
                    ))
        outputs_box.add_widget(scroll_output_view)
        outputs_tab.add_widget(outputs_box)
        tabs.add_widget(outputs_tab)

        # Tab Fee
        fee_tab = DetailTab(title="Miner Fee")
        fee_box = MDBoxLayout()
        fee_box.orientation = "vertical"
        try:
            fee = signed_tx.fee()
        except Exception as ex:
            fee = str(ex)
            print (ex)
        fee_lbl = MDLabel(text = "{}".format(fee)) #"{}..{}".format(signed_tx.as_hex()[:12], signed_tx.as_hex()[-12:]))
        fee_lbl.text_color: "#000000"
        fee_lbl.halign = "center"
        fee_lbl.valign = "top"
        fee_box.add_widget(fee_lbl)

        fee_tab.add_widget(fee_box)
        tabs.add_widget(fee_tab)

        # Raw hex
        raw_tx_hex_tab = DetailTab(title="Raw Transaction")
        raw_tx_hex_box = MDBoxLayout()
        raw_tx_hex_box.orientation = "vertical"

        raw_tx_hex_lbl = MDLabel(text = "{}..{}".format(signed_tx.as_hex()[:12], signed_tx.as_hex()[-12:]))
        raw_tx_hex_lbl.text_color: "#000000"
        raw_tx_hex_lbl.halign = "center"
        raw_tx_hex_lbl.font_name = "RobotoMono"
        raw_tx_hex_lbl.valign = "top"
        raw_tx_hex_box.add_widget(raw_tx_hex_lbl)

        raw_tx_hex_tab.add_widget(raw_tx_hex_box)
        tabs.add_widget(raw_tx_hex_tab)


        self.add_widget(tabs)



def open_tx_preview_bottom_sheet(signed_tx, history=None, wallet=None):
    screen_box = MDBoxLayout()
    #screen_box.md_bg_color = "#fafafa"
    screen_box.orientation = "vertical"
    screen_box.size_hint_y = None
    screen_box.add_widget(TxDetailInfo(signed_tx, history, wallet))

    tx_btm_sheet = MDCustomBottomSheet(screen=screen_box)
    tx_btm_sheet.open()
    return tx_btm_sheet
