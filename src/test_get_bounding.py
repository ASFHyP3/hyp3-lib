import unittest
from get_bounding import get_bounding


class TestGetBounding(unittest.TestCase):
    def setUp(self):
        self.basicBox = """
            <latitude>1.0e+00</latitude>
            <longitude>1.0e+00</longitude>

            <latitude>0.0e+00</latitude>
            <longitude>0.0e+00</longitude>
        """

        self.negatives = """
            <latitude>-1.0e+00</latitude>
            <longitude>-1.0e+00</longitude>

            <latitude>-0.3e+00</latitude>
            <longitude>-0.3e+00</longitude>

        """

        self.sample_from_test_file = """
            <latitude>3.788855146424307e+01</latitude>
            <longitude>-1.119597934146415e+02</longitude>

            <latitude>3.791710313604354e+01</latitude>
            <longitude>-1.121557443533816e+02</longitude>
        """

        self.test_annotation_path = "testing_files/test.SAFE/annotation"

    def test_simple_box(self):
        bound = get_bounding(self.basicBox)

        self.bound_equals(bound, [0., 1., 0., 1.])

    def test_negatives(self):
        bound_with_negatives = get_bounding(self.negatives)

        self.bound_equals(bound_with_negatives, [-1.0, -0.3, -1.0, -0.3])

    def test_annotation_file_sample(self):
        bound = get_bounding(self.sample_from_test_file)
        print(bound)


    def bound_equals(self, bound, check_values):
        lats, lons = bound['lat'], bound['lon']
        lat_min, lat_max, lon_min, lon_max = check_values

        self.assertAlmostEqual(lats['min'], lat_min, places=4)
        self.assertAlmostEqual(lats['max'], lat_max, places=4)
        self.assertAlmostEqual(lons['min'], lon_min, places=4)
        self.assertAlmostEqual(lons['max'], lon_max, places=4)


if __name__ == "__main__":
    unittest.main()
