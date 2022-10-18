from pythonforandroid.recipe import PythonRecipe # CythonRecipe


class AIOHTTPRecipe(PythonRecipe):
    version = "v3.8.3"
    url = "https://github.com/aio-libs/aiohttp/archive/{version}.zip"
    name = "aiohttp"
    depends = ['setuptools']
    
recipe = AIOHTTPRecipe()
