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

    # FIXME: this could/should be converted to python so it can be registered as an entrypoint
    scripts=['scripts/GC_map_mod'],

    entry_points={'console_scripts': [
        'apply_wb_mask.py = hyp3lib.apply_wb_mask:main',
        'byteSigmaScale.py = hyp3lib.byteSigmaScale:main',
        'copy_metadata.py = hyp3lib.copy_metadata:main',
        'createAmp.py = hyp3lib.createAmp:main',
        'cutGeotiffsByLine.py = hyp3lib.cutGeotiffsByLine:main',
        'cutGeotiffs.py = hyp3lib.cutGeotiffs:main',
        'draw_polygon_on_raster.py = hyp3lib.draw_polygon_on_raster:main',
        'dem2isce.py = hyp3lib.dem2isce:main',
        'enh_lee_filter.py = hyp3lib.enh_lee_filter:main',
        'extendDateline.py = hyp3lib.extendDateline:main',
        'geotiff_lut.py = hyp3lib.geotiff_lut:main',
        'get_bounding.py = hyp3lib.get_bounding:main',
        'getDemFor.py = hyp3lib.getDemFor:main',
        'get_asf.py = hyp3lib.get_asf:main',
        'get_dem.py = hyp3lib.get_dem:main',
        'get_orb.py = hyp3lib.get_orb:main',
        'iscegeo2geotif.py = hyp3lib.iscegeo2geotif:main',
        'make_arc_thumb.py = hyp3lib.make_arc_thumb:main',
        'makeAsfBrowse.py = hyp3lib.makeAsfBrowse:main',
        'makeChangeBrowse.py = hyp3lib.makeChangeBrowse:main',
        'make_cogs.py = hyp3lib.make_cogs:main',
        'makeColorPhase.py = hyp3lib.makeColorPhase:main',
        'makeKml.py = hyp3lib.makeKml:main',
        'offset_xml.py = hyp3lib.offset_xml:main',
        'ps2dem.py = hyp3lib.ps2dem:main',
        'raster_boundary2shape.py = hyp3lib.raster_boundary2shape:main',
        'rasterMask.py = hyp3lib.rasterMask:main',
        'resample_geotiff.py = hyp3lib.resample_geotiff:main',
        'rtc2colordiff.py = hyp3lib.rtc2colordiff:main',
        'rtc2color.py = hyp3lib.rtc2color:main',
        'simplify_shapefile.py = hyp3lib.simplify_shapefile:main',
        'SLC_copy_S1_fullSW.py = hyp3lib.SLC_copy_S1_fullSW:main',
        'subset_geotiff_shape.py = hyp3lib.subset_geotiff_shape:main',
        'tileList2shape.py = hyp3lib.tileList2shape:main',
        'utm2dem.py = hyp3lib.utm2dem:main',
        'verify_opod.py = hyp3lib.verify_opod:main',
        ]
    },

    zip_safe=False,
)
