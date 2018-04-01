import re
import os


def get_granule_bounding(granule_path):
    annotation_xml_paths = get_annotation_xmls_paths(granule_path)

    annotation_xmls = read_files(annotation_xml_paths)

    bounds = [
        get_values_from(xml_contents) for xml_contents in annotation_xmls
    ]

    return get_granule_extrema(bounds)


def get_annotation_xmls_paths(granule_path):
    annotation_dir = os.path.join(granule_path, 'annotation')

    annotation_file_names = os.listdir(annotation_dir)

    return [
        os.path.join(annotation_dir, a) for a in annotation_file_names
    ]


def read_files(paths):
    file_contents = []
    for path in paths:
        with open(path, 'r') as f:
            contents = f.read()

        file_contents.append(contents)

    return file_contents


def get_bounding(annotation_xml):
    lats, lons = get_values_from(annotation_xml)

    return get_extrema(lats, lons)


def get_extrema(lats, lons):
    return {
        "lat": get_extrema_from(lats),
        "lon": get_extrema_from(lons)
    }


def get_values_from(annotation_xml):
    lats = numbers_between('latitude', annotation_xml)
    lons = numbers_between('longitude', annotation_xml)

    return (
        lats,
        lons
    )


def numbers_between(tag, annotation_xml):
    numbers_in_tags = "<{tag}>(.*?)<\/{tag}>".format(
        tag=tag
    )

    matchs = re.findall(
        numbers_in_tags,
        annotation_xml
    )

    return convert_matches_to_floats(matchs)


def get_extrema_from(vals):
    return {
        "max": max(vals),
        "min": min(vals)
    }


def convert_matches_to_floats(matchs):
    return [
        convert_to_float(match) for match in matchs
    ]


def convert_to_float(match):
    """
         float conversion expects 1.0e-01
         xml is formatted like   -1.0e+01
    """
    modifier = 1

    if '-' in match:
        modifier = -1
        match = match.replace('-', '')

    return modifier * float(match)


def get_granule_extrema(swath_bounds):
    granule_lats, granule_lons = [], []

    for bound in swath_bounds:
        lats, lons = bound

        granule_lats += lats
        granule_lons += lons

    return get_extrema(granule_lats, granule_lons)
