import pytest


@pytest.mark.script_launch_mode('subprocess')
def test_gc_map_mod_script(script_runner):
    """
    This is testing `scripts/GC_map_mod`, which is installed as a *script*
    and not registered as a entrypoint -- see setup.py
    """
    ret = script_runner.run(['GC_map_mod'])
    assert ret.success


def test_get_orb(script_runner):
    ret = script_runner.run(['get_orb.py', '-h'])
    assert ret.success


def test_resample_geotiff(script_runner):
    ret = script_runner.run(['resample_geotiff.py', '-h'])
    assert ret.success


def test_rtc2color(script_runner):
    ret = script_runner.run(['rtc2color.py', '-h'])
    assert ret.success
