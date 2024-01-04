import pytest


@pytest.mark.script_launch_mode('subprocess')
def test_gc_map_mod_script(script_runner):
    """
    This is testing `scripts/GC_map_mod`, which is installed as a *script*
    and not registered as a entrypoint -- see setup.py
    """
    ret = script_runner.run('GC_map_mod')
    assert ret.success


def test_byteSigmaScale(script_runner):
    ret = script_runner.run('byteSigmaScale.py', '-h')
    assert ret.success


def test_cutGeotiffs(script_runner):
    ret = script_runner.run('cutGeotiffs.py', '-h')
    assert ret.success


def test_get_asf(script_runner):
    ret = script_runner.run('get_asf.py', '-h')
    assert ret.success


def test_get_orb(script_runner):
    ret = script_runner.run('get_orb.py', '-h')
    assert ret.success


def test_makeAsfBrowse(script_runner):
    ret = script_runner.run('makeAsfBrowse.py', '-h')
    assert ret.success


def test_resample_geotiff(script_runner):
    ret = script_runner.run('resample_geotiff.py', '-h')
    assert ret.success


def test_SLC_copy_S1_fullSW(script_runner):
    ret = script_runner.run('SLC_copy_S1_fullSW.py', '-h')
    assert ret.success


def test_utm2dem(script_runner):
    ret = script_runner.run('utm2dem.py', '-h')
    assert ret.success
