# NOTE: This file and is not currently in use.
# It has been replaced with park_factors_logit.R, which was assessed to be more
# accurate. For details, see: pf_comparison.txt

import pandas as pd
import MySQLdb
import argparse
import itertools
from collections import namedtuple
import os

STATS = ['1B', '2B', '3B', 'HR', 'BB', 'K']

# Scale the hyperparameters to make the prior more informative
# TODO: Adjust scalar?
HYPERPARAMETER_SCALAR = 1

BETA = namedtuple('BETA', ('alpha', 'beta'))

# These values were obtained using fitdistrplus::fitdist in R
# Priors were fit on 2012, 2013, and 2014 season data
# See: pf_priors.R
PF_PRIOR = {'1B': BETA(HYPERPARAMETER_SCALAR*210.55, HYPERPARAMETER_SCALAR*1144.55),
            '2B': BETA(HYPERPARAMETER_SCALAR*77.83, HYPERPARAMETER_SCALAR*1647.03),
            '3B': BETA(HYPERPARAMETER_SCALAR*6.03, HYPERPARAMETER_SCALAR*1272.19),
            'HR': BETA(HYPERPARAMETER_SCALAR*21.88, HYPERPARAMETER_SCALAR*834.92),
            'BB': BETA(HYPERPARAMETER_SCALAR*183.26, HYPERPARAMETER_SCALAR*2285.58),
            'K': BETA(HYPERPARAMETER_SCALAR*121.39, HYPERPARAMETER_SCALAR*502.16)}

# The oldest relevant season of the current stadium construction
# TODO: Find source
# NOTE: CHA, CHN, HOU, SDN, and TOR have planned rennovations before 2016 season
REL_YEAR = {"ANA": 1999, "ARI": 1999, "ATL": 1998, "BAL": 2009, "BOS": 2012,
            "CHA": 2008, "CHN": 2015, "CIN": 2004, "CLE": 2015, "COL": 1996,
            "DET": 2001, "HOU": 2001, "KCA": 2010, "LAN": 1963, "MIA": 2013,
            "MIL": 2002, "MIN": 2010, "NYA": 2010, "NYN": 2012, "OAK": 1997,
            "PHI": 2005, "PIT": 2002, "SDN": 2005, "SEA": 2000, "SFN": 2001,
            "SLN": 2007, "TBA": 1999, "TEX": 2011, "TOR": 2006, "WAS": 2009}


def park_factors(year=2013):

    # Query gameday database to gather all relevant plate appearances
    info = get_queries(year)

    # Calculate park_factors and store in dictionary
    park_factors = calculate_pf(info)

    return park_factors


def get_queries(year):
    '''
    Pulls relevant data from gameday MySQL database and stores data in
    a pandas DataFrame.
    '''

    # Note: There is a bug in gameday.Games.local_game_time
    #       Many 2nd games of a double header have a 3:33 AM start time
    #       Given this, it's possible that there are other bugs in start time
    db = MySQLdb.connect(host="localhost",  # your host, usually localhost
                         user="bbos",       # your username
                         passwd="bbos",     # your password
                         db="gameday")      # name of the data base

    query = (
        "SELECT pitcher, batter, bat_team,"
        " upper(left(right(atbats.gameName,8),3)) as stadium,"
        " stadiumID as stadium_id,"
        " if(halfinning='top', 'A', 'H') as bat_type,"
        " stand as bat_hand,"
        " if(local_game_time >= TIME(170000), 'N', 'D') as game_time,"
        " if(event = 'Single', 1, 0) as 1B,"
        " if(event = 'Double', 1, 0) as 2B,"
        " if(event = 'Triple', 1, 0) as 3B,"
        " if(event = 'Home Run', 1, 0) as HR,"
        " if(event = 'Walk', 1, 0) as BB,"
        " if(event = 'Hit By Pitch', 1, 0) as HBP,"
        " if(event = 'Intent Walk', 1, 0) as IBB,"
        " if(event in ('Strikeout','Strikeout - DP'), 1, 0) as K,"
        " 1 as PA "
        "FROM atbats "
        "JOIN Games using(gameName) "
        "JOIN gameDetail using(gameName) "
        "JOIN players ON atbats.gameName=players.gameName"
        " and atbats.batter=players.id "
        "WHERE year_id=%s and ind in ('F','FR') and event!='Runner Out'"
        " and current_position!='P';" % year)

    info = pd.read_sql(query, db)

    return info


def filter_info(info, bat_team=None, stadium=None, bat_hand=None, bat_type=None,
                game_time=None, batter=None, pitcher=None):
    '''
    Filters a pandas Dataframe.

    param info: DataFrame of pitch info to be filtered.
    param <others>: All other paramers must be iterable.
    '''

    rel_info = info

    filter_dict = {}

    if stadium is not None:
        filter_dict['stadium'] = stadium
    if bat_hand is not None:
        filter_dict['bat_hand'] = bat_hand
    if bat_type is not None:
        filter_dict['bat_type'] = bat_type
    if game_time is not None:
        filter_dict['game_time'] = game_time
    if bat_team is not None:
        filter_dict['bat_team'] = bat_team
    if batter is not None:
        filter_dict['batter'] = batter
    if pitcher is not None:
        filter_dict['pitcher'] = pitcher

    for key, val in filter_dict.items():
        rel_info = rel_info[rel_info[key].isin(val)]

    return rel_info


def calculate_pf(info):
    '''
    Creates the dictionary of park factors.
    Keys are:
        pf[(bat_type, stadium, bat_hand, game_time)]
        e.g. pf[('H', 'WAS', 'R', 'N')] would be home park factors for the
        Washington Nationals for right-handed batters during night-games.
    '''

    stadiums = sorted(info['stadium'].unique().tolist())

    # Whether the batter bats right-handed or left-handed
    bat_hands = sorted(info['bat_hand'].unique().tolist())

    # Whether the game is a day-game or a night-game
    game_times = sorted(info['game_time'].unique().tolist())

    # Whether the batter is home or away
    bat_types = sorted(info['bat_type'].unique().tolist())

    pf = {}
    bat_type = 'UNDEFINED'
    stadium = 'UNDEFINED'

    rates = {}
    rates['A'] = {'1B': info[info['bat_type'] == 'A']['1B'].mean(),
                  '2B': info[info['bat_type'] == 'A']['2B'].mean(),
                  '3B': info[info['bat_type'] == 'A']['3B'].mean(),
                  'HR': info[info['bat_type'] == 'A']['HR'].mean(),
                  'BB': info[info['bat_type'] == 'A']['BB'].mean(),
                  'K': info[info['bat_type'] == 'A']['K'].mean()}
    rates['H'] = {'1B': info[info['bat_type'] == 'H']['1B'].mean(),
                  '2B': info[info['bat_type'] == 'H']['2B'].mean(),
                  '3B': info[info['bat_type'] == 'H']['3B'].mean(),
                  'HR': info[info['bat_type'] == 'H']['HR'].mean(),
                  'BB': info[info['bat_type'] == 'H']['BB'].mean(),
                  'K': info[info['bat_type'] == 'H']['K'].mean()}

    # TODO: Incorporate year of most recent rennovation?
    #       Note: no rennovations were made between 2013 and 2014 seasons.
    for key in itertools.product(bat_types, stadiums, bat_hands, game_times):

        # Print out status message every time calculating a new team pf
        if key[1] != stadium:
            bat_type = key[0]
            stadium = key[1]
            if bat_type == 'A':
                print("CREATING AWAY PARK FACTOR: %s" % stadium)
            else:
                print("CREATING HOME PARK FACTOR: %s" % stadium)

        grouped = info.groupby(['bat_type', 'stadium', 'bat_hand', 'game_time'])
        park_pas = grouped.get_group(key)

        park_batters = park_pas['batter'].unique()
        # Every PA by a batter who has batted in park_pas
        bat_pas = filter_info(info, batter=park_batters, bat_type=['A'])

        park_pitchers = park_pas['pitcher'].unique()
        # Every PA by a pitcher who has pitcher in park_pas
        # Use this to account for quality of pitcher in park_pas
        # Restrict to home at bats for apples to appls comparison
        pit_pas = filter_info(info, pitcher=park_pitchers, bat_type=['H'])

        base_pitchers = bat_pas['pitcher'].unique()
        # Every PA by a pitcher who has pitched in bat_pas
        # Use this to account for quality of pitcher faced by park_batters
        # Restrict to away at bats for apples to apples comparison
        base_pit_pas = filter_info(info, pitcher=base_pitchers, bat_type=['A'])

        pf[key] = calc_park_factor(park_pas, bat_pas, pit_pas, base_pit_pas, rates, bat_type)

    return pf


def calc_park_factor(park_pas, bat_pas, pit_pas, base_pit_pas, rates, bat_type):
    '''
    Calculates the relative frequencies of singles, doubles, triples, home runs,
    non-intentional walks and strikeouts. Meant to capture the effect the
    park has relative to neutral conditions.

    For home park factors we compare hit type frequency relative to
    the respective team's hit type frequency for all plate appearances.

    For road park factors we compare hit type frequency relative to
    a basket of road hit_type frequencies for all batters that appear in the
    sample.

    All park factors are controlled for quality of pitchers faced.
    Park factors are adjusted using an empirical Bayes method.

    param: park_pas: DataFrame all observed plate appearances in the relevant
                     park factor
    param: bat_pas: DataFrame of all plate appearances for all batters that
                    appear in <park_pas>.
    param: pit_pas: DataFrame of all plate appearances for all pitchers that
                    appear in <park_pas>.
    param: base_pit_pas: DataFrame of all plate_appearances for all pitchers
                         that appear in <bat_pas>.
    '''

    # Append weightings and plate appearance counts to the dataframes
    bat_pas = append_weightings(park_pas, bat_pas, 'batter', False)
    pit_pas = append_weightings(park_pas, pit_pas, 'pitcher', False)
    base_pit_pas = append_weightings(bat_pas, base_pit_pas, 'pitcher', True)

    park_factors = {}
    for stat in STATS:
        contextual_pf = calc_contextual_pf(park_pas, bat_pas, pit_pas, base_pit_pas, rates, stat, bat_type)
        park_factors[stat] = calc_posterior_pf(contextual_pf, len(park_pas), PF_PRIOR[stat])

    return park_factors


def append_weightings(info, base, player_type, is_base_pit_info):
    '''
    Appends player weightings and plate appearance counts to base.
    The weightings are used to calculate the basket of players for adjusting
    observed statistics.
    '''

    player_weight = {}
    player_pa = {}

    for pid in info[player_type].unique():
        player_pa_info = info[info[player_type] == pid]
        # The proportion of PAs <pid> comprises in <info>
        if is_base_pit_info:
            player_weight[pid] = float(sum(player_pa_info['weight'] /
                                           player_pa_info['num_pa']))
        else:
            player_weight[pid] = len(player_pa_info) / len(info)
        # The count of PAs for <pid> in <base>
        player_pa[pid] = len(base[base[player_type] == pid])

    weightings = []
    plate_appearances = []
    for pid in base[player_type]:
        weightings.append(player_weight[pid])
        plate_appearances.append(player_pa[pid])
    # Append columns 'weight' and 'num_pa' to <base>
    base = base.assign(weight=weightings)
    base = base.assign(num_pa=plate_appearances)

    return base


def calc_posterior_pf(contextual_pf, num_obs, prior):
    '''
    Computes a posterior park factor utilizing empirical Bayes methods.
    '''
    # since the mle is the estimated success rate in a neutral context
    prior_mle = prior.alpha / (prior.alpha + prior.beta)
    # Compute contextual sucess rate using <contextual_pf>
    success_rate = contextual_pf * prior_mle
    successes = success_rate * num_obs
    # Beta-Binomial model to get posterior
    posterior_mle = (prior.alpha + successes) / (num_obs + prior.alpha + prior.beta)

    # Convert from rate stat to park factor
    return posterior_mle / prior_mle


def calc_contextual_pf(park_pas, bat_pas, pit_pas, base_pit_pas, rates, stat, bat_type):
    '''
    Calculates a contextual park factor using observed data.

    The Park factor controls for pitching faced by building a volume-weighted
    basket of pitcher's that the respective batter's face and controlling for
    the pitcher's <stat> rate.

    param: park_pas: DataFrame all observed plate appearances in the relevant
                     park factor. This is our observed park factor sample.
    param: bat_pas: DataFrame of all plate appearances for all batters that
                    appear in <park_pas>. This is a baseline for which to
                    compare <park_pas>.
    param: pit_pas: DataFrame of all plate appearances for all pitchers that
                    appear in <park_pas>. This is to adjust <park_pas> for
                    quality of pitcher faced.
    param: base_pit_pas: DataFrame of all plate_appearances for all pitchers
                         that appear in <bat_pas>. This is to adjust <bat_pas>
                         for quality of pitcher faced.
    param: stat: String containing the statistic of interest. Possible values of
                 stat include, "1B", "2B", "3B", "HR", "BB", and "K".
    return: contextual_pf: Float representing the park factor after adjusting
                    for pitching and hitting.
    '''
    obs_rate = sum(park_pas[stat]) / sum(park_pas['PA'])

    bat_rate = get_basket_rate(bat_pas[stat], bat_pas['weight'],
                               bat_pas['num_pa'])
    # Bat_rate is the number of observed <stats> in our control sample.
    # This issue occurs due to limited sampling. We do not expect to this occur
    # often and only expect to ever see this when <stat> is 3B. In this case, we
    # set contextual_pf = 2, which is a high estimate of park_factor, but we
    # expect it be largely regressed in the ensuing beta-binomial model
    if bat_rate == 0:
        return 2
    pit_rate = get_basket_rate(pit_pas[stat], pit_pas['weight'],
                               pit_pas['num_pa'])
    base_pit_rate = get_basket_rate(base_pit_pas[stat], base_pit_pas['weight'],
                                    base_pit_pas['num_pa'])

    # control for quality of pitcher faced in this context i.e. <park_pas>
    if bat_type == 'H':
        pitcher_adjusted_pf = obs_rate / pit_rate
    # We must estimate the pitcher control if bat_type is 'A' becuase away at
    # bats in <stadium> is equivalent to pitchers pitching at home in <stadium>.
    # We estimate a pitcher's 'home talent level' by calculating his
    # 'away talent level' relative to away league average and multiplying that
    # by the home league average
    else:
        pitcher_adjusted_pf = obs_rate / (rates['A'][stat] * (pit_rate / rates['H'][stat]))
    # control batters success rate for quality of pitcher faced
    # gives us multiplier of how much better batters in <park_pas> were overall
    relative_batters_skill = bat_rate / base_pit_rate
    # normalize by batters overall skill
    # this estimates the ratio of success in this context to a neutral context
    contextual_pf = pitcher_adjusted_pf / relative_batters_skill

    return contextual_pf


def get_basket_rate(bernoulli, player_weight, player_pa):
    '''
    Finds the success rate for <stat> for a volume weighted basket of players.

    We compute the relative weighting for each plate appearance in the basket
    and then sum the relative weightings for each successful plate appearance.

    param: bernoulli: List of Bernoulli variables, where 1 is the occurence
                      of <stat> in a plate appearance.
    param: player_weight: List of percentages representing the proportion of
                          basket plate appearances that <player> comprises.
    param: player_pa: List of the counts of plate appearances we observe
                      in the basket for <player>
    return: success_rate: Float representing the success rate for <stat> in our
                          basket.
    '''

    pa_weight = player_weight / player_pa
    success_rate = sum(bernoulli * pa_weight)

    return success_rate


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description=(
            "Create a dictionary of park factors.\n"
            "Park factors include:\n"
            "\t1B, 2B, 3B, BB, and K.\n"
            "Park Factors have granularity:\n"
            "\tstadium, righty/lefty, home/away, day/night."),
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument("--year", nargs='?', default=2013, type=int,
                        help="pull all relevant data for years >= <year>")
    args = parser.parse_args()

    info = park_factors(args.year)

    filepath = os.path.abspath(os.path.dirname(__file__))
    filename = filepath + ('/park_factors_%s.csv' % args.year)
    pd.DataFrame.from_dict(info).transpose().to_csv(filename)
