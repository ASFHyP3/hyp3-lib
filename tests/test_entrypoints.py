from __future__ import print_function, absolute_import, division, unicode_literals

import pytest


@pytest.mark.script_launch_mode('subprocess')
def test_gc_map_mod_script(script_runner):
    """
    This is testing `scripts/GC_map_mod`, which is installed as a *script*
    and not registered as a entrypoint -- see setup.py
    """
    ret = script_runner.run('GC_map_mod')
    assert ret.success


def test_apply_wb_mask(script_runner):
    ret = script_runner.run('apply_wb_mask.py', '-h')
    assert ret.success


def test_byteSigmaScale(script_runner):
    ret = script_runner.run('byteSigmaScale.py', '-h')
    assert ret.success


def test_copy_metadata(script_runner):
    ret = script_runner.run('copy_metadata.py', '-h')
    assert ret.success


def test_createAmp(script_runner):
    ret = script_runner.run('createAmp.py', '-h')
    assert ret.success


def test_cutGeotiffsByLine(script_runner):
    ret = script_runner.run('cutGeotiffsByLine.py', '-h')
    assert ret.success


def test_cutGeotiffs(script_runner):
    ret = script_runner.run('cutGeotiffs.py', '-h')
    assert ret.success


def test_draw_polygon_on_raster(script_runner):
    ret = script_runner.run('draw_polygon_on_raster.py', '-h')
    assert ret.success


def test_dem2isce(script_runner):
    ret = script_runner.run('dem2isce.py', '-h')
    assert ret.success


def test_enh_lee_filter(script_runner):
    ret = script_runner.run('enh_lee_filter.py', '-h')
    assert ret.success


def test_extendDateline(script_runner):
    ret = script_runner.run('extendDateline.py', '-h')
    assert ret.success


def test_geotiff_lut(script_runner):
    ret = script_runner.run('geotiff_lut.py', '-h')
    assert ret.success


def test_get_bounding(script_runner):
    ret = script_runner.run('get_bounding.py', '-h')
    assert ret.success


def test_getDemFor(script_runner):
    ret = script_runner.run('getDemFor.py', '-h')
    assert ret.success


def test_get_asf(script_runner):
    ret = script_runner.run('get_asf.py', '-h')
    assert ret.success


def test_get_dem(script_runner):
    ret = script_runner.run('get_dem.py', '-h')
    assert ret.success


def test_get_orb(script_runner):
    ret = script_runner.run('get_orb.py', '-h')
    assert ret.success


def test_iscegeo2geotif(script_runner):
    ret = script_runner.run('iscegeo2geotif.py', '-h')
    assert ret.success


def test_make_arc_thumb(script_runner):
    ret = script_runner.run('make_arc_thumb.py', '-h')
    assert ret.success


def test_makeAsfBrowse(script_runner):
    ret = script_runner.run('makeAsfBrowse.py', '-h')
    assert ret.success


def test_makeChangeBrowse(script_runner):
    ret = script_runner.run('makeChangeBrowse.py', '-h')
    assert ret.success


def test_make_cogs(script_runner):
    ret = script_runner.run('make_cogs.py', '-h')
    assert ret.success


def test_makeColorPhase(script_runner):
    ret = script_runner.run('makeColorPhase.py', '-h')
    assert ret.success


def test_makeKml(script_runner):
    ret = script_runner.run('makeKml.py', '-h')
    assert ret.success


def test_offset_xml(script_runner):
    ret = script_runner.run('offset_xml.py', '-h')
    assert ret.success


def test_ps2dem(script_runner):
    ret = script_runner.run('ps2dem.py', '-h')
    assert ret.success


def test_raster_boundary2shape(script_runner):
    ret = script_runner.run('raster_boundary2shape.py', '-h')
    assert ret.success


def test_rasterMask(script_runner):
    ret = script_runner.run('rasterMask.py', '-h')
    assert ret.success


def test_resample_geotiff(script_runner):
    ret = script_runner.run('resample_geotiff.py', '-h')
    assert ret.success


def test_rtc2colordiff(script_runner):
    ret = script_runner.run('rtc2colordiff.py', '-h')
    assert ret.success


def test_rtc2color(script_runner):
    ret = script_runner.run('rtc2color.py', '-h')
    assert ret.success


def test_simplify_shapefile(script_runner):
    ret = script_runner.run('simplify_shapefile.py', '-h')
    assert ret.success


def test_SLC_copy_S1_fullSW(script_runner):
    ret = script_runner.run('SLC_copy_S1_fullSW.py', '-h')
    assert ret.success


def test_subset_geotiff_shape(script_runner):
    ret = script_runner.run('subset_geotiff_shape.py', '-h')
    assert ret.success


def test_tileList2shape(script_runner):
    ret = script_runner.run('tileList2shape.py', '-h')
    assert ret.success


def test_utm2dem(script_runner):
    ret = script_runner.run('utm2dem.py', '-h')
    assert ret.success


def test_verify_opod(script_runner):
    ret = script_runner.run('verify_opod.py', '-h')
    assert ret.success


