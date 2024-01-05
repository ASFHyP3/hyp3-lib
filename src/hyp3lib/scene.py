"""Tools for working with Sentinel-1 scenes"""

SENTINEL_DISTRIBUTION_URL = 'https://sentinel1.asf.alaska.edu'


def get_download_url(scene):
    mission = scene[0] + scene[2]
    product_type = scene[7:10]
    if product_type == 'GRD':
        product_type += '_' + scene[10] + scene[14]
    url = f'{SENTINEL_DISTRIBUTION_URL}/{product_type}/{mission}/{scene}.zip'
    return url
