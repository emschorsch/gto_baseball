#!/usr/bin/env python
# Copyright (C) 2015 Author: Emanuel Schorsch
# cython: profile=True

from . import stat_index as st
from . import batting_rates_index as br
from . import misc_rates_index as mr

import pandas as pd


def default_batting_event_rates():
    return pd.Series([0.0]*br.NUM_RATES,
                     index=br.batting_events)


def default_misc_event_rates():
    return pd.Series([0.0]*mr.NUM_RATES,
                     index=mr.misc_events)


def normalize_batting_rates(batting_rates):
    batting_rates[br.OUT] = 1.0 - sum(batting_rates[:-1])


class Player:
    def __init__(self, age=-1, pid="", position="",
                 bat_hand="", switch_hitter=False):
        self.stats = [0]*st.NUM_STATS
        self.age = age
        self.pid = pid
        self.position = position
        self.bat_hand = bat_hand
        self.switch_hitter = switch_hitter
        # The batting rates against sp_pitcher (starting pitcher)
        self.sp_batting_rates = default_batting_event_rates()
        # Against rp_pitcher (generic reliever pitcher)
        self.rp_batting_rates = default_batting_event_rates()
        self.pinch_hitter_rates = default_batting_event_rates()
        self.reset()

        self.misc_rates = default_misc_event_rates()
        # TODO: should we do CDF method?
        normalize_batting_rates(self.batting_rates)
        assert(sum(self.batting_rates) == 1)

    def __str__(self):
        return str(self.stats) + "\nstarter rates: " + str(self.sp_batting_rates)

    def __repr__(self):
        return "mlb_id: {}".format(self.pid)

    def reset(self):
        """
        Resets player for a new game
        """
        self.stats = [0]*st.NUM_STATS
        # Reference to whichever rates are currently relevant
        self.facing_starter = True
        self.batting_rates = self.sp_batting_rates

    def get_batting_rates(self):
        return self.batting_rates

    def set_rp_batting_rates(self, rates):
        self.rp_batting_rates[:] = rates
        normalize_batting_rates(self.rp_batting_rates)

    def set_sp_batting_rates(self, rates):
        # Update in place so that batting_rates still points to the correct
        # version of sp_batting_rates instead of severing the connection
        self.sp_batting_rates[:] = rates
        normalize_batting_rates(self.sp_batting_rates)

    def set_pinch_hitter_rates(self, rates):
        self.pinch_hitter_rates[:] = rates
        normalize_batting_rates(self.pinch_hitter_rates)

    def set_facing_reliever(self):
        # Only change stats if currently facing a starter
        # This prevents pinch_hitter stats from being overriden during a subout
        # TODO: if switch_hitter set bat_hand to be S?
        if self.facing_starter:
            self.facing_starter = False
            self.batting_rates = self.rp_batting_rates

    def set_pinch_hitter_sub(self):
        # WARNING: Not technically true but necessary to prevent overwriting
        # TODO: this will mess up the average DK pts by spot in lineup even if we
        # throw out the stats for the batting pitcher at the end
        self.facing_starter = False
        self.batting_rates = self.pinch_hitter_rates

    def set_misc_rates(self, rates):
        self.misc_rates = rates

    def get_stats(self):
        return self.stats

    def increment_stat(self, stat, increment=1):
        self.stats[stat] += increment

    def get_misc_rate(self, event_index):
        return self.misc_rates[event_index]

    def get_batting_rate(self, event_index):
        return self.batting_rates[event_index]
