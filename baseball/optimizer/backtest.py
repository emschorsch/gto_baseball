#!/usr/bin/python

from baseball.stats import stat_loader
from . import optimizer
from .player_customizations import PlayerCustomizations
from .historical_game_details import HistoricalGameDetails

import numpy as np

import argparse
import random
import csv


def backtest(year, num_simulations=50):
    """
    For each day in <year> builds the optimal lineup.
    Simulates each game <num_simulations> times to get player projections
    Prints and outputs to csv the date, actual lineup score, and
        predicted lineup score.
    Assumes players can be picked from any game on a date but only the later
        game of a double header.
    """

    player_customizations = PlayerCustomizations(filename="Dummy")
    game_details = HistoricalGameDetails(year)
    data_handler = stat_loader.StatLoader(year, str(int(year) - 1), game_details)

    headers = ["date", "actual total", "predicted total", "var", "sal",
               "maj stack", "min stack"]
    training_data = [headers]
    baseline_data = [headers]

    dates = data_handler.get_relevant_dates()
    random.seed(10)  # So we get the same games each time
    dates = random.sample(dates, int(len(dates)*.7))
    dates.sort()

    for date in dates:
        player_data, _ = optimizer.prepare_player_data(year, date)

        player_predictions, cov_dict, pitcher_stats = optimizer.build_predictions(
            data_handler, player_data, date, num_simulations, player_customizations)

        baseline_predictions = generate_baseline_predictions(player_predictions)

        baseline_lineups = optimizer.build_optimal_lineups(player_data,
                                                           baseline_predictions)
        optimal_lineups = optimizer.build_optimal_lineups(player_data, player_predictions)
        if optimal_lineups is None:
            continue

        # TODO: do we want in dictionary or list form
        metrics = optimizer.append_lineup_metrics(baseline_lineups,
                                                  baseline_lineups.index, cov_dict)
        baseline_data.append([date] + metrics)

        metrics = optimizer.append_lineup_metrics(optimal_lineups,
                                                  optimal_lineups.index, cov_dict)
        training_data.append([date] + metrics)

        if date[-1] == '4':
            print(date, metrics)

    output_file = "optimization_error%s_%s.csv" % (year, num_simulations)
    with open(output_file, "w") as f:
        writer = csv.writer(f)
        writer.writerows(training_data)

    print("done: \n", training_data[:20])
    temp = np.array(training_data[1:], dtype='float')
    print("25 %: actual: {} 25% predicted {} var {} sal {} maj_stack {} min_stack {}".format(
        *np.percentile(temp[:, 1:], q=25, axis=0).tolist()))
    print("medians: actual: {} median predicted {} var {} sal {} maj_stack {} min_stack {}".format(
        *np.median(temp[:, 1:], axis=0).tolist()))
    print("75 %: actual: {} 75% predicted {} var {} sal {} maj_stack {} min_stack {}".format(
        *np.percentile(temp[:, 1:], q=75, axis=0).tolist()))
    print("averages: actual: {} predicted: {} var {} sal {} maj_stack {} min_stack {}".format(
        *temp[:, 1:].sum(axis=0)/len(temp)))
    print("25 %: baseline: {} 25% baseline salary used {} var {} sal {} maj_stack {} min_stack {}".format(
        *np.percentile(np.array(baseline_data[1:], dtype='float')[:, 1:],
                       q=25, axis=0).tolist()))
    print("averages: baseline: {} baseline salary used {} var {} sal {} maj_stack {} min_stack {}".format(
        *np.array(baseline_data[1:],
                  dtype='float')[:, 1:].sum(axis=0)/len(temp)))

    return training_data


def generate_baseline_predictions(player_predictions):
    """Generates predictions as if we had no baseball knowledge

    :param player_predictions: Built by build_predictions. Has player info
    :type player_predictions: Pandas DataFrame
    :return: player_predictions but with the DK pts pred column
            set to the baseline predictions

    The goal is to generate baseline lineup to compare our optimized lineups to
    With no outside knowledge the best one can do is use DK salary.
    This method assumes the salary is proportional to the expected points
        and so uses salary as the predicted DK pts.
    The method isn't completely ignorant since player_predictions has already
        restricted to players that actually played in the game
    """
    baseline_predictions = player_predictions.copy()
    baseline_predictions["DK pts pred"] = baseline_predictions["DK sal"]
    baseline_predictions["custom DK pts pred"] = baseline_predictions["DK sal"]
    return baseline_predictions


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Using statistics from <year> produces '
                    'an optimal lineup for <date>')
    parser.add_argument("--year", nargs='?', default='2014',
                        help="the year to collect data for")
    parser.add_argument("--num_simulations", nargs='?', default='1000',
                        type=int, help="number of times to simulate each game")
    args = parser.parse_args()

    backtest(args.year, args.num_simulations)
