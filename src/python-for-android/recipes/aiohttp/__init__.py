from pythonforandroid.recipe import PythonRecipe # CythonRecipe


#class AIOHTTPRecipe(PythonRecipe):
from pythonforandroid.recipe import IncludedFilesBehaviour, CppCompiledComponentsPythonRecipe
import os
import sys

class AIOHTTPRecipe(IncludedFilesBehaviour, CppCompiledComponentsPythonRecipe):

    version = "v3.8.3"
    url = "https://github.com/aio-libs/aiohttp/archive/{version}.zip"
    name = "aiohttp"
    depends = ['setuptools']
    call_hostpython_via_targetpython = False
    install_in_hostpython = True

recipe = AIOHTTPRecipe()
