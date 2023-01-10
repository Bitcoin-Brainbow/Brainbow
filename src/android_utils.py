import traceback

def dark_mode():
    """ Check for dark mode in Android. """
    try:
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        Configuration = autoclass('android.content.res.Configuration')
        night_mode_flags = PythonActivity.mActivity.getResources().getConfiguration().uiMode & Configuration.UI_MODE_NIGHT_MASK
        if night_mode_flags == Configuration.UI_MODE_NIGHT_YES:
            return True
        elif night_mode_flags in [Configuration.UI_MODE_NIGHT_NO, Configuration.UI_MODE_NIGHT_UNDEFINED]:
            return False
    except Exception as ex:
        print(ex)
        print(traceback.format_exc())
