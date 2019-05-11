#!/usr/bin/python

import pandas as pd

from tools import dk_lineup_processor


class DKGameDetails:
    def __init__(self, year, date):
        self.year = year
        self.date = date

        file_format = "fixtures/salaries/dk/{}/playerInfo_{}.csv"
        filename = file_format.format(self.year, date.lstrip("0"))

        player_data = pd.read_csv(filename, sep=",", encoding="latin-1")

        # Any char (eg '1') in the starter column means the player is starting
        # In NL there are two entries for the pitcher: as batter and as pitcher
        # The pitcher is indicated by having no bat order but still starting
        starters = player_data[player_data["starter"].notnull()].copy()
        starters["MLB_ID"] = starters["MLB_ID"].astype(int)

        dk_lineup_processor.sanity_checks(starters)

        # Many methods assume players are ordered by Team and then Bat order
        starters = starters.sort_values(by=["Team", "Bat order"])
        self.player_data = starters

    def prepare_player_data(self):
        player_data = self.player_data
        player_data["DK pts"] = 0

        # Removes pitchers as batters
        batting_pitchers = (player_data["DK posn"] == 'P') & (player_data["Bat order"].notnull())
        player_data = player_data[~batting_pitchers].copy()
        return player_data

    def game_info(self, game_id, cursor):
        """
        returns dict of relevant info like lineups, inn_ct, score, etc.
        game_result is dict of observed stats/events/results in <game_id>
            includes general info about the game
        """

        player_data = self.player_data[self.player_data["GameInfo"] == game_id]
        player_data = player_data.sort_values(by=["Team", "Bat order"])

        home_team = player_data[player_data["Team"] == player_data["stadium"]]
        away_team = player_data[player_data["Team"] != player_data["stadium"]]
        home_batters = home_team[home_team["Bat order"].notnull()]
        away_batters = away_team[away_team["Bat order"].notnull()]
        home_pitcher = home_team[home_team["Bat order"].isnull()]
        away_pitcher = away_team[away_team["Bat order"].isnull()]
        assert(len(player_data) == 20), player_data
        assert(len(home_batters) == 9), (home_batters, player_data.head())
        assert(len(away_batters) == 9), (away_batters, player_data.head())
        assert(len(home_pitcher) == 1), (home_pitcher, home_team)
        assert(len(away_pitcher) == 1), (away_pitcher, away_team)

        # Extracts the Series obj for each pitcher.
        # Makes accessing pitcher attributes simpler below
        home_pitcher = home_pitcher.iloc[0]
        away_pitcher = away_pitcher.iloc[0]
        game_result = {'game_id': game_id,
                       'stadium': home_pitcher["stadium"],
                       'home_team_id': home_pitcher["Team"],
                       'away_team_id': away_pitcher["Team"],
                       'home_pitcher_id': home_pitcher["MLB_ID"],
                       'away_pitcher_id': away_pitcher["MLB_ID"],
                       'home_pitcher_hand': home_pitcher["pit_hand"],
                       'away_pitcher_hand': away_pitcher["pit_hand"],
                       'year_id': self.year,
                       'inning': 9,
                       'game_time': home_pitcher["day_night"],
                       }

        teams_info = game_result.copy()
        teams_info['home_batter_ids'] = home_batters["MLB_ID"].tolist()
        teams_info['away_batter_ids'] = away_batters["MLB_ID"].tolist()
        # Actual pos the player is playing as on <date>. Not DK eligibility
        teams_info['home_fielder_pos'] = home_batters["POS"].tolist()
        teams_info['away_fielder_pos'] = away_batters["POS"].tolist()
        teams_info['home_bat_hands'] = home_batters["bat_hand"].tolist()
        teams_info['away_bat_hands'] = away_batters["bat_hand"].tolist()

        # TODO: see if can combine these two dicts into 1 esp since game_result
        # is already inside teams_info
        return game_result, teams_info

    def get_games_on_date(self, date, cursor):
        """
        Date looks like this: 1003 Assumes year of self.year
        Returns the DK game_id for all regular season games on that date
        """
        assert(date == self.date)
        return self.player_data["GameInfo"].unique().tolist()

    def create_pit_faced(self, date, cursor):
        assert(date == self.date)
        # Create table pit_faced for this specific date
        #   basically a dictionary of the starting pitcher each player is facing
        cursor.execute("create temporary table pit_faced AS "
                       "select batter, pitcher, p_throws from atbats limit 0;")
        cursor.fetchall()

        query = "INSERT INTO pit_faced VALUES "
        values = []

        for game in self.get_games_on_date(date, cursor):
            teams_info = self.game_info(game, cursor)[1]
            away_pit = teams_info['away_pitcher_id']
            home_pit = teams_info['home_pitcher_id']
            away_pit_hand = teams_info['home_pitcher_hand']
            home_pit_hand = teams_info['home_pitcher_hand']
            for batter in teams_info['home_batter_ids']:
                values.append("({}, {}, '{}')".format(batter, away_pit, away_pit_hand))
            for batter in teams_info['away_batter_ids']:
                values.append("({}, {}, '{}')".format(batter, home_pit, home_pit_hand))

        cursor.execute(query + ', '.join(values))
        cursor.fetchall()
