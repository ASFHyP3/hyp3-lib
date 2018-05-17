# stack.py
# Rohan Weeden
# August 17, 2017

# Class definitions for a stack of granules

from .pairs import get_pairs, SentinelGranulePair


class GranuleStack(object):
    def __init__(self, granule_list=[]):
        self.granules = granule_list

    def add_granule(self, granule):
        self.granules.append(granule)

    @property
    def pairs(self):
        return get_pairs(self.granules, 1) + get_pairs(self.granules, 2)

    def to_str(self):
        return [pair.to_str() for pair in self.pairs]

    def __str__(self):
        pass

    def __repr__(self):
        return self.__str__()


class SentinelGranuleStack(GranuleStack):
    @property
    def pairs(self):
        return get_pairs(self.granules, 1, SentinelGranulePair) + get_pairs(self.granules, 2, SentinelGranulePair)
