#!/usr/bin/env python
# Copyright (C) 2015 Author: Emanuel Schorsch

import unittest

import numpy as np
import pandas as pd

from baseball.simulator.team import Team
from baseball.simulator.game import Game
from baseball.simulator import stat_index as st

from baseball.tests.python_simulator_tests import initDoubleTeams


def initialize_playerstats():
    # Initializes the cum_results aggregator to all 0s
    results = Game(Team(), Team()).get_boxscore()
    return pd.DataFrame(results[0], columns=st.stats)


class TestGame(unittest.TestCase):
    def testInvalidEvent(self):
        home_team, away_team = initDoubleTeams()
        curr_game = Game(home_team, away_team)
        self.assertRaises(ValueError, curr_game.handle_event, "INVALID")

    def testEndCondition(self):
        """
        Test to check that the end conditions of the game are correct
        Simulates two teams against each other that always get out
        Game should get cut off after 21 innings with no winner.
        """
        home_team = Team()
        away_team = Team()

        curr_game = Game(home_team, away_team)
        curr_game.simulate_game()
        stats = curr_game.get_boxscore()
        state = curr_game.game_state()
        assert(state == {'outs': 0, 'away_score': 0, 'home_score': 0,
                         'inning_num': 21, 'away_at_bat': True,
                         'on_first': False, 'on_second': False, 'on_third': False})
        expected_stats = initialize_playerstats()
        expected_stats.loc[:5, "OUT"] = 7
        expected_stats.loc[6:, "OUT"] = 6
        np.testing.assert_array_equal(expected_stats, stats[0])
        np.testing.assert_array_equal(expected_stats, stats[1])

        home_pitcher = curr_game.get_home_pitcher()
        away_pitcher = curr_game.get_away_pitcher()
        assert(away_pitcher.get_stat('W') == 0)
        assert(home_pitcher.get_stat('W') == 0)
        assert(away_pitcher.get_stat('H') == 0)
        assert(home_pitcher.get_stat('H') == 0)
        # TODO: New Test. Pitchers pitch continuously if they have a no hitter
        #assert(away_pitcher.get_num_pitches() < 110)
        #assert(home_pitcher.get_num_pitches() < 110)
        assert(away_pitcher.get_num_pitches() > 95)
        assert(home_pitcher.get_num_pitches() > 95)

    def testGameInit(self):
        home_team, away_team = initDoubleTeams()
        curr_game = Game(home_team, away_team)
        print(curr_game)
        stats = curr_game.get_boxscore()
        state = curr_game.game_state()
        assert(state == {'outs': 0, 'away_score': 0, 'home_score': 0,
                         'inning_num': 1, 'away_at_bat': True,
                         'on_first': False, 'on_second': False, 'on_third': False})
        np.testing.assert_array_equal(np.zeros((9, 11)), stats[0])
        np.testing.assert_array_equal(np.zeros((9, 11)), stats[1])
        # should all be 0

    def testSOandHbpLogic(self):
        home_team, away_team = initDoubleTeams()
        curr_game = Game(home_team, away_team)
        curr_game.handle_event("HBP")
        curr_game.handle_event("SO")
        curr_game.handle_event("SO")
        curr_game.handle_event("HBP")
        stats = curr_game.get_boxscore()
        state = curr_game.game_state()
        assert(state == {'outs': 2, 'away_score': 0, 'home_score': 0,
                         'inning_num': 1, 'away_at_bat': True,
                         'on_first': True, 'on_second': True, 'on_third': False})

        home_pitcher = curr_game.get_home_pitcher()
        away_pitcher = curr_game.get_away_pitcher()
        assert(away_pitcher.get_stat('HBP') == 0)
        assert(home_pitcher.get_stat('HBP') == 2)
        self.assertAlmostEqual(home_pitcher.get_stat('IP'), 2/3.0)
        assert(away_pitcher.get_num_pitches() == 0)
        assert(away_pitcher.get_stat('IP') == 0)
        assert(away_pitcher.get_stat('H') == 0)
        assert(home_pitcher.get_stat('H') == 0)

        expected_away_stats = initialize_playerstats()
        expected_away_stats.loc[(0, 3), "HBP"] = 1
        expected_away_stats.loc[(1, 2), "OUT"] = 1
        expected_home_stats = initialize_playerstats()

        np.testing.assert_array_equal(expected_home_stats, stats[0])
        np.testing.assert_array_equal(expected_away_stats, stats[1])

    def testBasicWalkLogic(self):
        home_team, away_team = initDoubleTeams()
        curr_game = Game(home_team, away_team)
        curr_game.handle_event("BB")
        curr_game.handle_event("OUT")
        curr_game.handle_event("BB")
        stats = curr_game.get_boxscore()
        state = curr_game.game_state()
        assert(state == {'outs': 1, 'away_score': 0, 'home_score': 0,
                         'inning_num': 1, 'away_at_bat': True,
                         'on_first': True, 'on_second': True, 'on_third': False})

        home_pitcher = curr_game.get_home_pitcher()
        away_pitcher = curr_game.get_away_pitcher()
        assert(away_pitcher.get_stat('BB') == 0)
        assert(home_pitcher.get_stat('BB') == 2)
        self.assertAlmostEqual(home_pitcher.get_stat('IP'), 1/3.0)
        # TODO: implement new test to check number of pitches
        # self.assertAlmostEqual(home_pitcher.get_num_pitches(), 3.8+2*4.8,
        #                        places=4)
        assert(away_pitcher.get_num_pitches() == 0)
        assert(away_pitcher.get_stat('IP') == 0)
        assert(away_pitcher.get_stat('H') == 0)
        assert(home_pitcher.get_stat('H') == 0)

        expected_away_stats = initialize_playerstats()
        expected_away_stats.loc[(0, 2), "BB"] = 1
        expected_away_stats.loc[1, "OUT"] = 1
        expected_home_stats = initialize_playerstats()

        np.testing.assert_array_equal(expected_home_stats, stats[0])
        np.testing.assert_array_equal(expected_away_stats, stats[1])

    def testWalkLogic(self):
        home_team, away_team = initDoubleTeams()
        curr_game = Game(home_team, away_team)
        curr_game.handle_event("BB")
        curr_game.handle_event("BB")
        curr_game.handle_event("OUT")
        curr_game.handle_event("BB")
        curr_game.handle_event("BB")
        curr_game.handle_event("OUT")
        curr_game.handle_event("OUT")
        curr_game.handle_event("TRIPLE")
        curr_game.handle_event("BB")
        stats = curr_game.get_boxscore()
        state = curr_game.game_state()
        assert(state == {'outs': 0, 'away_score': 1, 'home_score': 0,
                         'inning_num': 1, 'away_at_bat': False,
                         'on_first': True, 'on_second': False, 'on_third': True})

        home_pitcher = curr_game.get_home_pitcher()
        away_pitcher = curr_game.get_away_pitcher()
        assert(away_pitcher.get_stat('BB') == 1)
        assert(home_pitcher.get_stat('BB') == 4)
        self.assertAlmostEqual(home_pitcher.get_stat('IP'), 1)
        assert(away_pitcher.get_stat('IP') == 0)
        assert(away_pitcher.get_stat('H') == 1)
        assert(home_pitcher.get_stat('H') == 0)

        expected_away_stats = initialize_playerstats()
        expected_away_stats.loc[(0, 1, 3, 4), "BB"] = 1
        expected_away_stats.loc[(2, 5, 6), "OUT"] = 1
        expected_away_stats.loc[0, "RUN"] = 1
        expected_away_stats.loc[4, "RBI"] = 1
        expected_home_stats = initialize_playerstats()
        expected_home_stats.loc[0, "TRIPLE"] = 1
        expected_home_stats.loc[1, "BB"] = 1

        np.testing.assert_array_equal(expected_home_stats, stats[0])
        np.testing.assert_array_equal(expected_away_stats, stats[1])

    def testTripleLogic(self):
        home_team, away_team = initDoubleTeams()
        curr_game = Game(home_team, away_team)
        curr_game.handle_event("TRIPLE")
        curr_game.handle_event("BB")
        curr_game.handle_event("OUT")
        curr_game.handle_event("TRIPLE")
        stats = curr_game.get_boxscore()
        state = curr_game.game_state()
        assert(state == {'outs': 1, 'away_score': 2, 'home_score': 0,
                         'inning_num': 1, 'away_at_bat': True,
                         'on_first': False, 'on_second': False, 'on_third': True})

        home_pitcher = curr_game.get_home_pitcher()
        away_pitcher = curr_game.get_away_pitcher()
        assert(away_pitcher.get_stat('BB') == 0)
        assert(home_pitcher.get_stat('BB') == 1)
        self.assertAlmostEqual(home_pitcher.get_stat('IP'), 1/3.0)
        assert(away_pitcher.get_stat('IP') == 0)
        assert(away_pitcher.get_stat('H') == 0)
        assert(home_pitcher.get_stat('H') == 2)
        assert(home_pitcher.get_stat('ER') == 2)

        expected_away_stats = initialize_playerstats()
        expected_away_stats.loc[(0, 1), "RUN"] = 1
        expected_away_stats.loc[(0, 3), "TRIPLE"] = 1
        expected_away_stats.loc[2, "OUT"] = 1
        expected_away_stats.loc[1, "BB"] = 1
        expected_away_stats.loc[3, "RBI"] = 2
        expected_home_stats = initialize_playerstats()

        np.testing.assert_array_equal(expected_home_stats, stats[0])
        np.testing.assert_array_equal(expected_away_stats, stats[1])

        return stats

    def testInningSwitch(self):
        home_team, away_team = initDoubleTeams()
        curr_game = Game(home_team, away_team)
        curr_game.handle_event("BB")
        curr_game.handle_event("OUT")
        curr_game.handle_event("OUT")
        curr_game.handle_event("OUT")
        curr_game.handle_event("BB")
        curr_game.handle_event("HR")
        curr_game.handle_event("OUT")
        curr_game.handle_event("OUT")
        curr_game.handle_event("OUT")
        curr_game.handle_event("HR")
        curr_game.handle_event("OUT")
        stats = curr_game.get_boxscore()
        state = curr_game.game_state()
        assert(state == {'outs': 1, 'away_score': 1, 'home_score': 2,
                         'inning_num': 2, 'away_at_bat': True,
                         'on_first': False, 'on_second': False, 'on_third': False})

        home_pitcher = curr_game.get_home_pitcher()
        away_pitcher = curr_game.get_away_pitcher()
        assert(away_pitcher.get_stat('BB') == 1)
        assert(home_pitcher.get_stat('BB') == 1)
        self.assertAlmostEqual(home_pitcher.get_stat('IP'), 4/3.0)
        self.assertAlmostEqual(away_pitcher.get_stat('IP'), 3/3.0)
        assert(away_pitcher.get_stat('H') == 1)
        assert(home_pitcher.get_stat('H') == 1)
        assert(away_pitcher.get_stat('ER') == 2)
        assert(home_pitcher.get_stat('ER') == 1)

        expected_away_stats = initialize_playerstats()
        expected_away_stats.loc[0, "BB"] = 1
        expected_away_stats.loc[4, "RUN"] = 1
        expected_away_stats.loc[4, "HR"] = 1
        expected_away_stats.loc[4, "RBI"] = 1
        expected_away_stats.loc[(1, 2, 3, 5), "OUT"] = 1
        expected_home_stats = initialize_playerstats()
        expected_home_stats.loc[0, "BB"] = 1
        expected_home_stats.loc[(0, 1), "RUN"] = 1
        expected_home_stats.loc[2:4, "OUT"] = 1
        expected_home_stats.loc[1, "RBI"] = 2
        expected_home_stats.loc[1, "HR"] = 1

        np.testing.assert_array_equal(expected_home_stats, stats[0])
        np.testing.assert_array_equal(expected_away_stats, stats[1])

        return stats


if __name__ == "__main__":
    unittest.main()
