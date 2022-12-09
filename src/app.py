
def update_loading_small_text(text):
    from kivymd.app import MDApp

    app = MDApp.get_running_app()
    app.root.ids.wait_text_small.text = text
