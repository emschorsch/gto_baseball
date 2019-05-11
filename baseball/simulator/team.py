#!/usr/bin/env python
# Copyright (C) 2015 Author: Emanuel Schorsch
# cython: profile=True

STUFF = "hi"


import numpy as np
import pandas as pd

from .player import Player
from .pitcher import Pitcher

from . import batting_rates_index as br


class Team:
    """
    Team class keeps lineup as list of players.
    batting_rates and misc_rates are the core probability distributions
        that will be used to form the Player objects
    lineup_ids is a list of mlb_ids
    fielding_lineup indicates each corresponding player's fielding position
    Tracks who is at bat, and what the score is
    """
    def __init__(self, lineup=None,
                 team_id="TEAM_NAME", starting_pitcher="DEFAULT"):
        self.team_id = team_id
        if lineup is None:
            lineup = []
            for i in range(9):
                lineup.append(Player())
        self.lineup = lineup

        if starting_pitcher == "DEFAULT":
            # TODO: this makes the SB model print out lots of stuff
            starting_pitcher = Pitcher(role="Starter", pid=None, hand='R')
        self.starter = starting_pitcher
        self.reliever = Pitcher(role="Reliever")

        self.catcher = Player()
        for player in self.lineup:
            if player.position == 'C':
                self.catcher = player

        self.reset_state()

    def __str__(self):
        return str(self.team_info_dataframe())

    def __repr__(self):
        return str(self)

    def team_info_dataframe(self):
        """
        Packs team player/pitcher rate stats and info into a DataFrame
        """
        info = []
        team_id = self.team_id
        for i, player in enumerate(self.lineup):
            # TODO: do we want to track reliever rates as well?
            sp_rates = player.sp_batting_rates.tolist()
            info.append([team_id, player.pid, i,
                         player.bat_hand, player.switch_hitter] + sp_rates)

        info.append([team_id, self.starter.pid])
        info_headers = ["Team", "MLB_ID", "bat_spot", "bat_hand", "switch_hitter"]
        info_headers.extend(event + "_rate" for event in br.batting_events)
        return pd.DataFrame(info, columns=info_headers)

    def reset_state(self):
        self.reliever_in = False
        self.pitcher = self.starter

        self.score = 0
        self.at_bat_index = 0

    def reset_team(self):
        """
        Resets the lineup for a new game.
        Sets all the player stats back to 0.
        Resets all pitcher stats
        """
        for player in self.lineup:
            player.reset()
        self.starter.reset()
        self.reliever.reset()
        self.reset_state()

    def get_boxscore(self):
        boxscore = []
        for player in self.lineup:
            boxscore.append(player.get_stats())
        return np.array(boxscore)

    def at_bat(self):
        """
        Returns the player_at_bat
        """
        return self.lineup[self.at_bat_index]

    def next_batter(self):
        """
        The current play is done.
        Sets the next batter in the lineup to be at_bat
        """
        self.at_bat_index = (self.at_bat_index + 1) % 9

    def check_lead_change(self, own_score, opponent_score):
        """
        Notifies the starter to check if his lead has been given up
        """
        self.starter.update_deserves_win(own_score, opponent_score)

    def handle_end_stats(self, own_score, opponent_score, inning_num):
        """
        Handles the pitcher stats at end of game.
        Determines if starter deserves win, NH, and CGSO
        """
        # Game is over so mark current pitcher if "left" with win
        self.pitcher.left_with_win(own_score, opponent_score)
        self.starter.check_deserves_win(own_score, opponent_score)

        self.handle_bonus_stats(self.pitcher, opponent_score, inning_num)

    def handle_bonus_stats(self, pitcher, opponent_score, inning_num):
        """
        Determines if pitcher deserves NH, CG and CGSO
        Assumes starter cannot be subbed back in after removal
        Reliever stats are irrelevant so assumes pitcher has a complete game
            This will be true if the pitcher is still the starter
        """
        pitcher.increment_stat("CG")
        if pitcher.get_stat("H") == 0.0 and inning_num >= 9:
            pitcher.increment_stat("NH")
        if opponent_score == 0:
            pitcher.increment_stat("CGSO")

    def sub_out_pitcher(self, own_score, opponent_score):
        """
        Handles the pitcher being subbed out.
        This method should be called right before next pitcher is subbed in
        Example: Pitcher is subbed out at end of half inning. Then assumes
            this method isn't called until pitcher's team gets a half inning
        """
        self.pitcher.left_with_win(own_score, opponent_score)
        # If we're in the NL sub in pinch hitter for pitcher
        if self.pitcher.batting_pos is not None:
            self.lineup[self.pitcher.batting_pos].set_pinch_hitter_sub()
        self.pitcher = self.reliever
        self.reliever_in = True

    def reliever_swapped_in(self):
        """
        Handles a reliever being subbed in
        Notifies all players to use reliever_batting_rates
        Assume starters are never subbed in so we don't need a corresponding method
        """
        for player in self.lineup:
            player.set_facing_reliever()
