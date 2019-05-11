#!/usr/bin/python
from __future__ import print_function

from baseball.stats import stat_loader
from baseball.stats import stats
from .historical_game_details import HistoricalGameDetails

from baseball.simulator.simulator import simulate
from baseball.simulator import batting_rates_index as br

import time
import csv
import argparse
import os

import numpy as np
import pandas as pd

pd.set_option("display.max_columns", 25)
pd.set_option("display.max_rows", 10)
pd.options.display.float_format = '{:,.3f}'.format

directory = os.path.dirname(os.path.abspath(__file__)) + '/../../fixtures/'
id_map = pd.read_csv(directory + "sfbb_playeridmap.csv", dtype="str")
id_map = id_map[["MLBID", "PLAYERNAME"]]


def _get_prediction_errors(year, data_handler, num_simulations):
    """
    Get predictions and save it to a csv file
    """
    print("Starting predictions", year, time.time())

    # errors is the list that keeps all the statistics for the csv file
    errors = [["home", "away", "home_score", "away_score", "prob_home_win",
               "pred_home_score", "pred_away_score"]]

    pred_playerstats = None
    pred_pitcherstats = None
    stat_dict = {}
    iteration = 0
    # TODO: would threading so collecting next game's
    # statistics at the same time as simulating speed this up?

    # Loops through each game in the season
    for game_result, teams_info in data_handler.get_games(dates=[]):
        if iteration % 100 == 0:
            print("on game# ", iteration, " time is: ", time.time())
        iteration += 1

        results = simulate(teams_info['home_team'],
                           teams_info['away_team'], num_simulations)
        predictions = results['avg_results']
        prob_home_win = predictions['prob_home_win']

        pred_playerstats, pred_pitcherstats = _dictify_predicted_stats(pred_playerstats,
                                                    pred_pitcherstats,
                                                    predictions, teams_info)

        track_season_stats(stat_dict, game_result, predictions)

        data = [game_result['home_team_id'], game_result['away_team_id'],
                game_result['home_team_runs'], game_result['away_team_runs'],
                prob_home_win,
                predictions['home_score'], predictions['away_score']]
        errors.append(data)

    output_file = "simulation_error%s_%s.csv" % (year, num_simulations)
    with open(output_file, "w") as f:
        writer = csv.writer(f)
        writer.writerows(errors)

    pred_obs_stat_corr(stat_dict)

    stat_dict['pred_stats'] /= float(iteration)
    obs = stat_dict['obs_player_stats'].export_as_dataframe()
    pred = pred_playerstats.export_as_dataframe()
    predpitcher = merge_stats(pred_pitcherstats.export_as_dataframe())

    stats = obs.merge(pred, how="outer", on=["pid", "team"], suffixes=["", "_pred"])
    stats["pid"] = stats["pid"].astype("int")  # bug in outer merge changes pid type
    stats = merge_stats(stats)
    stats.to_csv("validator_stats%s_%s.csv" % (year, num_simulations),
                 float_format='%.2f')
    predpitcher.to_csv("validator_pitcherstats%s_%s.csv" % (year, num_simulations),
                       float_format='%.2f')

    print("\t\tAccumulated validator player stats:\n", stats)
    print("\t\tAccumulated validator pitcher stats:\n", predpitcher)
    print("\t\tpredicted Game stats:\n", stat_dict['pred_stats'])
    print("num_games:", iteration)

    return stat_dict['pred_stats']


def _dictify_predicted_stats(prev_stats, prev_pitcherstats, predictions, info):
    """
    Handles the logic for putting the simulated player stats into prev_stats
    Decided to make the main function cleaner at the expense of having the
        custom logic about predictions and info in 2 places
    """
    if prev_stats is None:
        prev_stats = stats.StatTracker(
            key_labels=['pid', 'team'],
            value_labels=list(predictions['home_playerstats'].columns)+["PA"])
        prev_pitcherstats = stats.StatTracker(
            key_labels=['pid', 'team'],
            value_labels=list(predictions['home_pitcher'].stats.keys())+["num_games"])

    for team in ['home', 'away']:
        lineup_ids = info[team+'_batter_ids']
        team_id = info[team+'_team_id']
        player_stats = predictions[team+'_playerstats']
        player_stats["PA"] = player_stats.loc[:, br.batting_events].sum(axis=1)

        for pos in range(9):
            key = (lineup_ids[pos], team_id)
            prev_stats[key] += np.array(player_stats.loc[pos, :])

        # Add pitcher stats
        pitcher_key = (info[team+'_pitcher_id'], team_id)
        pitcher_stats = predictions[team+'_pitcher'].stats
        pitcher_stats['num_games'] = 1
        pitcher_array_stats = []
        for stat in prev_pitcherstats.value_labels:
            pitcher_array_stats.append(pitcher_stats[stat])

        prev_pitcherstats[pitcher_key] += np.array(pitcher_array_stats)

    return prev_stats, prev_pitcherstats


def merge_stats(stats_frame):
    """
    Takes in a StatsTracker object and merges it with id_map
    """
    stats_frame["pid"] = stats_frame["pid"].astype(str)
    merged = id_map.merge(stats_frame, left_on="MLBID", right_on="pid")
    del merged["MLBID"]
    return merged.sort_values(by="pid")


def track_season_stats(stat_dict, game_result, predictions):
    """
    Takes the observed and predicted player results and aggregates them to
        get game level stats that are tracked over the season
    Intent is to allow correlational analysis between predicted and observed
        stats and to see how accurate the simulations are on a game level.
    """
    stat_names = predictions['home_playerstats'].columns.tolist()
    del stat_names[stat_names.index("DK pts pred")]

    obs_stats = game_result['tracked_stats']
    if 'pred_stats' not in stat_dict:  # first time being called so setup dict
        stat_dict['pred_stats'] = predictions
        stat_dict['obs_player_stats'] = obs_stats

        # Prepend column names to list so headers are there after export_to_csv
        stat_dict['home_obs_stats'] = [stat_names]
        stat_dict['away_obs_stats'] = [stat_names]
        stat_dict['home_pred_stats'] = [stat_names]
        stat_dict['away_pred_stats'] = [stat_names]
    else:
        stat_dict['pred_stats'] += predictions
        stat_dict['obs_player_stats'] += obs_stats

    # Sum player stats for each team
    team_stats = obs_stats.export_as_dataframe().groupby("team").sum()[stat_names]
    # Track predicted and observed results by game for later correlational analysis
    stat_dict['home_obs_stats'].append(
        team_stats.loc[game_result['home_team_id']].tolist())
    stat_dict['away_obs_stats'].append(
        team_stats.loc[game_result['away_team_id']].tolist())
    stat_dict['home_pred_stats'].append(
        predictions['home_playerstats'].sum()[stat_names].tolist())
    stat_dict['away_pred_stats'].append(
        predictions['away_playerstats'].sum()[stat_names].tolist())

    return stat_dict


def pred_obs_stat_corr(stat_dict):
    """
    Prints out correlations between observed and predicted stats on a game level
    These include RUN, RBI, hit types, BB, OUT, PA, SB stats
    """
    stat_names = stat_dict['home_obs_stats'][0]
    # Track stat correlations in dataframe of 2 rows to make easier to read
    stat_corrs = pd.DataFrame(columns=stat_names, index=['home', 'away'])

    # We compute and store the correlation of each stat in stat_corrs
    # This is corr across the league for stat totals in each game
    # We treat home and away stats separately to account for home park adv.
    for team_type in ['home', 'away']:
        obs = stat_dict[team_type + '_obs_stats']
        pred = stat_dict[team_type + '_pred_stats']
        obs_headers = obs.pop(0)
        pred_headers = pred.pop(0)
        obs = pd.DataFrame(obs, columns=obs_headers)
        pred = pd.DataFrame(pred, columns=pred_headers)

        for stat in obs_headers:
            stat_corrs.loc[team_type, stat] = obs[stat].corr(pred[stat])

    print("\ngame stat correlations:\n", stat_corrs)


def simulate_year(year, num_simulations, train_on_test='false'):
    """
    Simulates the <year> season
    Each game is simulated <num_simulations> times
    Predictions are written to simulation_error<year>_<num_simulations>.csv
    """
    if train_on_test.lower() == 'false':
        train_year = str(int(year) - 1)
    else:
        train_year = str(year)
    game_details = HistoricalGameDetails(year)
    data_handler = stat_loader.StatLoader(year, train_year, game_details)
    _get_prediction_errors(year, data_handler, num_simulations)


def main():
    parser = argparse.ArgumentParser(description='Simulates a given year.')
    parser.add_argument("--year", nargs='?', default='2014',
                        help="the year to simulate")
    parser.add_argument("--num_simulations", nargs='?', type=int, default=100,
                        help="number of times to simulate each game")
    parser.add_argument("--train_on_test", nargs='?', default='false',
                        help="train and test on same year")
    args = parser.parse_args()

    return simulate_year(args.year, args.num_simulations, args.train_on_test)

if __name__ == "__main__":
    results = main()
