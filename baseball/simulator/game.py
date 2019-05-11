#!/usr/bin/env python
# Copyright (C) 2015 Author: Emanuel Schorsch

# cython: profile=True

import numpy as np

BASE_EMPTY = -1

from . import stat_index as st
from . import batting_rates_index as br

from baseball.sbModel.stolen_bases import StolenBases


def drand48():
    return np.random.uniform()


def choice(a, p):
    """
    a: A list of objects to be sampled by corresponding probabilities in p
    PREREQUISITES: p is a list of probabilties that sums to 1
    Faster version of np.random.choice without any sanity checks
    """
    assert(len(a) == len(p)), (a, p)
    x = drand48()
    # TODO: make sure the RNG doesn't have sequential correlation that would
    # be terrible for Monte Carlo to be accurate
    # Guaranteed for one of the events to happen
    for i, prob in enumerate(p):
        if x <= prob:
            return a[i]
        else:
            x -= prob

    print("no event selected? a: ", a, "\nprob: ", p)


def get_boxscore_indexes():
        index = {}
        index['home_playerstats'] = 0
        index['away_playerstats'] = 1

        index['home_pitcher'] = 2
        index['away_pitcher'] = 3

        index['home_score'] = 4
        index['away_score'] = 5
        index['prob_home_win'] = 6
        index['pre_state_counts'] = 7
        index['post_state_counts'] = 8
        return index


class Game:
    """
    Keeps track of whos on each base, numOuts, which team is batting
    """
    def __init__(self, home_team, away_team):
        """
        PRECONDITIONS:
            home_team is expected to be a team class
            away_team is expected to be a team class
        """
        # Home team always bats second
        self.home_team = home_team
        self.away_team = away_team

        self.sb = StolenBases()

        # Called at end of init to initialize all the fields
        self.reset_state()

    def __repr__(self):
        return "away score: {}\t home score: {}".format(self.away_team.score,
                                                        self.home_team.score)

    def reset_state(self):
        """
        Assumes team state has already been reset
        Resets game state
        """
        self.batting_team = self.away_team
        self.fielding_team = self.home_team

        self.pitcher = self.fielding_team.pitcher
        self.at_bat = self.batting_team.at_bat()

        self.first_base = BASE_EMPTY
        self.second_base = BASE_EMPTY
        self.third_base = BASE_EMPTY

        self.outs = 0
        self.inning_num = 1

        self.away_at_bat = True
        self.game_over = False

    def reset_game(self):
        """
        Resets state variables for the beginning of a new game.
        Resets all stats
        New game will have the same teams
        """
        self.away_team.reset_team()
        self.home_team.reset_team()

        self.reset_state()

    def get_boxscore(self):
        # TODO: make sure to update get_boxscore_index if change what is return
        home_score = self.home_team.score
        away_score = self.away_team.score
        if hasattr(self, "pre_state_counts"):
            pre_state_counts = self.pre_state_counts
            post_state_counts = self.post_state_counts
        else:
            pre_state_counts = np.zeros(8)
            post_state_counts = np.zeros(8)

        return [self.home_team.get_boxscore(),
                self.away_team.get_boxscore(),
                self.home_team.starter, self.away_team.starter,
                home_score, away_score,
                home_score > away_score,
                pre_state_counts, post_state_counts]

    def get_score(self):
        return (self.home_team.score, self.away_team.score)

    def get_home_pitcher(self):
        return self.home_team.starter

    def get_away_pitcher(self):
        return self.away_team.starter

    def simulate_game(self):
        """
        Simulates a game
        Returns the boxscore
        """
        self.pre_state_counts = np.zeros(8)
        self.post_state_counts = np.zeros(8)

        while not self.game_over:

            self.handle_pitcher_sub()
            self.at_bat = self.batting_team.at_bat()

            # TODO: differentiate state_counts by away_or home
            #   and by number of outs
            self.pre_state_counts[self.get_base_state()] += 1
            self.handle_steals()
            self.handle_event(self.random_PA())

        self.home_team.handle_end_stats(self.home_team.score,
                                        self.away_team.score, self.inning_num)
        self.away_team.handle_end_stats(self.away_team.score,
                                        self.home_team.score, self.inning_num)

        return self.get_boxscore()

    def random_PA(self):
        """
        Simulates a random Plate Appearance using the probability tables
        of whoever is at bat and on base
        """
        return choice(br.batting_events, self.at_bat.get_batting_rates())

    def switch_teams(self):
        """
        PRECONDITIONS: Assumes next_batter has already been called
        Switches the team that's at bat.
        Clears all the bases and resets the number of outs
        """
        # The home team is about to be up
        if self.away_at_bat:
            self.batting_team = self.home_team
            self.fielding_team = self.away_team
        else:
            self.batting_team = self.away_team
            self.fielding_team = self.home_team
            self.inning_num += 1
            # Cutoff game after 20 innings regardless.
            #   Shouldn't happen often so cutting short won't affect things
            if self.inning_num > 20:
                self.game_over = True

        self.pitcher = self.fielding_team.pitcher
        self.away_at_bat = not self.away_at_bat
        self.at_bat = self.batting_team.at_bat()

        self.outs = 0
        self.clear_bases()
        return

    def handle_half_inning(self):
        """
        PRECONDITIONS:
            Assumes self.outs >= 3
        RESPONSIBILITIES:
            Handles the end of half-inning
            Sets the game_over flag if appropriate
            Otherwise switches the teams and clears the bases
        """
        # The fielding team could have given up the lead
        # Not relevant that batting_team could have gained it
        self.fielding_team.check_lead_change(self.fielding_team.score,
                                             self.batting_team.score)

        if self.inning_num < 9:
            self.switch_teams()
            return

        # away_team is batting going into the bottom half of the inning
        if self.away_at_bat and self.away_team.score < self.home_team.score:
            self.game_over = True
            return
        elif not self.away_at_bat and self.away_team.score != self.home_team.score:
            self.game_over = True
            return
        else:
            self.switch_teams()
            return

    def handle_steals(self):
        """
        Determines if any of the players try to steal
        """

        # TODO: Need to verify that the inputs are correct
        #   and that the sb_probabilities are being computed fully and
        #   correctly

        """
        Loops through stolen base opportunities before advancing to the at bat.
        Continues looping until there is not a stolen base opportunity,
            someone chooses not to steal, or the third out is recorded via CS.
        """
        while self.steal_opportunity():
            sb_info = self.get_sb_info()

            # probability of attempt for all runners on first or second
            prob_attempt = self.sb.calc_prob_sb(sb_info, "attempt")
            if drand48() < prob_attempt:
                # probability of success for the lead runner
                prob_success = self.sb.calc_prob_sb(sb_info, "success")
                if drand48() < prob_success:
                    self.advance_sb_success(sb_info['base_state'])
                else:
                    self.advance_sb_failure(sb_info['base_state'])
                    if self.outs >= 3:
                        self.pitcher.increment_pitches(2)
                        self.handle_half_inning()
                        self.handle_pitcher_sub()
                        self.at_bat = self.batting_team.at_bat()
                        return
            else:
                self.post_state_counts[self.get_base_state()] += 1
                return
        self.post_state_counts[self.get_base_state()] += 1
        return

    def handle_event(self, event):
        """
        Implements the game logic for the mutually exclusive batting events
        """
        if event == "HR":
            self.pitcher.increment_stat("H", 1)
            self.at_bat.increment_stat(st.HR)
            self.advance_home()
        elif event == "TRIPLE":
            # TODO: Do the error rates differ at third than in other states
            self.pitcher.increment_stat("H", 1)
            self.at_bat.increment_stat(st.TRIPLE)
            self.at_bat.resp_pitcher = self.pitcher
            self.advance_home(False, True, True, True)
            self.third_base = self.at_bat
            # TODO: handle errors which would allow the batter to make it home
        elif event == "DOUBLE":
            self.handle_double()
        elif event == "SINGLE":
            self.handle_single()
        elif event == "BB":
            self.pitcher.increment_stat("BB", 1)
            self.at_bat.increment_stat(st.BB)
            self.at_bat.resp_pitcher = self.pitcher
            self.handle_force_advance()
        elif event == "HBP":
            self.pitcher.increment_stat("HBP", 1)
            self.at_bat.increment_stat(st.HBP)
            self.at_bat.resp_pitcher = self.pitcher
            self.handle_force_advance()
        elif event == "SO":
            self.pitcher.increment_stat("SO", 1)
            self.at_bat.increment_stat(st.OUT)
            self.update_outs()
        elif event == "OUT":
            self.at_bat.increment_stat(st.OUT)
            self.update_outs()
        else:
            print(self.home_team)
            print(self.away_team)
            raise ValueError("That is not a valid event! " + event)

        self.handle_pitch_count(event)

        self.batting_team.next_batter()
        self.at_bat = self.batting_team.at_bat()
        if self.outs >= 3:
            self.handle_half_inning()
        return

    def update_outs(self):
        """
        Increments number of outs and updates pither statistics
        Does not handle game logic of out such as team switch
        """
        self.pitcher.increment_stat("IP", 1/3.0)
        self.outs += 1

    def clear_bases(self):
        """
        Sets all the bases to have no players on them
        """
        self.first_base = BASE_EMPTY
        self.second_base = BASE_EMPTY
        self.third_base = BASE_EMPTY

    def handle_force_advance(self):
        """
        Implements the logic for a walk or hbp
        """
        if self.first_base != BASE_EMPTY:
            if self.second_base != BASE_EMPTY:
                if self.third_base != BASE_EMPTY:
                    self.handle_player_scores(self.third_base)
                self.third_base = self.second_base
            self.second_base = self.first_base
        self.first_base = self.at_bat

    def handle_single(self):
        self.pitcher.increment_stat("H", 1)
        self.at_bat.increment_stat(st.SINGLE)
        self.at_bat.resp_pitcher = self.pitcher
        if self.second_base == BASE_EMPTY:
            self.advance_home(False, False, False, True)
            event_generator = drand48()
            if event_generator < .5:
                self.third_base = self.first_base
            else:
                self.second_base = self.first_base
            self.first_base = self.at_bat
        elif self.first_base == BASE_EMPTY:
            event_generator = drand48()
            if event_generator < .5:
                self.advance_home(False, False, True, True)
            else:
                self.advance_home(False, False, False, True)
                self.third_base = self.second_base
                self.second_base = BASE_EMPTY
            self.first_base = self.at_bat
        elif self.third_base == BASE_EMPTY:
            # Handle the case of man on 1st and 2nd
            event_generator = drand48()
            if event_generator < .5:
                self.advance_home(False, False, False, True)
                self.third_base = self.second_base
                self.second_base = self.first_base
            elif event_generator < (2/3.0):
                # 1/6 chance of it ending with first and second
                self.advance_home(False, False, True, True)
                self.second_base = self.first_base
            else:
                # 1/3 chance of ending with first and third
                self.advance_home(False, False, True, True)
                self.third_base = self.first_base
            self.first_base = self.at_bat
        else:
            # Handle the case of bases loaded
            event_generator = drand48()
            if event_generator < .5:
                self.advance_home(False, False, True, True)
                self.third_base = self.first_base
            else:
                self.advance_home(False, False, False, True)
                self.third_base = self.second_base
                self.second_base = self.first_base
            self.first_base = self.at_bat

    def handle_double(self):
        self.pitcher.increment_stat("H", 1)
        self.at_bat.increment_stat(st.DOUBLE)
        self.at_bat.resp_pitcher = self.pitcher
        event_generator = drand48()
        if event_generator < .5:
            self.advance_home(False, True, True, True)
            self.second_base = self.at_bat
        else:
            self.advance_home(False, False, True, True)
            self.third_base = self.first_base
            self.first_base = BASE_EMPTY
            self.second_base = self.at_bat

    def advance_home(self, at_bat=True, first=True,
                     second=True, third=True):
        """
        For each base takes a boolean flag for whether or not to advance that
            runner home.
        Gives any runners advanced credit for a run and the batter for an rbi.
        It increments the score and clears the bases of the advanced players
        """
        if at_bat:
            self.at_bat.resp_pitcher = self.pitcher
            self.handle_player_scores(self.at_bat)
        if first and self.first_base != BASE_EMPTY:
            self.handle_player_scores(self.first_base)
            self.first_base = BASE_EMPTY
        if second and self.second_base != BASE_EMPTY:
            self.handle_player_scores(self.second_base)
            self.second_base = BASE_EMPTY
        if third and self.third_base != BASE_EMPTY:
            self.handle_player_scores(self.third_base)
            self.third_base = BASE_EMPTY

    def increment_score(self, increment):
        # TODO: should this method be inline?
        self.batting_team.score += increment
        return

    def game_state(self):
        return {"outs": self.outs,
                "away_score": self.away_team.score,
                "home_score": self.home_team.score,
                "inning_num": self.inning_num,
                "away_at_bat": self.away_at_bat,
                "on_first": self.first_base != BASE_EMPTY,
                "on_second": self.second_base != BASE_EMPTY,
                "on_third": self.third_base != BASE_EMPTY,
                }

    def advance_sb_success(self, base_state):

        if base_state in [1, 5]:
            self.first_base.increment_stat(st.SB)
            self.second_base = self.first_base
            self.first_base = BASE_EMPTY
        elif base_state == 2:
            self.second_base.increment_stat(st.SB)
            self.third_base = self.second_base
            self.second_base = BASE_EMPTY
        elif base_state == 3:
            self.first_base.increment_stat(st.SB)
            self.second_base.increment_stat(st.SB)
            self.third_base = self.second_base
            self.second_base = self.first_base
            self.first_base = BASE_EMPTY
        else:
            raise ValueError("sb_success: invalid base state! " + str(base_state))

    def advance_sb_failure(self, base_state):

        if base_state in [1, 5]:
            self.first_base.increment_stat(st.CS)
            self.first_base = BASE_EMPTY
        elif base_state == 2:
            self.second_base.increment_stat(st.CS)
            self.second_base = BASE_EMPTY
        # When runners are on 1st and 2nd, assumes the runner at second is
        #   always thrown out and the runner on first advances to second
        elif base_state == 3:
            self.second_base.increment_stat(st.CS)
            self.second_base = self.first_base
            self.first_base = BASE_EMPTY
        else:
            raise ValueError("sb_failure: invalid base state! " + base_state)
        self.update_outs()

    def get_base_state(self):
        """
        Returns the state of runners on base
        0 : bases empty
        1 : runner on first
        2 : runner on second
        3 : runners on first and second
        4 : runner on third
        5 : runners on first and third
        6 : runners on second and third
        7 : runners on first, second, and third
        """
        base_state = 0
        if self.first_base != BASE_EMPTY:
            base_state += 1
        if self.second_base != BASE_EMPTY:
            base_state += 2
        if self.third_base != BASE_EMPTY:
            base_state += 4
        return base_state

    def steal_opportunity(self):

        SB_OPPORTUNITIES = [1, 2, 3, 5]
        if self.get_base_state() in SB_OPPORTUNITIES:
            return True
        else:
            return False

    def get_sb_info(self):

        sb_info = {}

        sb_info['base_state'] = self.get_base_state()
        sb_info['pitcher'] = self.pitcher.pid
        sb_info['catcher'] = self.fielding_team.catcher.pid
        sb_info['runner_team'] = "runner_team"+self.batting_team.team_id
        sb_info['pitcher_hand'] = "hand"+self.pitcher.hand
        sb_info['inning_state'] = "state"+str(sb_info['base_state'])+"_"+str(self.outs)
        if sb_info['base_state'] in [1, 5]:
            sb_info['runner'] = self.first_base.pid
        else:
            sb_info['runner'] = self.second_base.pid
        sb_info['runner_team:pitcher_hand'] = (sb_info['runner_team'] + ":" +
                                               sb_info['pitcher_hand'])
        sb_info['runner_team:inning_state'] = (sb_info['runner_team'] + ":" +
                                               sb_info['inning_state'])
        sb_info['pitcher_hand:inning_state'] = (sb_info['pitcher_hand'] + ":" +
                                                sb_info['inning_state'])
        sb_info['runner_team:pitcher_hand:inning_state'] = (sb_info['runner_team'] + ":" +
                                                            sb_info['pitcher_hand'] + ":" +
                                                            sb_info['inning_state'])

        return sb_info

    def handle_pitcher_sub(self):
        """
        Check if pitcher should be switched out before plate appearance
        """
        # NOTE: IP/ER criteria was somewhat arbitrarily selected.
        # TODO: Verify this doesn't affect pitchers earning wins.
        # TODO: Examine the variabililty of pitch counts around the pitch limit
        #       when pitchers are pulled
        if self.pitcher.get_stat('H') == 0:
            return
        elif self.pitcher.get_stat('ER') == 0 and not self.pitcher.reached_pitch_limit(extra_pitches=20):
            return
        elif self.pitcher.get_stat('IP') < 4 and self.pitcher.get_stat('ER') > 4:
            self.sub_out_pitcher()
        elif 4 <= self.pitcher.get_stat('IP') < 5 and self.pitcher.get_stat('ER') > 5:
            self.sub_out_pitcher()
        elif self.pitcher.get_stat('IP') >= 5 and self.pitcher.get_stat('ER') > 6:
            self.sub_out_pitcher()
        elif self.pitcher.reached_pitch_limit():
            self.sub_out_pitcher()

    def handle_player_scores(self, player):
        """
        Increments the necessary statistics. Assumes not a result of an error
        """
        player.resp_pitcher.increment_stat("ER", 1)
        player.increment_stat(st.RUN)
        # TODO: this should maybe go outside the method. cause for steals AT bat
        # doesn't get an RBI
        self.at_bat.increment_stat(st.RBI)
        self.increment_score(1)

    def handle_pitch_count(self, event):
        '''
        Increments the pitch count of <pitcher> appropriately.
        '''

        # pmf[i] = Prob(plate appearance lasts i pitches | <event>)
        if event in ("SINGLE", "DOUBLE", "TRIPLE", "HR"):
            # TODO: takes lots of time cause need to make the random.choice
            pmf = [0.0, 0.1535, 0.2218, 0.2029, 0.1613, 0.1244, 0.0798, 0.0339,
                   0.0141, 0.0053, 0.0020, 0.0006, 0.0002, 0.0001, 0.0001]
            num_pitches = choice(list(range(len(pmf))), pmf)
            self.pitcher.increment_pitches(num_pitches)
        elif event == "OUT":
            pmf = [0.0, 0.1529, 0.2240, 0.2045, 0.1623, 0.1247, 0.0776, 0.0333,
                   0.0127, 0.0049, 0.0019, 0.0007, 0.0003, 0.0001, 0.0001]
            num_pitches = choice(list(range(len(pmf))), pmf)
            self.pitcher.increment_pitches(num_pitches)
        elif event == "BB":
            pmf = [0.0, 0.0, 0.0, 0.0, 0.1812, 0.3071, 0.2809, 0.1369, 0.0574,
                   0.0227, 0.0090, 0.0031, 0.0012, 0.0004, 0.0001]
            num_pitches = choice(list(range(len(pmf))), pmf)
            self.pitcher.increment_pitches(num_pitches)
        elif event == "SO":
            pmf = [0.0, 0.0, 0.0, 0.1795, 0.2840, 0.2596, 0.1707, 0.0663,
                   0.0255, 0.0092, 0.0035, 0.0013, 0.0003, 0.0001]
            num_pitches = choice(list(range(len(pmf))), pmf)
            self.pitcher.increment_pitches(num_pitches)
        else:  # event == "HBP"
            pmf = [0.0, 0.1916, 0.2125, 0.2023, 0.1826, 0.1175, 0.0594, 0.0224,
                   0.0079, 0.0026, 0.0004, 0.0006, 0.0002]
            num_pitches = choice(list(range(len(pmf))), pmf)
            self.pitcher.increment_pitches(num_pitches)

    def sub_out_pitcher(self):
        '''
        Replaces active pitcher with a default reliever.
        '''

        self.batting_team.reliever_swapped_in()
        self.fielding_team.sub_out_pitcher(self.fielding_team.score,
                                           self.batting_team.score)
        self.pitcher = self.fielding_team.pitcher
