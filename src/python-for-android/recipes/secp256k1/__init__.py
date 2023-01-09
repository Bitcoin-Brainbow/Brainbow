import os
from pythonforandroid.recipe import CppCompiledComponentsPythonRecipe


class Secp256k1Recipe(CppCompiledComponentsPythonRecipe):

    version = '0.14.0'
    url = "https://pypi.python.org/packages/source/s/secp256k1/secp256k1-{}.tar.gz".format(version)

    call_hostpython_via_targetpython = False

    depends = [
        'openssl',
        'hostpython3',
        'python3',
        'setuptools',
        'libffi',
        'cffi',
        'libsecp256k1'
    ]


#    build-essential
#    automake
##    pkg-config
 ##   libtool
#    libffi-dev


#    patches = [
#        "cross_compile.patch", "drop_setup_requires.patch",
#        "pkg-config.patch", "find_lib.patch", "no-download.patch"]

#    def get_recipe_env(self, arch=None):
#        env = super().get_recipe_env(arch)
#        libsecp256k1 = self.get_recipe('libsecp256k1', self.ctx)
##        libsecp256k1_dir = libsecp256k1.get_build_dir(arch.arch)
 ##       env['CFLAGS'] += ' -I' + os.path.join(libsecp256k1_dir, 'include')
#  #      env['LDFLAGS'] += ' -L{} -lsecp256k1'.format(libsecp256k1_dir)
#        return env


recipe = Secp256k1Recipe()
