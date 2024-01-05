"""Tools for working with images"""

from PIL import Image
from typing import Tuple
from pathlib import Path


def create_thumbnail(input_image: Path, size: Tuple[int, int] = (100, 100), output_dir: Path = None) -> Path:
    """Create a thumbnail from an image

    Args:
        input_image: location of the input image
        size: size of the thumbnail to create
        output_dir: if provided create the thumbnail here, otherwise create it alongside the input image

    Returns:
        thumbnail: location of the created thumbnail
    """
    thumbnail_name = f'{input_image.stem}_thumb{input_image.suffix}'
    if output_dir is None:
        thumbnail = input_image.with_name(thumbnail_name)
    else:
        thumbnail = output_dir / thumbnail_name

    output_image = Image.open(input_image)
    output_image.thumbnail(size)
    output_image.save(thumbnail)
    return thumbnail
