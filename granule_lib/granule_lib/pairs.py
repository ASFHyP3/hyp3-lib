# pair.py
# Rohan Weeden
# Created: August 17, 2017

# Class definitions and helper functions for pairs of granules


class GranulePair(object):
    def __init__(self, g1, g2):
        self.master = g1
        self.slave = g2

    def to_obj(self):
        return [self.master.to_obj(), self.slave.to_obj()]

    def __str__(self):
        return "GranulePair(" + str(self.to_obj()) + ")"

    def __repr__(self):
        return self.__str__()


class SentinelGranulePair(GranulePair):
    def get_dates(self):
        return self.master.start_date + "_" + self.slave.start_date

    def checksum_str(pair):
        return "{}-{}".format(pair.master.unique_id, pair.slave.unique_id)


# pairs up granule, takes a list of granules sorted by time
def get_pairs(granule_list, gap=1, pair_type=GranulePair):
    granule_list.sort(key=lambda g: g.start_date)
    pair_list = []

    for i, granule in enumerate(granule_list):
        try:
            pair = pair_type(granule, granule_list[i + gap])
            pair_list.append(pair)
        except:
            break

    return pair_list
