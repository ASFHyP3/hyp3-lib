
from setuptools import setup, find_packages

from codecs import open
import os

here = os.path.abspath(os.path.dirname(__file__))

# Get the long description from the README file
long_description = 'Utility classes for making working with sential granule strings easier and more readable.'

with open("version.txt", "r+") as f:
    version = f.read()

setup(
    name='asf_granule_util',
    version=str(version),

    description='Library for handling sential granules',
    long_description=long_description,

    url='https://github.com/asfadmin/hyp3-time-series-lib',

    author='ASF Student Development Team 2017',
    author_email='eng.accts@asf.alaska.edu',

    license="License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",

    classifiers=['Development Status :: 3 - Alpha',

                 # Indicate who your project is intended for
                 'Intended Audience :: Science/Research',
                 'Topic :: Scientific/Engineering :: GIS',

                 # Specify the Python versions you support here. In particular, ensure
                 # that you indicate whether you support Python 2, Python 3 or both.
                 'Programming Language :: Python :: 2.7',
                 'Programming Language :: Python :: 3',
                 ],
    keywords='granule asf sential util',
    packages=find_packages()
)
