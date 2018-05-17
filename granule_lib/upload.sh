#! /usr/bin/env bash

mkdir dist-old
mv dist/* dist-old/
echo "Last version: "
cat version.txt
echo "Enter new version: "
read version
echo $version > version.txt
git add version.txt
git commit -m "Uploaded version $version to PyPi"

echo python setup.py sdist
python2 setup.py sdist
echo python setup.py bdist_wheel --universal
python2 setup.py bdist_wheel --universal

twine upload dist/*


