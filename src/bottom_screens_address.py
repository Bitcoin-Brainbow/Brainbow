#from kivy.lang import Builder
#screen = Builder.load_string(""" ... """)
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDLabel
from kivy.core.window import Window
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.bottomsheet import MDCustomBottomSheet
from kivy_garden.qrcode import QRCodeWidget

class AddressDetailInfo(MDGridLayout):
    def __init__(self, address, **var_args):
        super(AddressDetailInfo, self).__init__(**var_args)
        self.cols = 1
        self.col_default_width = Window.width
        self.col_width = Window.width
        self.background_color = "#fafafa"

        #self.md_bg_color: '#00ffff'
        self.height = "400dp"
        self.width = Window.width
        self.size_hint_y = None
        #self.size_hint_x = None
        self.minimum_height = self.height
        self.padding = [ 0, "21dp", 0, 0]

        lbl1 = MDLabel(text ='Address')
        lbl1.size_hint_y = None
        lbl1.size_hint_x = Window.width
        lbl1.color: "#000000"
        lbl1.halign = "center"
        lbl1.font_size = '24sp'
        lbl1.theme_text_color = "Primary" #color: "#000000"
        lbl1.valign = "top"
        lbl1.bold = True
        self.add_widget(lbl1)

        chunk_size = 5
        chunked_address = [address[i:i+chunk_size] for i in range(0, len(address), chunk_size)]
        lbl2 = MDLabel(text = " ".join(chunked_address))
        lbl2.size_hint_y = 1.65
        lbl2.size_hint_x = Window.width
        lbl2.color: "#000000"
        lbl2.halign = "center"
        lbl2.font_name = "RobotoMono"
        lbl2.valign = "top"

        spacer = MDBoxLayout()
        spacer.add_widget(lbl2)
        spacer.padding = ["42dp", 0, "42dp", 0]

        self.add_widget(spacer)

        qrcode_widget = QRCodeWidget()
        qrcode_widget.id = "addr_qrcode_list_btm_screen"
        qrcode_widget.show_border = False
        qrcode_widget.background_color = (0.98, 0.98, 0.98, 1)  # = #fafafa
        qrcode_widget.data = "bitcoin:{}".format(address)

        spacer_btm = MDBoxLayout()
        spacer_btm.add_widget(qrcode_widget)
        spacer_btm.padding = [0, 0, 0, "42dp"]
        self.add_widget(spacer_btm)




def open_address_bottom_sheet(address, qr=False):
    addr_btm_sheet = MDCustomBottomSheet(screen=AddressDetailInfo(address))
    addr_btm_sheet.open()
    print(dir(addr_btm_sheet))
