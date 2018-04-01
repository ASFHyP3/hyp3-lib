import unittest
from get_bounding import get_bounding, get_granule_bounding


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

        self.granule_folder_path = '../testing_files/test.SAFE'
        self.test_annotation_path = self.granule_folder_path + \
            "/annotation/test-swath-1.xml"

    def test_simple_box(self):
        bound = get_bounding(self.basicBox)

        correct_lats = [0., 1.]
        correct_lons = [0., 1.]

        self.bound_equals(
            bound,
            correct_lats + correct_lons
        )

    def test_negatives(self):
        bound_with_negatives = get_bounding(self.negatives)

        correct_lats = [-1.0, -0.3]
        correct_lons = [-1.0, -0.3]

        self.bound_equals(
            bound_with_negatives,
            correct_lats + correct_lons
        )

    def test_annotation_file_sample(self):
        sample_bound = get_bounding(self.sample_from_test_file)

        correct_lats = [37.88855, 37.91710]
        correct_lons = [-112.15574, -111.95979]

        self.bound_equals(
            sample_bound,
            correct_lats + correct_lons
        )

    def test_annotation_file(self):
        correct_lats = [37.11964, 38.78037]
        correct_lons = [-112.54442, -111.184078]

        with open(self.test_annotation_path, 'r') as f:
            annotation_xml = f.read()

        bound = get_bounding(annotation_xml)

        self.bound_equals(
            bound,
            correct_lats + correct_lons
        )

    def test_granule_bounding(self):
        granule_bound = get_granule_bounding(self.granule_folder_path)

        self.assertIn('lat', granule_bound)
        self.assertIn('lon', granule_bound)

        print(granule_bound)

    def bound_equals(self, bound, check_values):
        lats, lons = bound['lat'], bound['lon']
        lat_min, lat_max, lon_min, lon_max = check_values

        self.assertAlmostEqual(lats['min'], lat_min, places=4)
        self.assertAlmostEqual(lats['max'], lat_max, places=4)
        self.assertAlmostEqual(lons['min'], lon_min, places=4)
        self.assertAlmostEqual(lons['max'], lon_max, places=4)


if __name__ == "__main__":
    unittest.main()
