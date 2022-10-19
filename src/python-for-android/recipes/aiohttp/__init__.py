from pythonforandroid.recipe import PythonRecipe # CythonRecipe
#from pythonforandroid.recipe import CythonRecipe

#class AIOHTTPRecipe(PythonRecipe):
from pythonforandroid.recipe import IncludedFilesBehaviour, CppCompiledComponentsPythonRecipe
import os
import sys

class AIOHTTPRecipe( CppCompiledComponentsPythonRecipe):
    """
    See:
    """
    #version = "v3.8.3"
    #url = "https://github.com/aio-libs/aiohttp/archive/{version}.zip"
    url = "https://files.pythonhosted.org/packages/ff/4f/62d9859b7d4e6dc32feda67815c5f5ab4421e6909e48cbc970b6a40d60b7/aiohttp-3.8.3.tar.gz"
    name = "aiohttp"
    depends = ['setuptools']
    call_hostpython_via_targetpython = False
    install_in_hostpython = True

    def get_recipe_env(self, arch):
        env = super().get_recipe_env(arch)
        env['LDFLAGS'] += ' -lc++_shared'
        return env
        
recipe = AIOHTTPRecipe()
