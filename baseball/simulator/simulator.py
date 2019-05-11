#!/usr/bin/env python
# Copyright (C) 2015 Author: Emanuel Schorsch
# cython: profile=True

from . import game
from .team import Team
from . import stat_index as st

import pandas as pd
import numpy as np


class GameResults():
    def __init__(self, boxscore):
        """
        Expects the boxscore to be in the format output by simulator:
            A tuple of 4 elements (home_boxscore, home_score,
                                    away_boxscore, away_score)
        """
        index = game.get_boxscore_indexes()
        self.results = {}
        for key in index:
            self.results[key] = boxscore[index[key]]

        column_headers = st.stats + ("DK pts pred", )

        self.results['home_playerstats'] = pd.DataFrame(
            self.results['home_playerstats'],
            columns=column_headers)
        self.results['away_playerstats'] = pd.DataFrame(
            self.results['away_playerstats'],
            columns=column_headers)

    def __getitem__(self, item):
        return self.results[item]

    def __setitem__(self, key, value):
        self.results[key] = value

    def __add__(self, other_game_stats):
        """
        Elementwise adds other_game_stats to itself
        Meant for case of acculumating stats across multiple games
        WARNING: This modifies self and doesn't return a new instance
        """
        for key, val in other_game_stats.items():
            self[key] += val
        return self

    def __truediv__(self, divisor):
        """
        Turns divisor into float
        Elementwise division of each stat by <divisor>
        """
        for key in self.results.keys():
            self[key] /= float(divisor)
        return self

    def __str__(self):
        return "\t\thome_playerstats:\n{}\n\t\taway_playerstats:\n{}\n" \
            "\thome_pitcher:\n{}\n\taway_pitcher:\n{}\n" \
            " home_score: {}\t away_score: {}\t prob_home_win: {}" \
            "\npre_state_counts: {}\npost_state_counts: {}\n".format(
                str(self.results['home_playerstats']),
                str(self.results['away_playerstats']),
                self.results['home_pitcher'],
                self.results['away_pitcher'],
                self.results['home_score'],
                self.results['away_score'],
                self.results['prob_home_win'],
                self.results['pre_state_counts'],
                self.results['post_state_counts'])

    def __repr__(self):
        return self.__str__()

    def keys(self):
        return self.results.keys()

    def items(self):
        return self.results.items()


def simulate(home_team, away_team, num_iterations=1):
    """
    PRECONDITIONS: teams must be of type Team
    Simulate takes in two teams and simulates <num_iterations> times
    returns GameResult object of average game stats
    """
    # Initializes the cum_results aggregator to all 0s
    cum_results = game.Game(Team(), Team()).get_boxscore()
    # add column to boxscore for fantasy scores
    cum_results[0] = np.hstack((cum_results[0], np.zeros(9)[:, None]))
    cum_results[1] = np.hstack((cum_results[1], np.zeros(9)[:, None]))

    curr_game = game.Game(home_team, away_team)

    # for writeout
    headers = ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8", "p9", "pitcher"]
    home_dk_scores = [headers]
    away_dk_scores = [headers]

    for iteration in range(num_iterations):
        curr_game.reset_game()

        results = curr_game.simulate_game()
        # DK scores
        home_scores = get_batters_dk_scores(results[0])
        away_scores = get_batters_dk_scores(results[1])
        home_pitcher_score = results[2].update_draftkings_score()
        away_pitcher_score = results[3].update_draftkings_score()

        # Attach fantasy scores column to boxscore
        results[0] = np.hstack((results[0], home_scores[:, None]))
        results[1] = np.hstack((results[1], away_scores[:, None]))

        for i in range(len(cum_results)):
            cum_results[i] += results[i]

        home_scores = home_scores.tolist() + [home_pitcher_score]
        away_scores = away_scores.tolist() + [away_pitcher_score]

        # for cov calculation add opposing pitcher to end of array
        home_scores.append(away_pitcher_score)
        away_scores.append(home_pitcher_score)

        home_dk_scores.append(home_scores)
        away_dk_scores.append(away_scores)

    # TODO: pitcher bats in NL might lead to subtle bugs? doesn't always bat 9th

    # The coviariance matrixes where each column is treated as a predictor.
    home_covs = np.cov(np.array(home_dk_scores[1:]).transpose())
    away_covs = np.cov(np.array(away_dk_scores[1:]).transpose())

    home_ids = [home_team.lineup[i].pid for i in range(9)] + [results[2].pid]
    home_ids.append(results[3].pid)
    away_ids = [away_team.lineup[i].pid for i in range(9)] + [results[3].pid]
    away_ids.append(results[2].pid)
    cov_dict = {}

    for i in range(9+1):
        # TODO: since pitchers are at end of array should override any pitcher
        # as batter covariances if in NL. Make sure this is true in the dict(zip
        cov_dict[home_ids[i]] = dict(zip(home_ids, home_covs[i]))
        cov_dict[away_ids[i]] = dict(zip(away_ids, away_covs[i]))

    # Add covariances of away_pitcher to home_batters and vice versa
    cov_dict[results[3].pid].update(dict(zip(home_ids, home_covs[10])))
    cov_dict[results[2].pid].update(dict(zip(away_ids, away_covs[10])))

    info = {}
    info['avg_results'] = GameResults(cum_results)/num_iterations
    info['cov_dict'] = cov_dict
    info['home_dk_scores'] = home_dk_scores
    info['away_dk_scores'] = away_dk_scores

    return info


def get_batters_dk_scores(stats):
    return np.dot(stats, st.DK_multiplier)


if __name__ == "__main__":
    raise Exception("Main not implemented")


"""
Improvements for future:
    Is it faster to use numpy array or just 2d int array?
    Bring player functionality into Team. Keep player rates in 2d array
     in team, saving all the dictionary acceses (prob around a 1.5x speedup)
    Declare the type of the numpy array
"""
