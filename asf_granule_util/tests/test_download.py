import unittest
import sys
import os
import json
import timeout as to

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')))
import asf_granule_util as gu


class TestDownload(unittest.TestCase):
    def setUp(self):
        test_granules_path = os.path.join(
            os.path.dirname(__file__), 'data/granules.json'
        )

        with open(test_granules_path, 'r') as f:
            self.ga, self.gb = json.load(f)

        self.ga_obj = gu.SentinelGranule(self.ga)
        self.gb_obj = gu.SentinelGranule(self.gb)

        username, password = get_creds()

        self.directory = '.'

        self.creds = {
            'username': username,
            'password': password
        }

    def tearDown(self):
        os.remove(os.path.join(self.directory, self.ga + '.zip'))

    def test_download_starts_with_bar(self):
        with self.assertRaises(to.TimeoutException):
            self.download_with_timeout(has_bar=True)

    def test_download_starts_without_bar(self):
        with self.assertRaises(to.TimeoutException):
            self.download_with_timeout(has_bar=False)

    def download_with_timeout(self, has_bar):
        with to.timeout(5):
            gu.download(
                granule=self.ga_obj,
                credentials=self.creds,
                directory=self.directory,
                progess_bar=has_bar
            )


def get_creds():
    with open('/home/william/Documents/test-earthdata.sh', 'r') as f:
        auth = f.read() \
            .strip()    \
            .split('\n')

    return tuple(v.split('=').pop() for v in auth)


if __name__ == "__main__":
    unittest.main()
