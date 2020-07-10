import os
import shutil
import requests

from hyp3lib.make_cogs import make_cog, cogify_dir


def test_make_cog(geotiff):
    make_cog(geotiff)

    with open(geotiff, 'rb') as f:
        response = requests.post('http://cog-validate.radiant.earth/api/validate', files={'file': f})

    assert response.status_code == 200


def test_cogify_dir(geotiff):
    copy_extensions = ['_1.tif', '_2.tif']
    for ext in copy_extensions:
        shutil.copy(geotiff, geotiff.replace('.tif', ext))

    cogify_dir(os.path.dirname(geotiff), file_pattern='*_?.tif')

    for ext in copy_extensions:
        with open(geotiff.replace('.tif', ext), 'rb') as f:
            response = requests.post('http://cog-validate.radiant.earth/api/validate', files={'file': f})
        assert response.status_code == 200

    with open(geotiff, 'rb') as f:
        response = requests.post('http://cog-validate.radiant.earth/api/validate', files={'file': f})
    assert response.status_code == 400
