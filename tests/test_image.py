from PIL import Image

import hyp3lib.image


def test_create_thumbnail(png_image):
    with Image.open(png_image) as input_image:
        assert input_image.size == (162, 150)

    thumbnail = hyp3lib.image.create_thumbnail(png_image, (100, 100))
    assert thumbnail.name == 'test_thumb.png'

    with Image.open(png_image) as input_image:
        assert input_image.size == (162, 150)

    with Image.open(thumbnail) as output_image:
        assert output_image.size == (100, 93)

    thumbnail = hyp3lib.image.create_thumbnail(png_image, (255, 255))

    with Image.open(thumbnail) as output_image:
        assert output_image.size == (162, 150)
