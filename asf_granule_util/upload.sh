#! /usr/bin/env bash

if [ "$1" = "test" ]
then
    mkdir dist-old
    mv dist/* dist-old/
    echo "Last version: "
    cat version.txt
    echo "Enter new version: "
    read version
    echo $version > version.txt

    echo python setup.py sdist
    python2 setup.py sdist
    echo python setup.py bdist_wheel --universal
    python2 setup.py bdist_wheel --universal

    twine upload --repository-url https://test.pypi.org/legacy/ dist/*
elif [ "$1" = "prod" ]
then
    read  -n 1 -p "Be sure to run a test upload before production upload (Enter)" mainmenuinput

    git add version.txt
    git commit -m "Uploaded version $version to PyPi"

    echo python setup.py sdist
    python2 setup.py sdist
    echo python setup.py bdist_wheel --universal
    python2 setup.py bdist_wheel --universal

    twine upload dist/*
else
    echo "test-upload.sh [test|prod]"
fi
