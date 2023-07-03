# How to run the sources on your own machine 

## Create a Python3 virtual environment

```shell
python -m venv ~/brainbowenv/
```

## Activate the Python3 virtual environment 

```shell
source ~/brainbowenv/bin/activate
```

Note: you can deactivate the python environment at any time with the command `deactivate`
read more about it [here](https://docs.python.org/3/library/venv.html)

## Clone brainbow repository and install requirements

```shell
git clone https://github.com/Bitcoin-Brainbow/Brainbow.git brainbow
cd brainbow/
```

Add the following to the new_requirements.txt

kivy-garden
kivy
kivy_garden.graph
kivy_garden.qrcode
embit
numpy
camera4kivy
pyzbar

```shell
pip install -r new_requirements.txt
```

Note: for MacOS I had to install zbar with brew

```shell
brew install zbar
```

## Start the app

```shell
python main.py
```

## NOTES:
- Tor must be installed and running.
