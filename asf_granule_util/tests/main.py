import unittest
import sys

try:
    shouldnt_dl = sys.argv[1]
except:
    from test_download import TestDownload
else:
    sys.argv.remove(shouldnt_dl)


from test_granules import TestSentinelGranule
from test_pairs import TestPairs

if __name__ == "__main__":
    unittest.main()
