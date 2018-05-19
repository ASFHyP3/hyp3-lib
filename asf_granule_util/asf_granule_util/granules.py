from .exceptions import InvalidGranuleException
import os
import re
import datetime


# From: https://earth.esa.int/web/sentinel/user-guides/sentinel-1-sar/naming-conventions
sentinel_pattern = re.compile(r"""
        (S1[AB])_           # Mission ID
        (IW|EW|WV|S[1-6])_  # Mode/Beam
        (GRD|SLC|OCN)       # Product Type
        ([FHM_])_           # Resolution
        ([12])              # Processing Level
        ([SA])              # Product Class
        (SH|SV|DH|DV)_      # Polarization
        (\d{8})T(\d{6})_    # Start (Date)T(Time)
        (\d{8})T(\d{6})_    # End (Date)T(Time)
        (\d{6})_            # Absolut Orbit Number
        ([0-9A-F]{6})_      # Missin Data Take ID
        ([0-9A-F]{4})       # Product Unique ID
""", re.X)


class Granule(object):
    def __init__(self, pattern, granule_string, attributes):
        m = re.search(pattern, granule_string)
        if m is None:
            raise InvalidGranuleException(
                "The string given does not describe a valid granule!", granule_string)

        g = m.groups()
        for i, attribute in enumerate(attributes):
            try:
                setattr(self, attribute, g[i])
            except IndexError:
                break

    # @abstractmethod <- So it works with python2
    def to_str(self):
        pass

    def __str__(self):
        return str(self.to_str())

    def __repr__(self):
        return self.__str__()



class SentinelGranule(Granule):
    @staticmethod
    def is_valid(possible_granule_string):
        return re.match(sentinel_pattern, possible_granule_string)

    def __init__(self, granule_string):
        length = len(granule_string)

        if length != 67:
            raise InvalidGranuleException(
                "Granule string is too {}! Must be 67 characters".format("short" if length < 67 else "long"), granule_string)

        attributes = self.get_attributes()
        super(SentinelGranule, self).__init__(sentinel_pattern, granule_string, attributes)

    def to_str(self):
        return "_".join([
            self.mission,
            self.beam_mode,
            self.prod_type + self.res,
            self.proc_level + self.prod_class + self.pol,
            self.start_date + "T" + self.start_time,
            self.stop_date + "T" + self.stop_time,
            self.orbit,
            self.data_id,
            self.unique_id
        ])

    def get_attributes(self):
        return [
            "mission",
            "beam_mode",
            "prod_type",
            "res",
            "proc_level",
            "prod_class",
            "pol",
            "start_date",
            "start_time",
            "stop_date",
            "stop_time",
            "orbit",
            "data_id",
            "unique_id"
        ]

    def get_start_date(self):
        """Returns datetime object start date"""
        return self.get_date(self.start_date + self.start_time)

    def get_stop_date(self):
        """Returns datetime object of stop date"""
        return self.get_date(self.stop_date + self.stop_time)

    def get_date(self, date_str, dtype='str'):
        """Returns datetime object from date_str formatted '%Y%m%d%H%M%S'"""
        return datetime.datetime.strptime(date_str, '%Y%m%d%H%M%S')

