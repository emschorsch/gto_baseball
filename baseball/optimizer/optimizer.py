#!/usr/bin/python

import pandas as pd

from baseball.simulator.simulator import simulate
from baseball.simulator import utils

from baseball.stats import stat_loader
from . import linearsolver
from .historical_game_details import HistoricalGameDetails
from .dk_game_details import DKGameDetails
from .player_customizations import PlayerCustomizations

import argparse
import os
import pickle

pd.set_option("display.max_columns", 35)
pd.set_option("display.max_rows", 30)
pd.options.display.float_format = '{:,.3f}'.format


rotoguru_pos_dict = {ord('1'): 'P',
                     ord('2'): 'C',
                     ord('3'): '1B',
                     ord('4'): '2B',
                     ord('5'): '3B',
                     ord('6'): 'SS',
                     ord('7'): 'OF',
                     }


def build_predictions(data_handler, player_data, date, num_simulations=1000,
                      player_customizations=None):
    """
    Uses data_handler to project dfs scores for <date>

    :param player_data: player info for <date> like DK salary, team etc.
    :type player_data: Pandas DataFrame
    Stores projected dfs points for each player in data frame with other info
    Returns data frame of player info and points
    """
    games_info = None
    pitcher_stats = None

    cov_dict = {}
    # Loops through each game on <date>
    for game_result, teams_info in data_handler.get_games([date]):
        player_customizations.adjust_rates(teams_info['home_team'])
        player_customizations.adjust_rates(teams_info['away_team'])

        results = simulate(teams_info['home_team'],
                           teams_info['away_team'], num_simulations)
        predictions = results['avg_results']
        cov_dict.update(results['cov_dict'])

        away_rates = teams_info['away_team'].team_info_dataframe()
        away_info = pd.concat([away_rates, predictions["away_playerstats"]], axis=1)
        away_info.ix[9, "DK pts pred"] = predictions['away_pitcher'].get_stat('dk_score')

        home_rates = teams_info['home_team'].team_info_dataframe()
        home_info = pd.concat([home_rates, predictions["home_playerstats"]], axis=1)
        home_info.ix[9, "DK pts pred"] = predictions['home_pitcher'].get_stat('dk_score')

        home_pitcher_stats = pd.Series(predictions['home_pitcher'].stats)
        home_pitcher_id = teams_info['home_team'].starter.pid
        away_pitcher_stats = pd.Series(predictions['away_pitcher'].stats)
        away_pitcher_id = teams_info['away_team'].starter.pid
        pitchers = pd.DataFrame([home_pitcher_stats, away_pitcher_stats],
                                index=[home_pitcher_id, away_pitcher_id])

        info = away_info.append(home_info)
        info["game_id"] = game_result["game_id"]

        pitcher_info = info.loc[9]
        # To handle NL: Remove batting stats for both home and away pitchers.
        batter_info = info[~info["MLB_ID"].isin(pitcher_info["MLB_ID"])]

        if games_info is None:
            games_info = batter_info.append(pitcher_info, ignore_index=True)
            pitcher_stats = pitchers
        else:
            games_info = games_info.append([batter_info, pitcher_info],
                                           ignore_index=True)
            pitcher_stats = pitcher_stats.append(pitchers)

    player_info_cols = ["MLB_ID", "Name", "DK posn", "DK sal"]
    pitcher_stats = pitcher_stats.reset_index().rename(columns={"index": "MLB_ID"})
    pitcher_stats = pitcher_stats.merge(player_data[player_info_cols], on="MLB_ID")
    # TODO: This doesn't include the custom adjustments. Add those in
    pitcher_stats["pts per Dollar"] = pitcher_stats["dk_score"]/pitcher_stats["DK sal"]

    prediction_data = games_info.merge(player_data[player_info_cols])
    prediction_data["MLB_ID"] = prediction_data["MLB_ID"].astype(int)
    prediction_data["custom DK pts pred"] = prediction_data["DK pts pred"]
    prediction_data["custom pts per Dollar"] = -1

    cols = ["game_id", "Team", "Name", "MLB_ID", "DK sal", "DK posn",
            "DK posn orig", "DK pts pred", "custom DK pts pred",
            "custom pts per Dollar"] + prediction_data.columns[2:22].tolist()

    # Make two rows for multipos player
    prediction_data = split_multipos_players(prediction_data)

    return prediction_data[cols], cov_dict, pitcher_stats


def prepare_player_data(year, date):
    """Loads in player_data for <date> and handles doubleheaders

    :param year: expects yyyy form. The year that is being simulated
    :param date: expects mmdd form. Can have leading 0 or not.
    :type year: string
    :type date: string
    :return: The player data from <date> with the first game in
            every double header removed
            players ordered by Team and then bat order
    """
    file_format = "fixtures/rotoguru_salaries/dk/{}/playerInfo_{}.csv"
    filename = file_format.format(year, date.lstrip("0"))
    if not os.path.isfile(filename):
        # then try to load DK lineup and game details
        game_details = DKGameDetails(year, date)
        player_data = game_details.prepare_player_data()
        return player_data, game_details

    player_data = pd.read_csv(filename, sep=";")

    dblhdr_teams = set(player_data["Team"][player_data["dblhdr"] == 2])

    # Removes players without position information
    player_data = player_data[pd.notnull(player_data["DK posn"])].copy()

    # For all double headers remove the first game from consideration
    # TODO: is this a source of doubleheader bugs?
    player_data = player_data[~(player_data["Team"].isin(dblhdr_teams) &
                              pd.isnull(player_data["dblhdr"]))]
    # TODO: rename DK Sal to Salary no reason to not have this be generic for
    # when we eventually switch over to handling FD as well

    assert((player_data['DK posn'] < 100).all())

    # cast to int first to avoid including decimals when converting to string
    player_data["DK posn"] = player_data["DK posn"].astype(int).astype(str)
    player_data["DK posn"] = player_data["DK posn"].str.join("/")
    player_data["DK posn"] = player_data["DK posn"].str.translate(table=rotoguru_pos_dict)

    game_details = HistoricalGameDetails(year)
    return player_data, game_details


@utils.timing
def optimize(year, date, num_lineups=3, num_simulations=1000, resimulate=True):
    """
    Collects player stats from <year> and uses to project scores on <date>
    Then optimizes over those scores using draftking rules
    Returns the top <num_lineups>, returns None if error
    """
    player_customizations = PlayerCustomizations()

    # Contains all the relevant player info for that day:
    #       salary, id, DK posn, DK pts etc.
    player_data, game_details = prepare_player_data(year, date)

    base_path = os.path.dirname(os.path.abspath(__file__))
    player_prediction_file = base_path + "/player_predictions.pickle"
    cov_dict_file = base_path + "/cov_dict.pickle"

    # TODO: have it check if the pickled files have the same paramaters
    # otherwise don't rerun
    if resimulate or not os.path.isfile(player_prediction_file):
        data_handler = stat_loader.StatLoader(year, str(int(year) - 1), game_details)
        player_predictions, cov_dict, pitcher_stats = build_predictions(
            data_handler, player_data,
            date, num_simulations,
            player_customizations)

        pitcher_stats.to_csv("predicted_pitcherscores_{}_{}sims.csv".format(date, num_simulations))

        with open(player_prediction_file, "wb") as f:
            pickle.dump(player_predictions, f)
        with open(cov_dict_file, "wb") as f:
            pickle.dump(cov_dict, f)
    else:
        with open(player_prediction_file, "rb") as f:
            player_predictions = pickle.load(f)
        with open(cov_dict_file, "rb") as f:
            cov_dict = pickle.load(f)

        # TODO: Do we want to adjust_scores no matter what or only if resimulate?
        # For now no matter what. Maybe in future if decide it'll be easier to
        # allow adjustments directly on the file then we can write out in csvs
        # and do mods to that directly

    # Adjust predicted scores according to custom weights
    # This is used to express preference for or exclude certain players
    player_predictions = player_customizations.adjust_scores(player_predictions)
    player_predictions["custom pts per Dollar"] = player_predictions["custom DK pts pred"]/player_predictions["DK sal"]
    player_predictions.to_csv("predicted_playerscores_{}_{}sims.csv".format(date, num_simulations))

    # TODO: new flag if want to resimulate? Otherwise get from pickled file? do
    # we want pickled file or human readable files of csv for players and
    # cov_dict.
    # DO we want to add small random perturbation in linearsolver as well?

    predictions = build_optimal_lineups(player_data,
                                        player_predictions, num_lineups)
    if predictions is None:
        print("No results")
        return None
    # Remove lineup info from rows functioning as visual seperators
    predictions.loc[predictions["MLB_ID"].isnull(), "Lineup"] = None

    for lineup, indexes in predictions.groupby("Lineup").groups.items():
        append_lineup_metrics(predictions, indexes, cov_dict)

    predictions.to_csv("predicted_lineups_{}_{}sims.csv".format(date, num_simulations))

    if num_lineups <= 3:
        print(predictions)

    return predictions


def append_lineup_metrics(predictions, player_indexes, cov_dict):
    """Inserts the relevant lineup info in predictions for
        every player that's part of the lineup

    :param player_indexes: index into predictions for each player in the lineup
    :type player_indexes: iterable of 10 ints

    Returns lineup metrics:
        actual score of lineup, simulated score of lineup
        simulated variance of lineup score
        count of number of players in major stack
        count of number of players in minor stack
    Major stack: number of players on the team that is most represented
        in this lineup
    Minor stack: number of players on team that is second most represented
    """
    metric_dict = {}

    var = 0
    # Var(Lineup) = Var(Sum of player scores) = sum of all pairwise covariances
    # https://en.wikipedia.org/wiki/Variance#Sum_of_correlated_variables
    for i in player_indexes:
        for j in player_indexes:
            id1 = predictions.loc[i, "MLB_ID"]
            game1 = predictions.loc[i, "game_id"]
            pos1 = predictions.loc[i, "DK posn"]
            team1 = predictions.loc[i, "Team"]

            id2 = predictions.loc[j, "MLB_ID"]
            game2 = predictions.loc[j, "game_id"]
            pos2 = predictions.loc[j, "DK posn"]
            team2 = predictions.loc[j, "Team"]

            # Not in same game => independent => cov = 0
            if game1 != game2:
                var += 0
            # If pitcher should have cov calculated with everyone in game
            elif pos1 == 1 or pos2 == 1:
                var += cov_dict[id1][id2]

            # Batters on same team should have cov calculated
            elif team1 == team2:
                var += cov_dict[id1][id2]
            # Batters on opposing team treated as independent
            # TODO: Possible dependency factors we're ignoring:
            #   Headwinds, rained out games
            else:
                var += 0

    metric_dict['pred var'] = var

    metric_dict['tot sal'] = predictions.loc[player_indexes, "DK sal"].sum()
    metric_dict['actual total'] = predictions.loc[player_indexes, "DK pts"].sum()
    metric_dict['pred total'] = predictions.loc[player_indexes, "DK pts pred"].sum()

    # TODO: Should group by game_id as well if want to examine cross-team
    # correlations and their effect on scores
    # Major stack is tracked to allow analysis of whether optimizer is tending
    # to pick lineups with stacks
    stack_info = predictions.loc[player_indexes, "Team"].value_counts()[:2]
    metric_dict['maj_stack'], metric_dict['min_stack'] = stack_info

    metrics = ['actual total', 'pred total', 'pred var', 'tot sal',
               'maj_stack', 'min_stack']
    for metric in metrics:
        if metric not in predictions:
            predictions[metric] = None
        predictions.loc[player_indexes, metric] = metric_dict[metric]

    return [metric_dict[metric] for metric in metrics]


def build_optimal_lineups(player_data, player_predictions, num_lineups=1):
    """Generates the optimal lineups from the player projections

    :param player_data: misc player data like DK pts and salary
    :param player_predictions: player info and projections for points scored
    :param num_lineups: number of optimal lineups to generate
    :type player_data: Pandas DataFrame
    :type player_predictions: Pandas DataFrame
    :param num_lineups: int
    """
    optimal_lineups, status = linearsolver.optimizeLineup(player_predictions,
                                                          num_lineups)

    if status != "Optimal":
        print("status isn't optimal\n\t", status, optimal_lineups)
        return None

    player_data = player_data[["MLB_ID", "DK pts"]]

    # Add column <DK pts> for what players actually scored on <date>
    results = optimal_lineups.merge(player_data, on="MLB_ID", how="left")
    # Turn into category so that it sorts using our custom ordering: (P, C, ...)
    results["DK posn"] = results["DK posn"].astype("category").cat.set_categories(
        ['P', 'C', '1B', '2B', '3B', 'SS', 'OF'])
    return results.sort_values(by=['Lineup', 'DK posn'])


def split_multipos_players(player_data):
    """
    For each player that is eligible for multiple positions makes a new row
    Adds column ID_POS which is string concatenated MLB_ID + posn
    DK posn is a string delimited by '/':
        eg. eligible for SS and 1B means DK posn is 1B/SS
    Assumes players can only be eligible for a max of 2 positions
    Renames DK posn to DK posn orig.
    Adds the position that row represents into DK posn
    Makes ID_POS the index and returns the new dataframe
    """
    # If no eligible players for the day just return so it won't crash
    if len(player_data) == 0:
        player_data["DK posn orig"] = player_data["DK posn"]
        return player_data

    # Split Multi positions into seperate columns and then stack those to make
    # one row for each position a player is eligible for
    row_per_pos = pd.DataFrame(player_data["DK posn"].str.split('/').tolist()).stack()
    # The index of row_per_pos and player_data are now lined up
    row_per_pos.index = row_per_pos.index.droplevel(-1)
    row_per_pos.name = "DK posn"

    player_data = player_data.rename(columns={"DK posn": "DK posn orig"})
    merged_data = player_data.join(row_per_pos)

    merged_data["ID_POS"] = merged_data["MLB_ID"].astype(str) + merged_data["DK posn"]

    valid_positions = set(['P', 'C', '1B', '2B', '3B', 'SS', 'OF'])
    if not set(merged_data["DK posn"].unique()).issubset(valid_positions):
        valid_pos_players = merged_data["DK posn"].isin(valid_positions)
        print("NOT VALID POSITIONS\n", merged_data[~valid_pos_players]["DK posn"].unique())
        print(merged_data[~valid_pos_players])
        raise AssertionError("Invalid positions")
    return merged_data.set_index("ID_POS")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Using statistics from <year> produces '
                    'an optimal lineup for <date>')
    parser.add_argument("--year", nargs='?', default='2014',
                        help="the year to collect data for")
    parser.add_argument("--date", nargs='?', default='0904',
                        help="the date to produce optimal lineups for")
    parser.add_argument("--num_lineups", nargs='?', default='3', type=int,
                        help="the number of optimal lineups to produce")
    parser.add_argument("--num_simulations", nargs='?', default='1000',
                        type=int, help="number of times to simulate each game")
    parser.add_argument("--resimulate", nargs='?', default='true',
                        help="whether to resimulate the games")

    args = parser.parse_args()

    if args.resimulate.lower() == "true":
        optimize(args.year, args.date, args.num_lineups, args.num_simulations)
    elif args.resimulate.lower() == "false":
        optimize(args.year, args.date, args.num_lineups, args.num_simulations,
                 resimulate=False)
    else:
        print("ERROR in args.resimulate. Input was: ", args.resimulate.lower())
