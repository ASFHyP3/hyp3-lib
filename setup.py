from pathlib import Path

from setuptools import find_packages, setup

readme = Path(__file__).parent / 'README.md'

setup(
    name='hyp3lib',
    use_scm_version=True,
    description='Common library for HyP3 plugins',
    long_description=readme.read_text(),
    long_description_content_type='text/markdown',

    url='https://github.com/ASFHyP3/hyp3-lib',

    author='ASF APD/Tools Team',
    author_email='uaf-asf-apd@alaska.edu',

    license='BSD',
    include_package_data=True,

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Software Development :: Libraries',
    ],

    python_requires='>=3.7',

    install_requires=[
        'boto3',
        'gdal',
        'imageio',
        'importlib_metadata',
        'lxml',
        'matplotlib',
        'netCDF4',
        'numpy<1.24',
        'pillow',
        'pyproj>=2',
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
            'flake8',
            'flake8-import-order',
            'flake8-blind-except',
            'flake8-builtins',
            'pytest',
            'pytest-cov',
            'pytest-console-scripts',
            'responses',
        ]
    },

    packages=find_packages(),

    # FIXME: this could/should be converted to python so it can be registered as an entrypoint
    scripts=['scripts/GC_map_mod'],

    entry_points={'console_scripts': [
        'byteSigmaScale.py = hyp3lib.byteSigmaScale:main',
        'cutGeotiffs.py = hyp3lib.cutGeotiffs:main',
        'get_asf.py = hyp3lib.get_asf:main',
        'get_orb.py = hyp3lib.get_orb:main',
        'makeAsfBrowse.py = hyp3lib.makeAsfBrowse:main',
        'resample_geotiff.py = hyp3lib.resample_geotiff:main',
        'SLC_copy_S1_fullSW.py = hyp3lib.SLC_copy_S1_fullSW:main',
        'utm2dem.py = hyp3lib.utm2dem:main',
        ]
    },

    zip_safe=False,
)
