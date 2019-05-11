#!/usr/bin/python

"""
Module to read and organize fangraphs Depth Charts rest of season player
projections for batters and pitchers.
"""

from . import park_factors as pf

import pandas as pd

import os.path
import sys

PROJECTION_YEAR = "2016"

# league rookie stats from 2012-2014
ROOKIE_STATS = {'HR': 2599, 'TRIPLE': 641, 'DOUBLE': 4805, 'SINGLE': 17174,
                'BB': 8296, 'HBP': 854, 'SO': 24030, 'OUT': 52220}

# league starting pitcher hitting stats from 2012-2014
PITCHER_STATS = {'HR': 60, 'TRIPLE': 20, 'DOUBLE': 276, 'SINGLE': 1429,
                 'BB': 491, 'HBP': 43, 'SO': 5867, 'OUT': 7902}

# league pinch hitter stats from 2012-2014
PINCH_HITTER_STATS = {'HR': 499, 'TRIPLE': 103, 'DOUBLE': 953, 'SINGLE': 3632,
                      'BB': 2228, 'HBP': 265, 'SO': 6922, 'OUT': 12323}

# league rookie pitcher pitching stats from 2013-2014
ROOKIE_PITCHER_STATS = {'HR': 1030, 'TRIPLE': 199, 'DOUBLE': 1946, 'SINGLE': 6583,
                        'BB': 3637, 'HBP': 371, 'SO': 8131, 'OUT': 20613,
                        'H': 9758, 'IP': 6871}

directory = os.path.dirname(os.path.abspath(__file__)) + '/../../'


def merge_player_ids(id_map_name, projections_name, unmapped_projections_name):
    id_map = pd.read_csv(id_map_name, dtype="str")
    id_map = id_map[["MLBID", "RETROID", "PLAYERNAME", "IDFANGRAPHS"]]
    unmapped_projections = pd.read_csv(unmapped_projections_name)
    projections = unmapped_projections.merge(id_map, left_on="playerid",
                                             right_on="IDFANGRAPHS",
                                             how="left", indicator=True)
    print("\n", (projections["_merge"] == "left_only").sum(), " zips projections unmapped!!\n")
    projections[projections["_merge"] == "both"].to_csv(projections_name)

if(PROJECTION_YEAR != '2016'):
    print("WARNING! Projections are from year:", PROJECTION_YEAR)
    user_input = input("Enter 'c' to continue. ")
    if user_input != 'c':
        print("Closing simulator")
        sys.exit()

mapped_hitters_file = (directory + "mapped_hitters_%s.csv" % PROJECTION_YEAR)
mapped_pitchers_file = (directory + "mapped_pitchers_%s.csv" % PROJECTION_YEAR)

id_map_filename = directory + "fixtures/sfbb_playeridmap.csv"

orig_hitters_file = (directory + "depthcharts_hitters_%s.csv" % PROJECTION_YEAR)
orig_pitchers_file = (directory + "depthcharts_pitchers_%s.csv" % PROJECTION_YEAR)

merge_player_ids(id_map_filename, mapped_hitters_file, orig_hitters_file)
merge_player_ids(id_map_filename, mapped_pitchers_file, orig_pitchers_file)


def load_projections(filename):
    # TODO: make sure projections have been updated in past day like player_cust
    if not os.path.isfile(filename):
        print("ERRROR!! no file: ", filename)
        return None

    projections = pd.read_csv(filename)

    return projections


def load_hitter_projections(filename):
    projections = load_projections(filename)

    column_mapping = {'2B': 'DOUBLE', '3B': 'TRIPLE'}
    projections.rename(columns=column_mapping, inplace=True)

    # Deduce SINGLES from Hits as H - (2B + 3B + HR)
    projections["SINGLE"] = projections["H"] - projections[["DOUBLE", "TRIPLE", "HR"]].sum(axis=1)
    # NOTE: SO are a seperate stat so OUT doesn't include them
    #       Now the stat_dict contains only mutually exclusive events
    projections["OUT"] = projections["AB"] - projections["H"] - projections['SO']
    return projections


def load_pitcher_projections(filename):
    projections = load_projections(filename)

    # Deduces OUTS as 3*IP - SO
    # NOTE: SO are a seperate stat so OUT doesn't include them
    projections['OUT'] = 3*projections['IP'] - projections['SO']

    return projections

hitter_projections = load_hitter_projections(mapped_hitters_file)
pitcher_projections = load_pitcher_projections(mapped_pitchers_file)
# Add hit by pitch column to pitcher projections
pitcher_projections['HBP'] = 0


def get_player_projections(mlb_id, stat_names, projection_type):
    # TODO: this method takes about 1/8 of stat_loader time when running 70 sims
    # Almost no execution time in get_projection_average, so it's all the slow
    # pandas loading
    if projection_type == 'hitter':
        player_data = hitter_projections[hitter_projections["MLBID"] == mlb_id]
    elif projection_type == 'pitcher':
        player_data = pitcher_projections[pitcher_projections["MLBID"] == mlb_id]
    else:
        print('Error! Invalid projection_type: %s' % projection_type)

    if len(player_data) == 0:
        return None

    assert(len(player_data) == 1), player_data
    # By returning and working with a dictionary instead of a DataFrame
    #   We cut projections_average from 37 seconds to 7 seconds
    # Restrict the DataFrame to only the stats we care about i.e. stat_names
    stat_data = player_data.iloc[0][stat_names]
    return stat_data.to_dict()


def get_hitter_projection(info, stat_names):
    batter_projection = get_player_projections(info['mlb_id'], stat_names, 'hitter')

    if batter_projection is not None:
        # neutralize projections for batters home stadium
        batter_projection = pf.fangraphs_park_adjust_stats(batter_projection,
                                                           info,
                                                           neutralize=True,
                                                           pitcher=False)
    else:
        if info['is_pitcher']:
            batter_projection = PITCHER_STATS.copy()
        else:
            batter_projection = ROOKIE_STATS.copy()
            # Avoid printing the same error messgae multiple times
            if info['pitcher_role'] == 'Reliever':
                print('Error! No hitter projections: %s: %s not found' % (info['team_id'], info['mlb_id']))

    return batter_projection


def get_pitcher_projection(info, stat_names):
    pitcher_stat_names = stat_names + ['H', 'IP']

    pitcher_projection = get_player_projections(info['opp_pitcher_id'], pitcher_stat_names, 'pitcher')

    if pitcher_projection is not None:
        # neutralize projection for pitchers home stadium
        pitcher_projection = pf.fangraphs_park_adjust_stats(pitcher_projection,
                                                            info,
                                                            neutralize=True,
                                                            pitcher=True)
    else:
        # Avoid printing the same error message multiple times
        if info['bat_order'] == 0:
            print('Error! No pitcher projections: %s: %s not found' % (info['opp_team_id'], info['opp_pitcher_id']))
        pitcher_projection = ROOKIE_PITCHER_STATS.copy()

    return pitcher_projection


# TODO: Would it be better to model pitcher hit types as a function of cfip?
#       Or should we just use league average 1B, 2B, 3B distributions?
def infer_hit_types(pitcher_data, batter_data):
    """
    Uses batter and pitcher projections to estimate a pitchers distribution of
    hit types allowed.

    Pitcher projections only predict a pitcher's total home runs and total hits
    allowed. From this, we must infer the total number of singles, doubles, and
    triples a pitcher allows. We combine this number with the relevant batter's
    distribution of singles, doubles, and triples to predict the pitcher's
    appropriate distribution of hits. We utilize the batter's hit type
    distribution because batters are significantly more predictive of hit type
    outcome than pitchers for a given at bat.

    Arguments:
        pitcher_data {dict} -- park neutralized pitcher projections
        batter_data {dict} -- park neutralized batter projections

    Returns:
        {dict} -- updated park neutralized pitcher projections
    """
    num_base_hits = 0
    base_hit_types = ['SINGLE', 'DOUBLE', 'TRIPLE']
    for hit_type in base_hit_types:
        num_base_hits += batter_data[hit_type]

    for hit_type in base_hit_types:
        hit_type_prob = batter_data[hit_type] / num_base_hits
        pitcher_data[hit_type] = hit_type_prob * (pitcher_data['H'] - pitcher_data['HR'])

    del pitcher_data['IP']
    del pitcher_data['H']

    return pitcher_data
