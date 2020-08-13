from __future__ import print_function, absolute_import, division, unicode_literals

import os
import numpy as np

from hyp3lib import get_bounding


def test_simple_box():
    box_xml = '<latitude>1.0e+00</latitude>\n' \
              '<longitude>1.0e+00</longitude>\n' \
              '\n' \
              '<latitude>0.0e+00</latitude>\n' \
              '<longitude>0.0e+00</longitude>\n'

    truth = (0., 1., 0., 1.)  # lat_min, lat_max, lon_min, lon_max

    bound = get_bounding.get_bounding(box_xml)

    test = (bound['lat']['min'], bound['lat']['max'],
            bound['lon']['min'], bound['lon']['max'])

    assert np.allclose(truth, test, atol=1e-4)


def test_box_with_negatives():
    box_xml = '<latitude>-1.0e+00</latitude>\n' \
              '<longitude>-1.0e+00</longitude>\n' \
              '\n' \
              '<latitude>-0.3e+00</latitude>\n' \
              '<longitude>-0.3e+00</longitude>\n'

    truth = (-1., -0.3, -1., -0.3)  # lat_min, lat_max, lon_min, lon_max

    bound = get_bounding.get_bounding(box_xml)

    test = (bound['lat']['min'], bound['lat']['max'],
            bound['lon']['min'], bound['lon']['max'])

    assert np.allclose(truth, test, atol=1e-4)


def test_annotation_file_sample():
    box_xml = '<latitude>3.788855146424307e+01</latitude>\n' \
              '<longitude>-1.119597934146415e+02</longitude>\n' \
              '\n' \
              '<latitude>3.791710313604354e+01</latitude>\n' \
              '<longitude>-1.121557443533816e+02</longitude>\n'

    truth = (37.88855, 37.91710, -112.15574, -111.95979)  # lat_min, lat_max, lon_min, lon_max

    bound = get_bounding.get_bounding(box_xml)

    test = (bound['lat']['min'], bound['lat']['max'],
            bound['lon']['min'], bound['lon']['max'])

    assert np.allclose(truth, test, atol=1e-4)


def test_annotation_file(safe_data):
    with open(os.path.join(safe_data, 'annotation', 'test-swath-001.xml')) as f:
        box_xml = f.read()

    truth = (37.11964, 38.78037, -112.54442, -111.184078)  # lat_min, lat_max, lon_min, lon_max

    bound = get_bounding.get_bounding(box_xml)

    test = (bound['lat']['min'], bound['lat']['max'],
            bound['lon']['min'], bound['lon']['max'])

    assert np.allclose(truth, test, atol=1e-4)


def test_granule_bounding(safe_data):
    truth = (37.11964, 39.07924, -114.36318, -111.184078)  # lat_min, lat_max, lon_min, lon_max

    bound = get_bounding.get_granule_bounding(safe_data)

    test = (bound['lat']['min'], bound['lat']['max'],
            bound['lon']['min'], bound['lon']['max'])

    assert np.allclose(truth, test, atol=1e-4)
