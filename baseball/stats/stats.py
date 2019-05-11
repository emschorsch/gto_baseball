import pandas as pd
import numpy as np


class StatTracker():
    def __init__(self, value_labels=[], key_labels=[]):
        """
        For the use case where statistics are being kept for different objects
        It can be accessed as a dictionary and keeps track of each items stats
        The keys are expected to be a tuple of identifiers
        The values are a Stat object which supports division and addition
        Expects a list of column headers for the keys and the values
        """
        self.key_labels = key_labels
        self.value_labels = value_labels
        self.stats = {}

    def __getitem__(self, item):
        """
        WARNING: returns 0 by default
        """
        if item in self.stats:
            return self.stats[item]
        else:
            # Returns 0 for all the stats if key is unseen
            return np.zeros(len(self.value_labels))

    def __setitem__(self, key, value):
        self.stats[key] = value

    def __add__(self, other_stat_tracker):
        """
        Elementwise adds other_stat_tracker to itself
        Meant for case of acculumating stats across multiple games for each item
        WARNING: This modifies self and doesn't return a new instance
        """
        for key, val in other_stat_tracker.items():
            self[key] += val
        return self

    def __truediv__(self, divisor):
        """
        Turns divisor into float
        Elementwise division of each stat by <divisor>
        WARNING: This modifies self and doesn't return a new instance
        """
        for key in self.stats.keys():
            self[key] /= float(divisor)
        return self

    def __str__(self):
        """
        Returns only the first 5 items so the screen doesn't get flooded
        """
        return "{}".format(str(list(self.stats.items())[:5]))

    def __repr__(self):
        return self.__str__()

    def update_from_dict(self, otherDict):
        """
        Each key, value pair in otherDict is set in self
        WARNING: This overwrites not adds existing keys.
        If you want to add then use the + operator
        """
        for key, value in otherDict.items():
            self[key] = value

    def keys(self):
        return self.stats.keys()

    def items(self):
        return self.stats.items()

    def export_as_dataframe(self):
        """
        Uses the column labels given in the initialization to make a dataframe.
        The keys will be the first few columns, followed by the values
        """
        values = pd.DataFrame(list(self.stats.values()),
                              columns=self.value_labels)
        keys = pd.DataFrame(list(self.stats.keys()), columns=self.key_labels)
        return pd.concat([keys, values], axis=1)
