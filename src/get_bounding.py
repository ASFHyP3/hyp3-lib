import re

def numbers_between(tag, annotation_xml):
    numbers_in_tags = "<{tag}>(.*?)<\/{tag}>".format(
        tag=tag
    )

    matchs = re.findall(
        numbers_in_tags,
        annotation_xml
    )

    return convert_matches_to_floats(matchs)


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


def get_bounding(annotation_xml):
    lats = numbers_between('latitude', annotation_xml)
    lons = numbers_between('longitude', annotation_xml)

    return {
        "lat": get_extrema_from(lats),
        "lon": get_extrema_from(lons)
    }

def get_extrema_from(vals):
    return {
        "max": max(vals),
        "min": min(vals)
    }
