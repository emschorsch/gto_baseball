#!/usr/bin/python
from __future__ import print_function

from . import stat_loader

from baseball.simulator.simulator import simulate

import time
import csv
import argparse


def simulate_year(year, num_simulations, num_games):
    """
    Simulates the first <num_games> games of <year>
    """
    dataHandler = stat_loader.StatLoader(year, str(int(year) - 1))
    print("Starting predictions", year, time.time())

    iteration = 0

    # Loops through each game in the season
    for game_result, teams_info in dataHandler.get_games(dates=[]):
        iteration += 1

        results = simulate(teams_info['home_team'],
                           teams_info['away_team'], num_simulations)

        output_file = "dk_scores_home_%s_%s.csv" % (iteration, num_simulations)
        with open(output_file, "w") as f:
            writer = csv.writer(f)
            writer.writerows(results['home_dk_scores'])

        output_file = "dk_scores_away_%s_%s.csv" % (iteration, num_simulations)
        with open(output_file, "w") as f:
            writer = csv.writer(f)
            writer.writerows(results['away_dk_scores'])

        if iteration == num_games:
            print("on game# ", iteration, " time is: ", time.time())
            break


def main():
    parser = argparse.ArgumentParser(description='Simulates a given year.')
    parser.add_argument("--year", nargs='?', default='2014',
                        help="the year to simulate")
    parser.add_argument("--num_simulations", nargs='?', type=int, default=5000,
                        help="number of times to simulate each game")
    parser.add_argument("--num_games", nargs='?', type=int, default=1,
                        help="number of games to simulate")
    args = parser.parse_args()

    return simulate_year(args.year, args.num_simulations, args.num_games)

if __name__ == "__main__":
    results = main()
