import os

from setuptools import setup, find_packages


_HERE = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(_HERE, 'README.md'), 'r') as f:
    long_desc = f.read()

setup(
    name='hyp3lib',
    use_scm_version=True,
    description='HyP3 common library plugin',
    long_description=long_desc,
    long_description_content_type='text/markdown',

    url='https://github.com/asfadmin/hyp3-lib',

    author='ASF APD/Tools Team',
    author_email='uaf-asf-apd@alaska.edu',

    license='BSD',
    include_package_data=True,

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Software Development :: Libraries',
        ],

    install_requires=[
        'boto3',
        'botocore',  # FIXME: here because we import it directly... do we need too?
        'imageio',
        'importlib_metadata',
        'lxml',
        'matplotlib',
        'netCDF4',
        'numpy',
        'gdal',  # FIXME: Need to verify if GDAL v2 or v3 is being used
        'pillow',
        # FIXME: Need to verify if HyP3 uses pyproj v1 or v2 type syntax:
        #  http://pyproj4.github.io/pyproj/stable/examples.html
        'pyproj',
        'requests',
        'scipy',
        'six',
        'statsmodels',
    ],

    extras_require={
        'develop': [
            'pytest',
            'pytest-cov',
            'pytest-console-scripts',
            'tox',
        ]
    },

    packages=find_packages(),

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
        'par_s1_slc_single.py = hyp3lib.par_s1_slc_single:main',
        'ps2dem.py = hyp3lib.ps2dem:main',
        'raster_boundary2shape.py = hyp3lib.raster_boundary2shape:main',
        'rasterMask.py = hyp3lib.rasterMask:main',
        'resample_geotiff.py = hyp3lib.resample_geotiff:main',
        'rtc2colordiff.py = hyp3lib.rtc2colordiff:main',
        'rtc2color.py = hyp3lib.rtc2color:main',
        'SLC_copy_S1_fullSW.py = hyp3lib.SLC_copy_S1_fullSW:main',
        'subset_geotiff_shape.py = hyp3lib.subset_geotiff_shape:main',
        'tileList2shape.py = hyp3lib.tileList2shape:main',
        'utm2dem.py = hyp3lib.utm2dem:main',
        'verify_opod.py = hyp3lib.verify_opod:main',
        ]
    },

    zip_safe=False,
)
