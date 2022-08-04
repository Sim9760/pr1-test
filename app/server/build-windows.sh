#!/bin/bash

cd "${0%/*}"
python -m venv env
source env/Scripts/activate
python setup.py install
pip install ../../host
pyinstaller --noconfirm main.spec
deactivate
cd -
