import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')))

import datetime

import granule_lib as gl


class TestSentinelGranule(unittest.TestCase):
    def setUp(self):
        self.ga = 'S1A_IW_SLC__1SSV_20150829T123751_20150829T123821_007478_00A50D_C506'
        self.gb = 'S1B_IW_SLC__1SDV_20170224T023050_20170224T023117_004436_007B7E_4835'

        self.ga_obj = gl.SentinelGranule(self.ga)
        self.gb_obj = gl.SentinelGranule(self.gb)

    def test_matches_granules(self):
        to_str_value = str(self.ga_obj)

        self.assertEqual(to_str_value, self.ga)

    def test_too_short_granules(self):
        too_short_str = 'afosd=b90'

        self.invalid_granules_raise_with(too_short_str)

    def test_invald_mission(self):
        bad_mission = self.gb.replace('B', 'C')

        self.invalid_granules_raise_with(bad_mission)

    def invalid_granules_raise_with(self, test_str):
        with self.assertRaises(gl.InvalidGranuleException):
            gl.SentinelGranule(test_str)

    def test_datetime_objects(self):
        start_date = datetime.datetime(
            year=2015, month=8, day=29, hour=12, minute=37, second=51
        )
        stop_date = datetime.datetime(
            year=2015, month=8, day=29, hour=12, minute=38, second=21
        )

        self.assertEqual(
            start_date,
            self.ga_obj.get_start_date()
        )
        self.assertEqual(
            stop_date,
            self.ga_obj.get_stop_date()
        )

    def test_date_strings(self):
        start_date, stop_date = self.ga[17:25], self.ga[33:41]

        self.assertEqual(start_date, self.ga_obj.start_date)
        self.assertEqual(stop_date, self.ga_obj.stop_date)

    def test_time_strings(self):
        start_time, stop_time = self.ga[26:32], self.ga[42:48]

        self.assertEqual(start_time, self.ga_obj.start_time)
        self.assertEqual(stop_time, self.ga_obj.stop_time)


if __name__ == '__main__':
    unittest.main()
