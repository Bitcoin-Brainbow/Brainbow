from os.path import join
from pythonforandroid.recipe import PythonRecipe


class EmbitRecipe(PythonRecipe):

    url = 'https://github.com/diybitcoinhardware/embit/archive/refs/heads/bip85.zip'

    depends = ['setuptools']

recipe = EmbitRecipe()

 
