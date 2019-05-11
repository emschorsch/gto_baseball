#!/usr/bin/python

"""
This file loads in the fangraphs park factors and our custom in house park
factors as dictionaries. It also contains the functions to adjust stat
dictionaries to make them either park neutral or park specific.
"""

from tools.mysqldb import connect
import pandas as pd
import operator as op


def load_park_factors(db, table):
    """

    Load the park factors from MySQL gameday database into dictionaries

    Arguments:
        db {Connect object} -- A MySQLdb Connection object
        table {str} -- The name of the table to collect the park factors from

    Returns:
        [dict] -- A dictionary of park factors. Keys are relevant conditions:
                  stadiums, bat_hand, year, etc.
    """
    query = ("SELECT * FROM %s;" % table)
    pf = pd.read_sql(query, db)

    if 'num_pas' in pf.columns:
        del pf['num_pas']
    pf.loc[pf['outcome'] == 'Home Run', 'outcome'] = 'HR'
    pf.loc[pf['outcome'] == 'Strikeout', 'outcome'] = 'SO'
    pf.loc[pf['outcome'] == 'Walk', 'outcome'] = 'BB'
    pf['outcome'] = pf['outcome'].str.upper()

    keys = pf.columns.tolist()
    keys.remove('pf')
    grouped = pf.groupby(keys)

    pf_dict = {}
    for key in dict(list(grouped)).keys():
        pf_dict[key] = float(grouped.get_group(key)['pf'])

    return pf_dict


gameday = connect(host="localhost",  # your host, usually localhost
                  user="bbos",       # your username
                  passwd="bbos",     # your password
                  db="gameday")      # name of the data base
fangraphs_pf = load_park_factors(gameday, table='fangraphs_pf')
custom_pf = load_park_factors(gameday, table='park_factors')


def fangraphs_park_adjust_stats(stats, infos, neutralize, pitcher=False):
    """
    Adjust rate stats using fangraphs park factors.
    See park_adjust_stats for more details.

    Fangraphs park factors are halved to account for the fact that a player
    only plays half of his games in his home stadium. Thus we can divide a
    player's year long projection by his fangraphs park factors to get a park
    neutral year long projection.
    """
    info = infos.copy()
    if pitcher:
        info['bat_hand'] = 'P'  # Pitcher park factor
        info['key_r'] = [info['opp_team_id'], 'R', 'OUTCOME', info['year_id']]
        info['key_l'] = [info['opp_team_id'], 'L', 'OUTCOME', info['year_id']]
    elif info['bat_hand'] == 'S':  # Batter is switch hitter
        info['key_r'] = [info['team_id'], 'R', 'OUTCOME', info['year_id']]
        info['key_l'] = [info['team_id'], 'L', 'OUTCOME', info['year_id']]
    else:
        info['key'] = [info['team_id'], info['bat_hand'], 'OUTCOME',
                       info['year_id']]
    info['outcome_index'] = 2
    info['outcomes'] = ['SINGLE', 'DOUBLE', 'TRIPLE', 'HR']

    return park_adjust_stats(stats, info, fangraphs_pf, neutralize)


def custom_park_adjust_stats(stats, infos, neutralize):
    """
    Adjust rate stats using our custom park factors.
    See park_adjust_stats for more details.
    """
    info = infos.copy()
    if info['bat_hand'] == 'S':  # Batter is switch hitter
        info['key_r'] = [info['stadium'], info['bat_type'], 'R',
                         info['game_time'], 'OUTCOME', info['year_id']]
        info['key_l'] = [info['stadium'], info['bat_type'], 'L',
                         info['game_time'], 'OUTCOME', info['year_id']]
    else:
        info['key'] = [info['stadium'], info['bat_type'], info['bat_hand'],
                       info['game_time'], 'OUTCOME', info['year_id']]
    info['outcome_index'] = 4
    info['outcomes'] = ['SINGLE', 'DOUBLE', 'TRIPLE', 'HR', 'SO', 'BB']

    return park_adjust_stats(stats, info, custom_pf, neutralize)


def park_adjust_stats(stat_dict, info, pf, neutralize):
    """
    Adjust stats dictionary for fangraphs park factors.

    Arguments:
        stats {dict} -- Dictionary of player rate stats
        info {dict} -- Dictionary of relevant player and game info
        pf {dict} -- Dictionary of relevant park factors
        neutralize {bool} -- If true, convert to park neutral stats.
                             If false, convert to park adjusted stats.

    Returns:
        [dict] -- Dictionary of batter rate stats
    """
    if neutralize:
        operator = op.itruediv
    else:
        operator = op.imul

    for outcome in info['outcomes']:
        if info['bat_hand'] == 'P' or info['bat_hand'] == 'S':
            info['key_r'][info['outcome_index']] = outcome
            key_r = tuple(info['key_r'])
            info['key_l'][info['outcome_index']] = outcome
            key_l = tuple(info['key_l'])
            if key_l not in pf or key_r not in pf:
                raise KeyError("PF doesn't exist!" + str((key_l, key_r)))
            if info['bat_hand'] == 'P':
                # .54 and .46 are league average proportions of at bats by
                # righty and lefty batters, respectively.
                adjustment = .54*pf[key_r] + .46*pf[key_l]
            else:
                # .3 and .7 are league average proportions of at bats thrown by
                # lefty and righty pitchers, respectively. Batter's hand is
                # opposite of pitcher's hand.
                adjustment = .3*pf[key_r] + .7*pf[key_l]
            stat_dict[outcome] = operator(stat_dict[outcome], adjustment)
        else:
            info['key'][info['outcome_index']] = outcome
            key = tuple(info['key'])
            if key not in pf:
                raise KeyError("PF doesn't exist!" + str(key))
            adjustment = pf[key]
            stat_dict[outcome] = operator(stat_dict[outcome], adjustment)

    return stat_dict
