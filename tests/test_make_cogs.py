import os
import shutil
import requests

from hyp3lib.make_cogs import cogify_dir, cogify_file


def _is_cog(filename):
    with open(filename, 'rb') as f:
        response = requests.post('http://cog-validate.radiant.earth/api/validate', files={'file': f})
    return response.status_code == 200


def test_make_cog(geotiff):
    assert not _is_cog(geotiff)
    cogify_file(geotiff)
    assert _is_cog(geotiff)


def test_cogify_dir(geotiff):
    base_dir = os.path.dirname(geotiff)
    copy_names = [os.path.join(base_dir, '1.tif'), os.path.join(base_dir, '2.tif')]

    for name in copy_names:
        shutil.copy(geotiff, name)

    # Only cogify our copied files
    cogify_dir(base_dir, file_pattern='?.tif')

    for name in copy_names:
        assert _is_cog(name)

    assert not _is_cog(geotiff)
