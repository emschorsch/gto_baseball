#!/usr/bin/python

import numpy as np


class HistoricalGameDetails:
    def __init__(self, year):
        self.year = year

        # TODO: Verify these numberings match with others used later
        self.defensive_position = {'P': 1, 'C': 2, '1B': 3, '2B': 4, '3B': 5,
                                   'SS': 6, 'LF': 7, 'CF': 8, 'RF': 9, 'DH': 10}

    def game_info(self, game_id, cursor):
        """
        returns dict of relevant info like lineups, inn_ct, score, etc.
        game_result is dict of observed stats/events/results in <game_id>
            includes general info about the game
        """

        # Get game info for <game_id>
        cursor.execute(
            "SELECT g.gameName AS game_id, UPPER(home_code) AS stadium,"
            " UPPER(home_code) AS home_team_id, UPPER(away_code) AS away_team_id,"
            " home_team_runs, away_team_runs, p1.id AS home_pitcher_id,"
            " p2.id AS away_pitcher_id, inning, game_time,"
            " p1.rl AS home_pitcher_hand, p2.rl AS away_pitcher_hand, year_id "
            "FROM gameDetail AS g "
            "JOIN players AS p1 ON p1.gameName=g.gameName AND"
            " p1.game_position='P' AND p1.homeaway='home' "
            "JOIN players AS p2 ON p2.gameName=g.gameName AND"
            " p2.game_position='P' AND p2.homeaway='away' "
            "WHERE g.gameName='%s';" % game_id)
        game_info = cursor.fetchall()[0]
        game_info_fields = cursor.description

        # Initializes game_result dict with SQL column headers as keys
        game_result = dict([(game_info_fields[i][0], game_info[i])
                            for i in range(len(game_info))])

        teams_info = {}
        for field in ['game_time', 'year_id', 'home_team_id', 'away_team_id',
                      'home_pitcher_id', 'away_pitcher_id', 'home_pitcher_hand',
                      'away_pitcher_hand', 'stadium']:
            teams_info[field] = game_result[field]

        # Get lineup and defensive positions for home and away teams for
        # <game_id>
        cursor.execute(
            "SELECT id, game_position "
            "FROM players "
            "WHERE gameName='%s' and bat_order BETWEEN 1 AND 9 "
            "ORDER BY homeaway ASC, bat_order ASC;" % game_id)
        lineup_info = cursor.fetchall()

        teams_info['away_batter_ids'] = []
        teams_info['away_fielder_pos'] = []
        for i in range(0, 9):
            teams_info['away_batter_ids'].append(lineup_info[i][0])
            teams_info['away_fielder_pos'].append(self.get_defensive_position(lineup_info[i][1]))

        teams_info['home_batter_ids'] = []
        teams_info['home_fielder_pos'] = []
        for i in range(9, 18):
            teams_info['home_batter_ids'].append(lineup_info[i][0])
            teams_info['home_fielder_pos'].append(self.get_defensive_position(lineup_info[i][1]))

        return game_result, teams_info

    def get_games_on_date(self, date, cursor):
        """
        Date looks like this: 1003 Assumes year of self.year
        Returns the game_id of all regular season games on that date
        """
        cursor.execute(
            "SELECT max(gameName) FROM gameDetail "
            "WHERE game_type='R' AND ind IN ('F', 'FR') AND"
            " year_id=%s AND date_id=%s "
            "GROUP BY LEFT(gameName, 28);" % (self.year, date))
        results = cursor.fetchall()
        return np.array(results)[:, 0].tolist()

    def create_pit_faced(self, date, cursor):
        # Create table pit_faced for this specific date
        #   basically a dictionary of the starting pitcher each player is facing
        query = ("CREATE TEMPORARY TABLE pit_faced AS "
                 "SELECT e.batter, e.pitcher, p.rl as pit_hand "
                 "FROM event_info_table AS e "
                 "JOIN players AS p ON e.gameName=p.gameName AND e.pitcher=p.id "
                 "WHERE p.game_position='P' AND e.date_id='%s' and e.year_id=%s "
                 "GROUP BY batter, pitcher;" % (date, self.year))
        cursor.execute(query)
        results = cursor.fetchall()

    def get_defensive_position(self, position):
        return self.defensive_position[position]
