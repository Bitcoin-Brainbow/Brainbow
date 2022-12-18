
def update_loading_small_text(text):
    from kivymd.app import MDApp

    app = MDApp.get_running_app()
    app.root.ids.wait_text_small.text = text


def update_waiting_texts(text="", small_text=""):
    from kivymd.app import MDApp

    app = MDApp.get_running_app()
    app.root.ids.wait_text.text = text.upper()
    app.root.ids.wait_text_small.text = small_text
