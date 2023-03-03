# Compatibility and utils
from kivy.utils import platform
from os.path import join as os_path_join

def get_storage_path(filename=""):
    try:
        from android.storage import primary_external_storage_path
        ext_path = primary_external_storage_path()
    except ModuleNotFoundError:
        from os.path import expanduser
        ext_path = expanduser("~")
    return os_path_join(ext_path, 'Downloads', filename)


def open_url(url):
    if platform == 'android':
        """ Open a webpage in the default Android browser. """
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
        webbrowser.open_new(url)
