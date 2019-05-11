#!/usr/bin/env python

import numpy as np


class Pitcher:
    def __init__(self, role="Default", pid="Default", hand="R", pitch_limit=95):
        self.role = role
        self.pid = pid
        self.hand = hand
        self.batting_pos = None
        self.reset()

        # NOTE: We shift pitch_limit down by 3 to account for a manager pulling
        # the pitcher if he is close to hitting his limit
        self.pitch_limit = pitch_limit - 3

    def __str__(self):
        return "{}: {}\tpitches: {:8.4f}".format(self.role, self.stats,
                                                 self.num_pitches)

    def __repr__(self):
        return self.__str__()

    def __add__(self, other_pitcher_stats):
        """
        Elementwise adds otherPitcherStats to itself
        Meant for case of acculumating stats across multiple games
        WARNING: This modifies self and doesn't return a new instance
        """
        for key, val in other_pitcher_stats.items():
            self.stats[key] += val
        self.num_pitches += other_pitcher_stats.get_num_pitches()
        return self

    def __truediv__(self, divisor):
        """
        Turns divisor into float
        Elementwise division of each stat by <divisor>
        WARNING: This modifies self and doesn't return a new instance
        """
        for key in self.stats:
            self.stats[key] /= float(divisor)

        self.num_pitches /= float(divisor)
        return self

    def reset(self):
        self.stats = {'IP': 0.0,
                      'SO': 0,
                      'W': 0,
                      'ER': 0,
                      'H': 0,
                      'BB': 0,
                      'HBP': 0,
                      'CG': 0,
                      'CGSO': 0,
                      'NH': 0,
                      'dk_score': 0}
        self.num_pitches = 0
        self.meets_win_requirements = False
        self.lead_changes = 0

    def increment_stat(self, stat, increment=1):
        self.stats[stat] += increment

    def increment_pitches(self, num_pitches):
        self.num_pitches += num_pitches

    def get_pitch_limit(self):
        return self.pitch_limit

    def get_num_pitches(self):
        return self.num_pitches

    def reached_pitch_limit(self, extra_pitches=0):
        """
        Check whether <pitcher> has reached his pitch_limit + <extra_pitches>.
        Extra pitches allow pitcher to increase his pitch_limit in certain
        cases (e.g. shutouts, no hitters, etc.)
        """
        if self.num_pitches < self.pitch_limit + extra_pitches:
            return False
        else:
            return True

    def get_stat(self, stat):
        return self.stats[stat]

    def get_dict(self):
        return self.stats

    def items(self):
        return self.stats.items()

    def left_with_win(self, own_score, opponent_score):
        """
        This method should be called right before next pitcher is subbed in
        Example: Pitcher is subbed out at end of half inning. Then assumes
            this method isn't called until pitcher's team gets a half inning
        """
        if own_score > opponent_score:
            self.meets_win_requirements = True
        else:
            self.meets_win_requirements = False

    def update_deserves_win(self, own_score, opponent_score):
        """
        This should be called any time the lead could have been given up.
        At minimum this must be called at the end of every half inning where
            the pitcher's team is fielding.
        """
        if own_score <= opponent_score:
            self.meets_win_requirements = False

    def check_deserves_win(self, own_score, opponent_score):
        """
        PREREQUISITES:
          Assumes team.check_lead_change was called after every fielding inning
        Check if pitcher should be assigned win
        """
        if own_score <= opponent_score:
            return  # Shouldn't get win

        # IP >= 4.9 to handle floats if 4.9998
        if self.meets_win_requirements and self.get_stat("IP") >= 4.9:
            self.increment_stat("W")

    def update_draftkings_score(self):
        """
        Calculates the draftkings score and stores it in self.stats['dk_score']
        """
        # TODO: convert stats into array like batter stats and use dot product
        stats = self.stats
        dk_points = 2.25*stats["IP"] + 2*stats["SO"] - 2*stats["ER"] + \
                    4*stats["W"] - .6*stats["H"] - \
                    .6*stats["BB"] - .6*stats["HBP"] + \
                    2.5*stats["CG"] + 2.5*stats["CGSO"] + 5*stats["NH"]
        self.stats['dk_score'] = dk_points
        return dk_points
