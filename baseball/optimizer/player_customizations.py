#!/usr/bin/python
import pandas as pd

import yaml
import os
import datetime
import math

from baseball.simulator import utils
from baseball.simulator import batting_rates_index as br

HITS_INDEXES = [br.SINGLE, br.DOUBLE, br.TRIPLE, br.HR]


def modification_date(filename):
    t = os.path.getmtime(filename)
    return datetime.datetime.fromtimestamp(t)


class PlayerCustomizations:
    """
    Handles player customizations as defined in player_customizations.yaml
    We expect a list of dictionaries representing player customizations
        after loading in the YAML
    Each dictionary should have at minimum mlb_id.
        potentially also a score multiplier and rate stats adjustments

    For more details look in player_customizations_example.yaml
    """
    def __init__(self, filename="player_customizations.yaml"):
        print("----/" * 12)
        self.players = {}
        self.teams = {}

        base_path = os.path.dirname(os.path.abspath(__file__)) + '/../../'
        customizations_filename = base_path + filename

        full_team_map = pd.read_csv(base_path + "fixtures/sfbb_mlbteammap.csv", dtype="str")
        retroteams = set(full_team_map["RETROTEAM"].unique())

        if not os.path.isfile(customizations_filename):
            print("\n\tERRROR!! no file: {}\n".format(customizations_filename))
            return None

        with open(customizations_filename, 'r') as stream:
            configs = yaml.load(stream)
            assert(set(configs.keys()) == set(['batters', 'teams']))
            # TODO: handle batters and pitchers separately?
            # TODO: have this process all the different factors that apply to a
            # batter. Then for each batter we only have to do one set of
            # adjustments. (multiply them all together or wtvr)
            for team in configs['teams']:
                assert(team['team_id'] in retroteams), team
                if 'bat_hand' in team:
                    assert(team['bat_hand'] in ['R', 'L'])
                    key = (team['team_id'], team['bat_hand'])
                else:
                    key = team['team_id']
                assert(key not in self.teams), (key, self.teams.keys())
                self.teams[key] = team

                # Handle team rate multipliers if present
                if 'batting_rates_multiplier' in team:
                    # Check that its the right stats
                    # WARNING: won't know if duplicate stats are entered.
                    affected_events = set(team['batting_rates_multiplier'].keys())
                    assert(affected_events.issubset(set(br.batting_events)))

            # TODO: for game adjustments adjust RP_rates as well since it's
            # usuallly a weather affect that affects all batters

            for player in configs['batters']:
                mlb_id = player['mlb_id']
                assert(len(str(mlb_id)) == 6)
                assert(mlb_id not in self.players)  # Only one entry per player
                self.players[mlb_id] = player

                # Handle player rate adjustments if present
                if 'batting_rates' in player:
                    # Check rates add up to 1 and have all the right stats
                    assert(set(player['batting_rates'].keys()) == set(br.batting_events))
                    assert(math.isclose(sum(player['batting_rates'].values()), 1))

                    player['batting_rates'] = utils.listify_stat_dict(player['batting_rates'])

                # Handle player rate multipliers if present
                if 'batting_rates_multiplier' in player:
                    # Check that its the right stats
                    affected_events = set(player['batting_rates_multiplier'].keys())
                    assert(affected_events.issubset(set(br.batting_events)))

            print("\t{} players are customized and {} teams\n".format(
                len(self.players), len(self.teams)))
            now = datetime.datetime.now()
            time_difference = now - modification_date(customizations_filename)
            hours_since_mod = time_difference.total_seconds()/(60*60)
            print("\t{0:.2f} hours since file last modified\n".format(hours_since_mod))
            if hours_since_mod > 24:
                print("\nWARNING: more than 24 hours since file modified!\n")
            print("----/" * 12)

        return

    def get_players(self):
        return self.players.values()

    def get_teams(self):
        return self.teams.items()

    def adjust_scores(self, player_predictions):
        # Do all player customizations specified by player_config.yaml
        player_ids = set(player_predictions["MLB_ID"])
        player_predictions = player_predictions.copy()
        for player in self.get_players():
            if player['mlb_id'] not in player_ids:
                print("Warning player in YAML but not playing in sim: ", player)
                continue

            # If score_multiplier not specified make it 1
            score_multiplier = player.get("score_multiplier", 1.0)
            player_rows = player_predictions["MLB_ID"] == player['mlb_id']
            if 'POS' in player:
                player_rows = player_rows & (player_predictions["DK posn"] == player['POS'])
                # Makes sure the player is matched for exactly 1 position.
                # Catches if enter the wrong POS for the player
                assert(player_rows.sum() == 1), player

            player_predictions.loc[player_rows, "custom DK pts pred"] *= score_multiplier

        for key, team_adj in self.get_teams():
            # TODO: for team adjustments which will prob be for weather affect
            # reliever stats as well
            score_multiplier = team_adj.get("score_multiplier", 1.0)
            batters = player_predictions["bat_spot"].notnull()
            team_players = (player_predictions["Team"] == team_adj['team_id'])
            if 'bat_hand' in team_adj:
                matching_handedness = (player_predictions["bat_hand"] == team_adj['bat_hand'])
            else:
                matching_handedness = True
            matching_players = batters & team_players & matching_handedness
            player_predictions.loc[matching_players, "custom DK pts pred"] *= score_multiplier

        return player_predictions

    def adjust_rates(self, team):
        team_id = team.team_id
        for player in team.lineup:
            if player.pid in self.players:
                player_adjustment = self.players[player.pid]
                if 'batting_rates' in player_adjustment:
                    # TODO: This makes the batting rates np.array, instead of
                    # pd.series
                    player.set_sp_batting_rates(player_adjustment['batting_rates'])

                stat_dict = player_adjustment.get('batting_rates_multiplier', {})
                self.adjust_event_rates(stat_dict, player)

            # Now apply relevant rate adjustments for team
            if team_id in self.teams:
                self.adjust_team_rates(self.teams[team_id], player)
            key = (team_id, player.bat_hand)
            if key in self.teams:
                self.adjust_team_rates(self.teams[key], player)

        return

    def adjust_team_rates(self, team_adj, player):
        # NOTE: This applies multipliers cumulatively so all multipliers that
        # are relevant will get applied
        rates = player.get_batting_rates().copy()
        if 'hit_rate_multiplier' in team_adj:
            rate_adjustment = team_adj['hit_rate_multiplier']
            rates.iloc[HITS_INDEXES] *= rate_adjustment
            player.set_sp_batting_rates(utils.normalize_stats(rates))

        stat_dict = team_adj.get('batting_rates_multiplier', {})
        self.adjust_event_rates(stat_dict, player)

    def adjust_event_rates(self, stat_dict, player):
        # TODO: put this in utils. Doesn't need to be here
        rates = player.get_batting_rates().copy()
        for event, multiplier in stat_dict.items():
            rates[event] *= multiplier
        player.set_sp_batting_rates(utils.normalize_stats(rates))
