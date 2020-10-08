from hyp3lib import scene


def test_get_download_url():
    granule = 'S1A_IW_GRDH_1SDV_20200611T090849_20200611T090914_032967_03D196_D46C'
    url = scene.get_download_url(granule)
    assert url == f'https://dy4owt9f80bz7.cloudfront.net/GRD_HD/SA/{granule}.zip'

    granule = 'S1B_IW_SLC__1SDV_20200611T071252_20200611T071322_021982_029B8F_B023'
    url = scene.get_download_url(granule)
    assert url == f'https://dy4owt9f80bz7.cloudfront.net/SLC/SB/{granule}.zip'
