"""Get the lat/lon min/max values given a .SAFE directory"""

from __future__ import print_function, absolute_import, division, unicode_literals

import re
import os
import argparse


def get_granule_bounding(granule_path):
    annotation_xml_paths = get_annotation_xmls_paths(granule_path)

    annotation_xmls = read_files(annotation_xml_paths)

    bounds = [
        get_values_from(xml_contents) for xml_contents in annotation_xmls
    ]

    return get_granule_extrema(bounds)


def get_annotation_xmls_paths(granule_path):
    annotation_dir = os.path.join(granule_path, 'annotation')

    annotation_folder_paths = [
        os.path.join(annotation_dir, f)
        for f in os.listdir(annotation_dir) if is_xml_file(f)
    ]

    return annotation_folder_paths


def is_xml_file(f):
    return re.match('.*\.xml', f)


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


def nice_printout(granule_path, extrema):
    print("from granule: {}\n".format(granule_path))

    print("lat:")
    print("  min: {}".format(extrema['lat']['min']))
    print("  max: {}".format(extrema['lat']['max']))

    print("lon:")
    print("  min: {}".format(extrema['lon']['min']))
    print("  max: {}".format(extrema['lon']['max']))


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument(
        'granule_safe_path',
        help='relative path to a *.SAFE directory containing the annotation xml files'
    )
    args = parser.parse_args()

    granule_path = args.granule_safe_path

    extrema = get_granule_bounding(granule_path)

    nice_printout(granule_path, extrema)


if __name__ == "__main__":
    main()
