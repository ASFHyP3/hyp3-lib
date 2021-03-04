import os

import responses

from hyp3lib import get_orb

_GRANULE = 'S1A_IW_SLC__1SSV_20150621T120220_20150621T120232_006471_008934_72D8'


@responses.activate
def test_download_sentinel_orbit_file_esa():
    remote_url = 'http://aux.sentinel1.eo.esa.int/POEORB/2015/07/11/' \
                 'S1A_OPER_AUX_POEORB_OPOD_20150711T121908_V20150620T225944_20150622T005944.EOF'
    responses.add_passthru(remote_url)

    response = {'results': [{'remote_url': remote_url}]}
    responses.add(responses.GET, 'https://qc.sentinel1.eo.esa.int/api/v1/', json=response)

    orbit_file, provider = get_orb.downloadSentinelOrbitFile(_GRANULE, providers=('ESA',))

    assert provider == 'ESA'
    assert os.path.exists(orbit_file)
    assert orbit_file == 'S1A_OPER_AUX_POEORB_OPOD_20150711T121908_V20150620T225944_20150622T005944.EOF'


@responses.activate
def test_get_orbit_url_esa_poeorb():
    remote_url = 'http://aux.sentinel1.eo.esa.int/POEORB/2015/07/11/' \
                 'S1A_OPER_AUX_POEORB_OPOD_20150711T121908_V20150620T225944_20150622T005944.EOF'
    response = {'results': [{'remote_url': remote_url}]}
    responses.add(responses.GET, 'https://qc.sentinel1.eo.esa.int/api/v1/', json=response)

    orbit_url = get_orb.get_orbit_url(_GRANULE, provider='ESA')

    assert 'http://aux.sentinel1.eo.esa.int/POEORB/2015/07/11/' \
           'S1A_OPER_AUX_POEORB_OPOD_20150711T121908_V20150620T225944_20150622T005944.EOF' \
           == orbit_url


@responses.activate
def test_get_orbit_url_esa_resorb():
    remote_url = 'http://aux.sentinel1.eo.esa.int/RESORB/2015/06/21/' \
                 'S1A_OPER_AUX_RESORB_OPOD_20150621T152320_V20150621T111644_20150621T143414.EOF'
    response = {'results': [{'remote_url': remote_url}]}
    responses.add(responses.GET, 'https://qc.sentinel1.eo.esa.int/api/v1/', json=response)

    orbit_url = get_orb.get_orbit_url(_GRANULE, orbit_type='aux_resorb', provider='ESA')

    assert 'http://aux.sentinel1.eo.esa.int/RESORB/2015/06/21/' \
           'S1A_OPER_AUX_RESORB_OPOD_20150621T152320_V20150621T111644_20150621T143414.EOF' \
           == orbit_url


def test_get_orbit_url_asf():
    orbit_url = get_orb.get_orbit_url(_GRANULE, provider='ASF')

    assert 'https://s1qc.asf.alaska.edu/aux_poeorb/' \
           'S1A_OPER_AUX_POEORB_OPOD_20150711T121908_V20150620T225944_20150622T005944.EOF' \
           == orbit_url
