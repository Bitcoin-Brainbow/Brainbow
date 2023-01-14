import traceback

try:
    from android.runnable import run_on_ui_thread
    from jnius import autoclass
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Params = autoclass('android.view.WindowManagerLayoutParams')
except:
    def run_on_ui_thread(*args, **kwargs):
        pass

def dark_mode():
    return True
# def dark_mode():
#     """ Check for dark mode in Android. """
#     try:
#         from jnius import autoclass
#         PythonActivity = autoclass('org.kivy.android.PythonActivity')
#         Configuration = autoclass('android.content.res.Configuration')
#         night_mode_flags = PythonActivity.mActivity.getResources().getConfiguration().uiMode & Configuration.UI_MODE_NIGHT_MASK
#         if night_mode_flags == Configuration.UI_MODE_NIGHT_YES:
#             return True
#         elif night_mode_flags in [Configuration.UI_MODE_NIGHT_NO, Configuration.UI_MODE_NIGHT_UNDEFINED]:
#             return False
#     except Exception as ex:
#         print(ex)
#         print(traceback.format_exc())


def android_setflag():
    try:
        PythonActivity.mActivity.getWindow().addFlags(Params.FLAG_KEEP_SCREEN_ON)
    except:
        pass



def android_clearflag():
    try:
        PythonActivity.mActivity.getWindow().clearFlags(Params.FLAG_KEEP_SCREEN_ON)
    except:
        pass



try:
    run_on_ui_thread(android_setflag)
    run_on_ui_thread(android_clearflag)
except:
    pass
