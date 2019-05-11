#!/usr/bin/env python
# Copyright (C) 2015 Author: Emanuel Schorsch

import unittest

import numpy as np
import pandas as pd

from baseball.simulator.team import Team
from baseball.simulator.simulator import simulate

from baseball.simulator import batting_rates_index as br
from baseball.simulator import utils


def initDoubleTeams():
    """
    Initializes home_team and away_team
    away_team simply gets out every at bat
    home_team gets a double 50% of the time and gets out 50%
    """
    batting_event_rates = utils.lineup_zeroed_batting_rates()
    batting_event_rates.loc[:, "DOUBLE"] = 0.5

    players = utils.lineup_from_batting_rates(batting_event_rates)

    home_team = Team(players, team_id="NYA")

    away_team = Team(team_id="ANA")

    return home_team, away_team


def sanityChecks(home_team, away_team):
    """
    Run simulator enough times that we can make assertions about what we expect
        certain stats to be. Verifies that CG, CGSO, W, num_pitches are tracked.
    """
    simulated_results = simulate(home_team, away_team, 500)
    results = simulated_results['avg_results']
    np.testing.assert_array_less(np.zeros((9, 12)) - .00001,
                                    np.array(results["home_playerstats"]))
    np.testing.assert_array_less(np.array(results["home_playerstats"]),
                                    np.full((9, 12), 100.0))
    np.testing.assert_array_less(np.zeros((9, 12)) - .00001,
                                    np.array(results["away_playerstats"]))
    # TODO: replace with better test
    #expected_away_stats = util.initialize_playerstats()
    #np.testing.assert_array_almost_equal(results["away_playerstats"], expected_away_stats, 2)
    home_pitcher = results["home_pitcher"]
    away_pitcher = results["away_pitcher"]
    assert(away_pitcher.get_stat('W') == 0)
    assert(0.9 <= home_pitcher.get_stat('W') <= 1.0)
    assert(home_pitcher.get_stat('CG') >= 0.9)
    assert(home_pitcher.get_stat('CGSO') >= 0.9)
    assert(home_pitcher.get_stat('NH') >= 0.9)
    assert(away_pitcher.get_stat('H') > 0)
    assert(home_pitcher.get_stat('H') == 0)
    assert(50 < away_pitcher.get_num_pitches() < 110)
    assert(50 < home_pitcher.get_num_pitches() < 110)
    return results


class TestSimulator(unittest.TestCase):
    def testSimpleDoubleTeam(self):
        """
        Run simulator with easy to reason about statistics so that sanityChecks
            can be run
        """
        # TODO: more precise tests here
        home_team, away_team = initDoubleTeams()
        print("steal team\n", sanityChecks(home_team, away_team))

    def testSimpleStealTeam(self):
        pass
        # TODO: implement a test which does basic testing of the SB module

    def testBraves(self):
        """
        Runs simulation enough times that stats stabilize
        Ensures that win rates and away score are in reasonable range
        """
        home_team = Team(team_id="ATL")

        # SINGLEs, DOUBLEs, TRIPLEs, HR, walks, HBP, SO, outs
        rates = [[0.168, 0.050, 0.007, 0.056, 0.146, 0.001, 0.001, 0.571],
                 [0.140, 0.040, 0.002, 0.049, 0.082, 0.000, 0.000, 0.687],
                 [0.165, 0.050, 0.003, 0.065, 0.165, 0.000, 0.000, 0.552],
                 [0.140, 0.060, 0.001, 0.043, 0.061, 0.000, 0.000, 0.695],
                 [0.190, 0.055, 0.000, 0.011, 0.069, 0.000, 0.000, 0.675],
                 [0.186, 0.044, 0.008, 0.040, 0.121, 0.000, 0.000, 0.601],
                 [0.200, 0.040, 0.000, 0.030, 0.100, 0.000, 0.000, 0.630],
                 [0.210, 0.040, 0.002, 0.043, 0.070, 0.000, 0.000, 0.635],
                 [0.096, 0.008, 0.000, 0.000, 0.040, 0.000, 0.000, 0.856]]

        batting_rates = pd.DataFrame(rates, columns=br.batting_events)
        players = utils.lineup_from_batting_rates(batting_rates)
        away_team = Team(players,
                         team_id="CHN")

        # TODO: np.random.seed(10)  # so we can put exact tests
        simulated_results = simulate(home_team, away_team, 10000)
        results = simulated_results['avg_results']
        assert(results["home_score"] == 0)
        assert(results["away_pitcher"].get_stat('ER') == 0)
        assert(results["away_pitcher"].get_stat('H') == 0)
        assert(0.99 <= results["away_pitcher"].get_stat('W'))
        assert(5.20 <= results["away_score"] <= 5.34)
        print("braves\n", results)
