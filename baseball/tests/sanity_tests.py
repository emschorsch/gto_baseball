#!/usr/bin/env python
# Copyright (C) 2015 Author: Emanuel Schorsch

import unittest


class TestStatsConsistency(unittest.TestCase):
    def testStatIndexSanity(self):
        from baseball.simulator import stat_index as st
        assert(st.NUM_STATS == len(st.stats))
        assert(st.DK_multiplier == st.compute_dk_multiplier())
        for stat in st.stats:
            assert(st.__dict__[stat] == st.stats.index(stat))

    def testBattingRatesIndexSanity(self):
        from baseball.simulator import batting_rates_index as br
        assert(br.NUM_RATES == len(br.batting_events))
        for event in br.batting_events:
            assert(br.__dict__[event] == br.batting_events.index(event))

    def testMiscRatesIndexSanity(self):
        from baseball.simulator import misc_rates_index as mr
        assert(mr.NUM_RATES == len(mr.misc_events))
        for event in mr.misc_events:
            assert(mr.__dict__[event] == mr.misc_events.index(event))


if __name__ == "__main__":
    unittest.main()
