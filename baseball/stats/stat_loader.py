#!/usr/bin/python

"""
This file deals exclusively with historical stats.
Handles collection and tracking of observed stats from past seasons
"""

from __future__ import print_function

from tools.mysqldb import connect
import numpy as np
import random

from collections import defaultdict

from baseball.simulator import stat_index as st

from .stats import StatTracker
from . import stats_adjuster


TRACKED_STATS_LABELS = list(st.stats) + ["AB", "PA"] + \
    ("State{},"*8).format(*range(8)).split(',')[:-1]


class StatLoader:
    def __init__(self, year, train_year, game_details):
        """
        Stat loader will collect all stats from <train_year>
        <year> is the current season to be simulated.
        Statistics will be iteratively updated for <year> but without peeking
        """
        gameday_db = connect(host="localhost",  # your host, usually localhost
                             user="bbos",       # your username
                             passwd="bbos",     # your password
                             db="gameday")      # name of the data base

        # Gameday cursor allows execution of queries on gameday databse
        self.gameday_cur = gameday_db.cursor()

        retrosheet_db = connect(host="localhost",  # your host, often localhost
                                user="bbos",       # your username
                                passwd="bbos",     # your password
                                db="retrosheet")   # name of the data base

        # Retrosheet cursor allows execution of queries on retrosheet databse
        self.retrosheet_cur = retrosheet_db.cursor()

        self.game_details = game_details

        self.data_collected = False

        self.year = str(year)
        self.train_year = train_year
        self.prev_date = "0101"

        # Keys to stat dictionaries are mlb_ids
        # Values are dictionary of observed event counts
        self.bat_stats_starter = {}
        self.bat_stats_reliever = {}

        self._load_maps()

    def collect_data(self, condition):
        """
        Collects games that satisfy <condition>.
        <condition> goes in the SQL where clause and can condition on tables:
            events AS e and game_types
        Automatically restricts to regular season games
        """
        # Gets the relevant games
        # TODO: Remove duplicate games from server/locally
        # TODO: Fix boston duplicate game on 07/21/2012
        # TODO: Remove ARI duplicate game in Australia on 03/23/2014
        inner_query = (
            "CREATE TEMPORARY TABLE IF NOT EXISTS event_info_table_1 AS "
            "(SELECT gameName, pitcher, batter,"
            " if(`event` = 'Strikeout - DP', 'Strikeout', `event`) as outcome,"
            " UPPER(home_code) as stadium, stand as bat_hand,"
            " if(bat_team=UPPER(home_code), 'H', 'A') as bat_type, game_time,"
            " atbats.date_id, atbats.year_id "
            "FROM atbats "
            "JOIN gameDetail USING(gameName) "
            "WHERE game_type='R' AND ind IN ('F', 'FR') AND"
            " `event`!='Runner Out' AND `event` NOT LIKE '%%Interference' AND atbats.%s);"
            % condition)

        print("creating event_info_table ... ")
        self.gameday_cur.execute(inner_query)
        self.gameday_cur.fetchall()  # get result set to avoid Command out of sync error

        query = (
            "CREATE TEMPORARY TABLE IF NOT EXISTS event_info_table AS "
            "(SELECT e.*, IFNULL(pf.pf, 1) AS pf "
            "FROM event_info_table_1 AS e "
            "LEFT JOIN (SELECT * from park_factors WHERE year_id=%s) AS pf "
            "USING(stadium, bat_type, bat_hand, game_time, outcome));"
            % self.train_year)

        self.gameday_cur.execute(query)
        self.gameday_cur.fetchall()
        self.gameday_cur.execute("DROP TABLE IF EXISTS event_info_table_1;")
        self.gameday_cur.fetchall()

        self.data_collected = True

    def get_games(self, dates=[]):
        """
        Generator function that loops over dates in the form: mmdd
        If no dates are provided we randomly select 70% of games from <year>
        For each game that occurs on dates home_team and away_team objects
            are stored in a info dict along w/ other details and yielded
        """
        self._ensure_data_collected()

        # If no dates collect all games for <self.year>
        if len(dates) == 0:
            dates = self.get_relevant_dates()
            random.seed(10)  # So we get the same games each time
            dates = random.sample(dates, int(len(dates)*.7))

        # Dates must be in ascending order
        dates.sort()

        # TODO: for 70 sims and .03 of dates get_games takes 56 secs cumalative
        # of that 36 secs spend in _collect_pitcher_adjusted
        # 10 seconds spent in get_lineup_for_game (aka historical tracking)
        # 10 seconds spent in adjuster._prepare_team_object
        #   Of which 7.5 seconds spent in get_player_projections

        for date in dates:
            self._collect_park_and_pitcher_adjusted(date=date)

            # Then collect stats
            for game_id in self.game_details.get_games_on_date(date,
                                                               self.gameday_cur):
                results = self.get_lineup_for_game(game_id)
                if results is not None:
                    yield results
            self.prev_date = date

    def get_lineup_for_game(self, game_id):
        """
        For a given game returns a dictionary of relevant info:
            Each team's lineup, the fielders
            Each player's historical stats
        """
        self._ensure_data_collected()

        game_result, teams_info = self.game_details.game_info(game_id,
                                                              self.gameday_cur)

        if int(game_result['inning']) < 9:
            # TODO: Come back and account for this
            print("not enough innings", game_result['inning'], game_id)
            return  # Throw out games that don't finish

        self._prepare_tracked_stats(game_result, game_id)
        stats_adjuster.prepare_team_object(self, teams_info, 'home', 'H')
        stats_adjuster.prepare_team_object(self, teams_info, 'away', 'A')
        return game_result, teams_info

    def _prepare_tracked_stats(self, game_result, gameday_id):
        """
        Tracks stats by player and team for <game_id>
        Updates <info> with tracked_stats stored in the StatTracker class
        """
        # TODO: no reason to collect this game by game. Just do it once for all
        #   games that will be simulated
        # BAT_HOME_ID is 0 if visitor 1 if home. But not currently tracking.

        game_id = self._get_retrosheet_game_id(gameday_id)

        query = ("select bat_id, bat_team_id, rbi_ct AS {}, "
                 "IF(BAT_FATE_ID>3,1,0) AS {}, "
                 "IF(event_cd=20,1,0) AS {}, "
                 "IF(event_cd=21,1,0) AS `{}`, "
                 "IF(event_cd=22,1,0) AS {}, "
                 "IF(event_cd=23,1,0) AS {}, "
                 "IF(event_cd=3,1,0) AS {}, "
                 "IF(event_cd=14 OR event_cd=15,1,0) AS {},  "
                 "0 AS {}, 0 AS {}, "
                 "IF(bat_dest_id=0,1,0) AS `{}`, "
                 "IF(AB_FL='T', 1,0) AS {}, "
                 "IF(BAT_EVENT_FL='T', 1,0) AS {}, "
                 "IF(START_BASES_CD=0, 1,0) AS {}, "
                 "IF(START_BASES_CD=1, 1,0) AS {}, "
                 "IF(START_BASES_CD=2, 1,0) AS {}, "
                 "IF(START_BASES_CD=3, 1,0) AS {}, "
                 "IF(START_BASES_CD=4, 1,0) AS {}, "
                 "IF(START_BASES_CD=5, 1,0) AS {}, "
                 "IF(START_BASES_CD=6, 1,0) AS {}, "
                 "IF(START_BASES_CD=7, 1,0) AS {} "
                 "FROM events "
                 "WHERE BAT_EVENT_FL='T' and game_id='{}';"
                 ).format(*TRACKED_STATS_LABELS+[game_id])

        self.retrosheet_cur.execute(query)
        results = self.retrosheet_cur.fetchall()

        # Key is tuple of (player_id, team)
        #  value is array of counts corresponding to TRACKED_STATS_LABELS
        countDict = {}
        self._prepare_steal_stats(game_id, countDict)

        if len(results) == 0:
            print("no retrosheet results?: ", gameday_id)

        num_keys = 2
        for row in results:
            key = (self.get_mlb_id(row[0]), row[1])
            if key in countDict:
                countDict[key] += np.array(row[num_keys:])
            else:
                countDict[key] = np.array(row[num_keys:])

        tracked_stats = StatTracker(value_labels=TRACKED_STATS_LABELS,
                                    key_labels=['pid', 'team'])
        tracked_stats.update_from_dict(countDict)
        game_result["tracked_stats"] = tracked_stats

    def _prepare_steal_stats(self, game_id, countDict):
        """
        Helper function for _prepare_tracked_stats
        Updates countDict which is passed in to include steals and CS stats
        """
        # For each base update countDict for all the
        # players who stole or were caught stealing
        for base in [1, 2, 3]:
            # TODO: pickoffs are excluded but counted as CS by most sites
            query = ("select base{0}_run_id, bat_team_id, "
                     "IF(run{0}_sb_fl='T',1,0) AS sb, "
                     "IF(run{0}_cs_fl='T',1,0) AS cs "
                     "FROM events WHERE (run{0}_sb_fl='T' "
                     "OR (run{0}_cs_fl='T' and run{0}_pk_fl='F')"
                     ") and game_id='{1}';").format(base, game_id)
            self.retrosheet_cur.execute(query)
            results = self.retrosheet_cur.fetchall()
            for row in results:
                key = (self.get_mlb_id(row[0]), row[1])
                values = np.zeros(len(TRACKED_STATS_LABELS), dtype='int')
                values[TRACKED_STATS_LABELS.index("SB")] = row[1+1]
                values[TRACKED_STATS_LABELS.index("CS")] = row[1+2]
                if key in countDict:
                    countDict[key] += values
                else:
                    countDict[key] = values

    def _ensure_data_collected(self):
        """
        Checks if data is loaded.
            If not loads data with the default scheme
            of training on the past year
        """
        if not self.data_collected:
            self.collect_data("year_id IN (%s, %s)" % (self.train_year,
                                                       self.year))

    def _collect_park_and_pitcher_adjusted(self, date="0101"):
        """
        PREREQUISITES: Assumes event_info_table has been set up by collect_data
        Computes event statistics for each player and stores them for later
        Also loads mlb_id map for later use
        """
        # Dictionary to hold player stats. Key is player_id
        #   Value is dictionary of events and their counts
        starter_stats = self.bat_stats_starter
        reliever_stats = self.bat_stats_reliever

        self.gameday_cur.execute("DROP TABLE If exists pit_faced;")
        self.gameday_cur.fetchall()

        pss_table = "pitcher_similarity"
        pss_type = "cfip"

        # About 4x slower now that we're recomputing the whole player stats
        # every time. I'm surpised that it doesn't make a bigger difference.
        # Maybe limiting to only the players that are playing today makes a big
        # difference

        # TODO: make col indicating if pitcher is starter.
        #   Then have all pitchers and can handle relievers as well
        self.game_details.create_pit_faced(date, self.gameday_cur)

        # For each batter compute weighted sum for each hit_type.
        #   Gives greater weight to similar pitchers since those PAs are more
        #   representative. Adjusts AB for contextual park_factor.
        # The pitcher and park adjusted weight for each PA is the pitcher's
        #   similarity to the starting pitcher the batter will be facing on
        #   <date> divided by the relevant contextual park factor.
        # The park adjusted weight is 1 divided by the relevant park factor.
        # TODO: we do pss.{0} IS NOT NULL to handle a rookie pitcher. Make sure
        # that it can handle rookie pitcher correctly
        query = ("SELECT e.batter, e.outcome,"
                 " SUM(pss.{0}/e.pf) AS pit_park_adj,"
                 " SUM(1/e.pf) AS park_adj "
                 "FROM pit_faced "
                 "JOIN event_info_table AS e USING(batter) "
                 "JOIN {1} AS pss ON pss.pit1=pit_faced.pitcher AND"
                 " pss.pit2=e.pitcher AND pss.{0} IS NOT NULL "
                 "WHERE (e.year_id={2} OR (e.year_id={3} AND e.date_id<{4})) "
                 "GROUP BY batter, outcome;").format(pss_type, pss_table,
                                                     self.train_year,
                                                     self.year, date)
        self.gameday_cur.execute(query)
        results = self.gameday_cur.fetchall()

        # populate the player_stats dictionary with the returned event counts
        counting_stats = ["Single", "Double", "Triple", "Home Run", "Strikeout",
                          "Walk", "Intent Walk", "Hit By Pitch"]
        for row in results:
            # row[0] is mlb_id
            if row[0] not in starter_stats:
                starter_stats[row[0]] = defaultdict(float)  # Returns 0 by default
                reliever_stats[row[0]] = defaultdict(float)  # Returns 0 by default
            # row[1] is the outcome type
            # row[2] is park and similarity weighted basket of counts
            # row[3] is park_adjusted pitcher neutral counts aka 'reliever'
            if row[1] in counting_stats:
                starter_stats[row[0]][row[1]] += float(row[2])
                reliever_stats[row[0]][row[1]] += float(row[3])
            else:
                starter_stats[row[0]]['Out'] += float(row[2])
                reliever_stats[row[0]]['Out'] += float(row[3])

        return starter_stats, reliever_stats

    def get_player_stats(self, mlb_id, role='Starter'):
        """
        Retrieves player stats collected by get_all_stats
        Replaces unseen players with dict of all 0s
        """
        self._ensure_data_collected()

        if role == 'Starter':
            stats = self.bat_stats_starter
        else:
            stats = self.bat_stats_reliever

        if mlb_id in stats:
            results = stats[mlb_id]
        else:  # player is unseen, assume a rookie, and return 0s
            return {'HR': 0, 'TRIPLE': 0, 'DOUBLE': 0, 'SINGLE': 0,
                    'BB': 0, 'HBP': 0, 'SO': 0, 'OUT': 0}
        stat_dict = {'HR': results['Home Run'], 'TRIPLE': results['Triple'],
                     'DOUBLE': results['Double'], 'SINGLE': results['Single'],
                     'SO': results['Strikeout'], 'HBP': results['Hit By Pitch'],
                     'BB': results['Walk'] + results['Intent Walk'],
                     'OUT': results['Out']}

        # NOTE: including SF and other non AB PAs.
        return stat_dict

    def _load_maps(self):
        """
        Loads mlb_ids for all players that might be encountered
        """
        id_map = {}
        bat_hand = {}
        pit_hand = {}

        # If encountered, latest_seen must be at least train_year
        #  and earliest seen must be at least year
        self.retrosheet_cur.execute(
            "SELECT retrosheet_id, mlb_id, BAT_HAND_CD, PIT_HAND_CD "
            "FROM id_map WHERE earliest_seen <= %s AND latest_seen >= %s;"
            % (self.year, self.train_year))
        players = self.retrosheet_cur.fetchall()
        for row in players:
            id_map[row[0]] = row[1]
            if row[2] is not None:
                bat_hand[row[1]] = row[2]
            if row[3] is not None:
                pit_hand[row[1]] = row[3]

        self.id_map = id_map
        self.bat_hand = bat_hand
        self.pit_hand = pit_hand

    def get_mlb_id(self, player_id):
        return int(self.id_map[player_id])

    def get_pitcher_hand(self, pitcher_id):
        return self.pit_hand[str(pitcher_id)]

    def get_batter_hand(self, batter_id):
        return self.bat_hand[str(batter_id)]

    def get_all_games(self):
        """
        Returns all games in <self.year>
        """
        self.gameday_cur.execute(
            "SELECT gameName FROM gameDetail "
            "WHERE game_type='R' AND ind IN ('F', 'FR') AND year_id=%s;"
            % self.year)
        results = self.gameday_cur.fetchall()
        return np.array(results)[:, 0].tolist()

    def get_relevant_dates(self):
        """
        Returns all the dates on which regular season games are played
        Returns in ascending order by Date
        """
        self.gameday_cur.execute(
            "SELECT distinct(date_id) "
            "FROM gameDetail "
            "WHERE game_type='R' AND ind IN ('F', 'FR') and year_id=%s "
            "ORDER BY date_id;" % self.year)
        results = self.gameday_cur.fetchall()
        return np.array(results)[:, 0].tolist()

    def _get_retrosheet_game_id(self, gameName):

        home_team = gameName[22:25].upper()
        year = gameName[4:8]
        month = gameName[9:11]
        day = gameName[12:14]
        index = gameName[-1]
        if gameName[-1] == '1':
            index = '0'
        game_id = home_team + year + month + day + index

        return game_id
