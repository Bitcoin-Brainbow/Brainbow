from os.path import join
from pythonforandroid.recipe import PythonRecipe


class Pbkdf2Recipe(PythonRecipe):

    url = 'https://github.com/dlitz/python-pbkdf2/archive/refs/tags/v1.3.zip'
    #url = 'https://github.com/dlitz/python-pbkdf2/archive/master.zip'

    depends = ['setuptools']

recipe = Pbkdf2Recipe()
