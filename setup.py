from __future__ import print_function, absolute_import, division, unicode_literals

import os

from setuptools import find_packages, setup

_HERE = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(_HERE, 'README.md'), 'r') as f:
    long_desc = f.read()

setup(
    name='hyp3lib',
    use_scm_version=True,
    description='Common library for HyP3 plugins',
    long_description=long_desc,
    long_description_content_type='text/markdown',

    url='https://github.com/ASFHyP3/hyp3-lib',

    author='ASF APD/Tools Team',
    author_email='uaf-asf-apd@alaska.edu',

    license='BSD-3-Clause',
    include_package_data=True,

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Software Development :: Libraries',
        ],

    python_requires='~=3.6',

    install_requires=[
        'boto3',
        'gdal',
        'imageio',
        'importlib_metadata',
        'lxml',
        'matplotlib',
        'netCDF4',
        'numpy',
        'pillow',
        'pyproj~=2.0',
        'pyshp',
        'requests',
        'scipy',
        'six',
        'statsmodels',
        'urllib3',
    ],

    extras_require={
        'develop': [
            'botocore',
            'pytest',
            'pytest-cov',
            'pytest-console-scripts',
            'responses',
        ]
    },

    packages=find_packages(),

    # FIXME: Only seems to be used in SLC_copy_S1_fullSW.py
    #        If needed, this could/should be converted to python so it can be
    #        registered as an entrypoint
    scripts=['scripts/GC_map_mod'],

    zip_safe=False,
)
