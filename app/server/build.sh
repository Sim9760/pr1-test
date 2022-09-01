#!/bin/bash

set -e
python3 -m venv env
source env/bin/activate
pip install ../../host
pip install ../../units/builtin
pip install ../../units/amf
pip install ../../units/gpio
pip install ../../units/numato
pip install ../../units/opcua
pip install .
pyinstaller --noconfirm main.spec
deactivate
