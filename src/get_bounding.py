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
    values = []

    for match in matchs:
        modifier = 1

        if '-' in match:
            modifier = -1
            match = match.replace('-', '')

        value = modifier * float(match)
        values.append(value)

    return values


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
