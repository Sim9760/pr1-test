python -m venv env
./env/Scripts/activate
pip install nuitka
cd ../..
pip install ../server --target tmp/resources/beta/packages --upgrade
pip install ../../host --target tmp/resources/beta/packages --upgrade
pip install ../../units/builtin --target tmp/resources/beta/packages --upgrade
pip install ../../units/amf --target tmp/resources/beta/packages --upgrade
pip install ../../units/gpio --target tmp/resources/beta/packages --upgrade
pip install ../../units/numato --target tmp/resources/beta/packages --upgrade
pip install ../../units/opcua --target tmp/resources/beta/packages --upgrade
deactivate
