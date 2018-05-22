#! /usr/bin/env bash

read  -n 1 -p "Be sure to run a test upload before production upload (Enter)" mainmenuinput

git add version.txt
git commit -m "Uploaded version $version to PyPi"

echo python setup.py sdist
python2 setup.py sdist
echo python setup.py bdist_wheel --universal
python2 setup.py bdist_wheel --universal

twine upload dist/*


