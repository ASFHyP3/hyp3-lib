class GranulePair(object):
    def __init__(self, master, slave):
        self.master = master
        self.slave = slave

    def tuple(self):
        return (self.master, self.slave)

    def __str__(self):
        return "({m}, {s})".format(m=self.master, s=self.slave)

    def __repr__(self):
        return "GranulePair({m}, {s})".format(
            m=self.master,
            s=self.slave
        )


class SentinelGranulePair(GranulePair):
    def time_delta(self):
        return self.master.get_date() - self.slave.get_date()

    def get_dates(self):
        return self.master.start_date + "_" + self.slave.start_date

    def checksum_str(pair):
        return "{}-{}".format(pair.master.unique_id, pair.slave.unique_id)


def get_pairs(granule_list, gap=1, pair_type=GranulePair):
    """pairs up granule, takes a list of granules sorted by time"""
    granule_list.sort(key=lambda g: g.start_date)
    pair_list = []

    for i, granule in enumerate(granule_list):
        try:
            pair = pair_type(granule, granule_list[i + gap])
            pair_list.append(pair)
        except:
            break

    return pair_list
