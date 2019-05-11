#!/usr/bin/python

"""
Module to adjust batter rates stats for the relevant batter vs pitcher matchup.
"""

from . import utils

# league batting stats from 2012-2014
STATS = {'HR': 13778, 'TRIPLE': 2542, 'DOUBLE': 24495, 'SINGLE': 84805,
         'BB': 43367, 'HBP': 4682, 'SO': 110566, 'OUT': 268775}

# League stats for left handed batters from 2012-2014
L_STATS = {'HR': 5833, 'TRIPLE': 1342, 'DOUBLE': 10602, 'SINGLE': 37123,
           'BB': 20914, 'HBP': 1833, 'SO': 48046, 'OUT': 117488}

# League stats for right handed batters from 2012-2014
R_STATS = {'HR': 7945, 'TRIPLE': 1200, 'DOUBLE': 13893, 'SINGLE': 47682,
           'BB': 22453, 'HBP': 2849, 'SO': 62520, 'OUT': 151287}

# League stats for left handed batters against left handed pitchers from 2012-2014
L_L_STATS = {'HR': 908, 'TRIPLE': 218, 'DOUBLE': 1765, 'SINGLE': 7254,
             'BB': 3355, 'HBP': 550, 'SO': 10951, 'OUT': 22772}

# League stats for left handed batters against right handed pitchers from 2012-2014
L_R_STATS = {'HR': 4925, 'TRIPLE': 1124, 'DOUBLE': 8837, 'SINGLE': 29869,
             'BB': 17559, 'HBP': 1283, 'SO': 37095, 'OUT': 94716}

# League stats for right handed batters against left handed pitchers from 2012-2014
R_L_STATS = {'HR': 2947, 'TRIPLE': 441, 'DOUBLE': 5404, 'SINGLE': 16822,
             'BB': 9126, 'HBP': 691, 'SO': 20712, 'OUT': 53449}

# League stats for right handed batters against right handed pitchers from 2012-2014
R_R_STATS = {'HR': 4998, 'TRIPLE': 759, 'DOUBLE': 8489, 'SINGLE': 30860,
             'BB': 13327, 'HBP': 2158, 'SO': 41808, 'OUT': 97838}

LEAGUE_STATS = {'': STATS, 'R': R_STATS, ('R', 'R'): R_R_STATS,
                ('R', 'L'): R_L_STATS, 'L': L_STATS, ('L', 'R'): L_R_STATS,
                ('L', 'L'): L_L_STATS}


def get_splits_dict(league_stats, splits_stats):
    """
    Returns a dictionary of scalar values to multiply projections by in order
    to account for the relevant splits matchup (batter hand vs. pitcher hand)
    """
    normalized_league_stats = utils.normalize_dictionary(league_stats)
    normalized_splits_stats = utils.normalize_dictionary(splits_stats)

    splits_dict = {}
    for stat in splits_stats:
        splits_dict[stat] = normalized_splits_stats[stat] / normalized_league_stats[stat]

    return splits_dict


# TODO: Should adjustments be of league stats or same handedness league stats?
# TODO: Explicitly enter splits scalars
#       Adjust to R/L specific league stats, not overall league stats
SPLITS_SCALAR = {('R', 'R'): get_splits_dict(R_STATS, R_R_STATS),
                 ('R', 'L'): get_splits_dict(R_STATS, R_L_STATS),
                 ('L', 'R'): get_splits_dict(L_STATS, L_R_STATS),
                 ('L', 'L'): get_splits_dict(L_STATS, L_L_STATS)}


def adjust_splits(info, neutral_projection):
    """
    Adjusts a projection for the hands of the batter and the pitcher in the
    relevant matchup.
    """
    if info['pitcher_role'] == 'Reliever':
        return neutral_projection

    split_projection = {}
    for stat in neutral_projection:
        key = (info['bat_hand'], info['opp_pitcher_hand'])
        split_projection[stat] = neutral_projection[stat] * SPLITS_SCALAR[key][stat]

    return split_projection


def get_league_stats(info):
    """
    Returns the relevant league average splits stats.
    Assumes that switch hitters have bat handedness already set to either R or L
    """
    key = (info['bat_hand'], info['opp_pitcher_hand'])

    return LEAGUE_STATS[key].copy()
