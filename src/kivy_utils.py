# Compatibility and utils

from kivy.utils import platform


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
        webbrowser.open_new(url)
