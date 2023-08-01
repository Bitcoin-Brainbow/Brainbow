[app]
title = Brainbow Bitcoin Client
package.name = brainbow
package.domain = space.brainbow
source.dir = src
source.include_exts = py,png,jpg,kv,atlas,json,ttf,xml
source.exclude_exts = spec
source.exclude_dirs = tests, bin, venv, old-sources, multisig
version.regex = __version__ = ['"](.*)['"]
version.filename = %(source.dir)s/main.py

requirements =
  python3==3.9.9,
  cffi==1.15.1,
  pbkdf2,
  Cython==0.29.36,
  typing-extensions==4.4.0,
  aioconsole==0.1.10,
  aiosignal==1.2.0,
  appdirs==1.4.4,
  async-timeout==4.0.2,
  asyncgui==0.5.5,
  asynckivy==0.5.4,
  aiohttp==3.8.3,
  attrs==17.4.0,
  beautifulsoup4==4.6.0,
  certifi==2018.1.18,
  chardet==3.0.4,
  charset-normalizer==2.1.1,
  colorama==0.4.5,
  distlib==0.3.6,
  docutils==0.14,
  filelock==3.8.0,
  frozenlist==1.3.1,
  idna==2.6,
  importlib-metadata==4.12.0,
  Jinja2==3.1.2,
  Kivy==2.1.0,
  kivymd==1.0.2,
  kivy-garden.qrcode==2021.314,
  MarkupSafe==2.1.1,
  multidict==6.0.2,
  pep517==0.6.0,
  pexpect==4.8.0,
  Pillow==8.4.0,
  platformdirs==2.5.2,
  ptyprocess==0.7.0,
  pycoin==0.80,
  pycryptodome==3.9.8,
  Pygments==2.2.0,
  pytoml==0.1.21,
  qrcode==5.3,
  requests==2.20.0,
  six==1.11.0,
  toml==0.10.2,
  urllib3==1.24.3,
  yarl==1.8.1,
  zipp==3.8.1,
  android,
  pyjnius==1.4.2,
  embit==0.7.0,
  numpy==1.22.3,
  camera4kivy==0.1.0,
  gestures4kivy==0.1.0,
  pillow==8.4.0,
  libiconv,
  libzbar,
  pyzbar==0.1.7

presplash.filename = %(source.dir)s/brain_icon.png
icon.filename = %(source.dir)s/brain_icon.png

orientation = portrait

[buildozer]
log_level = 2
warn_on_root = 1

p4a.branch = develop
p4a.local_recipes = %(source.dir)s/python-for-android/recipes/
p4a.hook = ./src/camerax_provider/gradle_options.py

android.arch = arm64-v8a

android.api = 33
android.allow_backup = True
android.wakelock = True
android.accept_sdk_license = True
android.entrypoint = org.kivy.android.PythonActivity
