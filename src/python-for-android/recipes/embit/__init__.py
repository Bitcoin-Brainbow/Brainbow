"""Build embit"""
from typing import List
from pythonforandroid.recipe import CppCompiledComponentsPythonRecipe


class EmbitRecipe(CppCompiledComponentsPythonRecipe):  # type: ignore # pylint: disable=R0903
    url = 'https://github.com/diybitcoinhardware/embit/archive/refs/heads/bip85.zip'
    name = "embit"
    depends: List[str] = ["setuptools"]
    call_hostpython_via_targetpython = False
    install_in_hostpython = True

recipe = EmbitRecipe()
