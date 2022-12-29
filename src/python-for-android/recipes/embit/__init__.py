from pythonforandroid.recipe import PythonRecipe


class EmbitRecipe(PythonRecipe):
    url = 'https://github.com/diybitcoinhardware/embit/archive/refs/heads/bip85.zip'
    depends = ['setuptools']
    site_packages_name = "embit"
    call_hostpython_via_targetpython = False
    install_in_hostpython = True
    
recipe = EmbitRecipe()
