from osgeo import gdal

from hyp3lib import util


def test_gdal_config_manager():
    gdal.SetConfigOption('OPTION1', 'VALUE1')
    gdal.SetConfigOption('OPTION2', 'VALUE2')

    assert gdal.GetConfigOption('OPTION1') == 'VALUE1'
    assert gdal.GetConfigOption('OPTION2') == 'VALUE2'
    assert gdal.GetConfigOption('OPTION3') is None
    assert gdal.GetConfigOption('OPTION4') is None

    with util.GDALConfigManager(OPTION2='CHANGED', OPTION3='VALUE3'):
        assert gdal.GetConfigOption('OPTION1') == 'VALUE1'
        assert gdal.GetConfigOption('OPTION2') == 'CHANGED'
        assert gdal.GetConfigOption('OPTION3') == 'VALUE3'
        assert gdal.GetConfigOption('OPTION4') is None

        gdal.SetConfigOption('OPTION4', 'VALUE4')

    assert gdal.GetConfigOption('OPTION1') == 'VALUE1'
    assert gdal.GetConfigOption('OPTION2') == 'VALUE2'
    assert gdal.GetConfigOption('OPTION3') is None
    assert gdal.GetConfigOption('OPTION4') == 'VALUE4'


def test_string_is_true():
    assert util.string_is_true('true')
    assert util.string_is_true('True')
    assert util.string_is_true('TRUE')
    assert not util.string_is_true('')
    assert not util.string_is_true(' ')
    assert not util.string_is_true('true1')
    assert not util.string_is_true('false')
