import pandas as pd
import numpy as np
import os
from scipy.stats import ks_2samp
import MySQLdb
import random
import argparse
import itertools


S_ZONE = [1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 16, 17, 18, 19]
B_ZONE = [21, 22, 23, 24]
ALL_ZONES = S_ZONE + B_ZONE


# TODO: Build pitch filtering into MySQL query:
#       pitcher_hand, batter_stand, pitch_type
def collect_pitch_data(min_year, max_year):
    '''
    Returns a DataFrame of all pitches thrown and their accompanying
    pitch data for pitches in the [min_year, max_year] seasons inclusive.
    '''

    db = MySQLdb.connect(host="localhost",  # your host, usually localhost
                         user="bbos",       # your username
                         passwd="bbos",     # your password
                         db="gameday")      # name of the data base
    query = (
        "SELECT pitches.gameName, pitches.pitcher, pitches.batter, pitches.des,"
        " start_speed, end_speed, sz_top, sz_bot, pfx_x, pfx_z, px, pz, x0, y0,"
        " z0, vx0, vy0, vz0, ax, ay, az, break_angle, break_length, pitch_type,"
        " zone, p_throws, stand "
        "FROM pitches "
        "JOIN Games "
        "ON pitches.gameName=Games.gameName and Games.year_id BETWEEN %d and %d"
        " and Games.type not in ('E','S','A') "
        "JOIN atbats "
        "ON pitches.gameName=atbats.gameName and pitches.gameAtBatID=atbats.num"
        " and pitches.pitcher=atbats.pitcher and pitches.batter=atbats.batter "
        "WHERE pitches.pitch_type is not NULL"
        " and pitches.pitch_type not in ('IN','PO','UN','AB');"
        % (min_year, max_year))

    pitches = pd.read_sql(query, db)

    return pitches


def get_cfip(min_year, max_year):
    """
    Collects a DataFrame of pitchers and their average cfips over the
    relevant years.

    Arguments:
        min_year {int} -- the earliest year from which to collect cfip data
        max_year {int} -- the last year from which to collect cfip data

    Returns:
        [DataFrame] -- dataframe of pitcher's and their average cFIPs during
                       the relevant years.
    """

    db = MySQLdb.connect(host="localhost",  # your host, usually localhost
                         user="bbos",       # your username
                         passwd="bbos",     # your password
                         db="gameday")      # name of the data base

    query = (
        "SELECT pitcher, avg(cfip) AS cfip "
        "FROM cfip "
        "WHERE year_id BETWEEN %s AND %s "
        "GROUP BY pitcher;" % (min_year, max_year))

    cfip = pd.read_sql(query, db)

    return cfip


def relabel_pitch_type(pitches):
    '''
    Adjusts the pitch type of certain pitches. We consolidate pitch types for
    simplicity and due to categoric errors from the pitch-fx database.
    '''

    pitches.loc[pitches['pitch_type'] == 'FF', 'pitch_type'] = 'FA'
    pitches.loc[pitches['pitch_type'] == 'FT', 'pitch_type'] = 'SI'
    pitches.loc[pitches['pitch_type'] == 'FO', 'pitch_type'] = 'FS'
    pitches.loc[pitches['pitch_type'] == 'KC', 'pitch_type'] = 'CU'

    return pitches


def adjust_release(pitches):
    '''
    This adjusts the pitch release data so that it is measured
    from 55 feet away from home plate, rather than 50 feet away. It is
    generally agreed upon that it is more representative to measure a pitcher's
    release point from 55 feet.
    Utilizes Newtonian physics kinematics equations. Assumes constant
    acceleration: x = x_0 + vt+ (1/2)at^2
    '''

    # Solves for t, the time to travel from y=50 to y=55
    t = ((-pitches['vy0'] - (((pitches['vy0']**2) -
                             ((2)*pitches['ay']*(-5)))**(1/2)))/pitches['ay'])
    pitches['x0'] = (pitches['x0'] + pitches['vx0']*t +
                     (0.5)*pitches['ax']*(t**2))
    pitches['z0'] = (pitches['z0'] + pitches['vz0']*t +
                     (0.5)*pitches['az']*(t**2))
    pitches['y0'] = (pitches['y0'] + pitches['vy0']*t +
                     (0.5)*pitches['ay']*(t**2))

    return pitches


def label_zones(pitches):
    '''
    Determines what zone the pitch was thrown in. The strike zone has been
    broken into 5 horizontal zones and 5 vertical zones. For each we follow
    the same process. First we break the srike zone into 3 horizontal/vertical
    zones. We then break the outer 2 zones, each of which represent 1/3 of the
    strike zone, into 2 zones. This results in the following, which we show
    from the catcher'sperspective.
    Note pitch data is in unit feet and we must convert it to unit inches.
    All units in this method are in inches. Horizontal mesurements are
    horizontal displacements from the center of home plate, relative to the
    catcher's perspective. Vertical measurements are vertical height of above
    the ground in inches.

                  |
       21         |        22
                  |
         _________|_________
         |11___|_12__|__ 13|
         |  |  |     |  |  |
         |__|1_|__2__|_3|__|
         |  |  |     |  |  |
    _____|14|4 |  5  | 6|16|_____
         |__|__|_____|__|__|
         |  |  |     |  |  |
         |  |7_|__8__|_9|  |
         |17___|_18__|___19|
                  |
       23         |        24
                  |
                  |
    '''

    min_horz = -9.95  # Left edge of home plate from catcher's perspective
    max_horz = 9.95  # Right edge of home plate from catcher's perspective
    mid_horz = 0  # Middle of home plate
    horz1 = min_horz
    horz2 = (2/3)*min_horz
    horz3 = (1/3)*min_horz
    horz4 = (1/3)*max_horz
    horz5 = (2/3)*max_horz
    horz6 = max_horz
    # We multiply by 12 to convert from feet to inches
    min_vert = 12*pitches['sz_bot']-1.45  # Bottom of strike zone
    max_vert = 12*pitches['sz_top']+1.45  # Top of strike zone
    mid_vert = (1/2)*(min_vert+max_vert)  # Middle of strike zone
    vert1 = min_vert
    vert2 = min_vert + (1/6)*(max_vert-min_vert)
    vert3 = min_vert + (2/6)*(max_vert-min_vert)
    vert4 = max_vert - (2/6)*(max_vert-min_vert)
    vert5 = max_vert - (1/6)*(max_vert-min_vert)
    vert6 = max_vert
    # We multiply by 12 to convert from feet to inches
    pitch_horz = 12*pitches['px']
    pitch_vert = 12*pitches['pz']

    '''
    We use a combination of < ,> and <=,>= to ensure that ball zones are equally
    sized. Within the strike zone we push pitches toward the inner zones (i.e.
    single digit strike zone).
    '''

    # Pitches outside of strike zone
    pitches.loc[(pitch_horz < horz1) & (pitch_vert >= mid_vert), 'zone'] = 21
    pitches.loc[(pitch_horz < horz1) & (pitch_vert < mid_vert), 'zone'] = 23
    pitches.loc[(pitch_horz > horz6) & (pitch_vert > mid_vert), 'zone'] = 22
    pitches.loc[(pitch_horz > horz6) & (pitch_vert <= mid_vert), 'zone'] = 24
    pitches.loc[(pitch_vert < vert1) & (pitch_horz <= mid_horz), 'zone'] = 23
    pitches.loc[(pitch_vert < vert1) & (pitch_horz > mid_horz), 'zone'] = 24
    pitches.loc[(pitch_vert > vert6) & (pitch_horz < mid_horz), 'zone'] = 21
    pitches.loc[(pitch_vert > vert6) & (pitch_horz >= mid_horz), 'zone'] = 22
    # Pitches in inner part of strike zone
    pitches.loc[(pitch_horz >= horz2) & (pitch_horz < horz3) &
                (pitch_vert > vert4) & (pitch_vert <= vert5), 'zone'] = 1
    pitches.loc[(pitch_horz >= horz3) & (pitch_horz <= horz4) &
                (pitch_vert > vert4) & (pitch_vert <= vert5), 'zone'] = 2
    pitches.loc[(pitch_horz > horz4) & (pitch_horz <= horz5) &
                (pitch_vert > vert4) & (pitch_vert <= vert5), 'zone'] = 3
    pitches.loc[(pitch_horz >= horz2) & (pitch_horz < horz3) &
                (pitch_vert >= vert3) & (pitch_vert <= vert4), 'zone'] = 4
    pitches.loc[(pitch_horz >= horz3) & (pitch_horz <= horz4) &
                (pitch_vert >= vert3) & (pitch_vert <= vert4), 'zone'] = 5
    pitches.loc[(pitch_horz > horz4) & (pitch_horz <= horz5) &
                (pitch_vert >= vert3) & (pitch_vert <= vert4), 'zone'] = 6
    pitches.loc[(pitch_horz >= horz2) & (pitch_horz < horz3) &
                (pitch_vert >= vert2) & (pitch_vert < vert3), 'zone'] = 7
    pitches.loc[(pitch_horz >= horz3) & (pitch_horz <= horz4) &
                (pitch_vert >= vert2) & (pitch_vert < vert3), 'zone'] = 8
    pitches.loc[(pitch_horz > horz4) & (pitch_horz <= horz5) &
                (pitch_vert >= vert2) & (pitch_vert < vert3), 'zone'] = 9
    # Pitches in outer part of strike zone
    pitches.loc[(pitch_horz >= horz1) & (pitch_horz < horz2) &
                (pitch_vert > vert4) & (pitch_vert <= vert6), 'zone'] = 11
    pitches.loc[(pitch_horz >= horz1) & (pitch_horz < horz3) &
                (pitch_vert > vert5) & (pitch_vert <= vert6), 'zone'] = 11
    pitches.loc[(pitch_horz >= horz3) & (pitch_horz <= horz4) &
                (pitch_vert > vert5) & (pitch_vert <= vert6), 'zone'] = 12
    pitches.loc[(pitch_horz > horz5) & (pitch_horz <= horz6) &
                (pitch_vert > vert4) & (pitch_vert <= vert6), 'zone'] = 13
    pitches.loc[(pitch_horz > horz4) & (pitch_horz <= horz6) &
                (pitch_vert > vert5) & (pitch_vert <= vert6), 'zone'] = 13
    pitches.loc[(pitch_horz >= horz1) & (pitch_horz < horz2) &
                (pitch_vert >= vert3) & (pitch_vert <= vert4), 'zone'] = 14
    pitches.loc[(pitch_horz > horz5) & (pitch_horz <= horz6) &
                (pitch_vert >= vert3) & (pitch_vert <= vert4), 'zone'] = 16
    pitches.loc[(pitch_horz >= horz1) & (pitch_horz < horz2) &
                (pitch_vert >= vert1) & (pitch_vert < vert3), 'zone'] = 17
    pitches.loc[(pitch_horz >= horz1) & (pitch_horz < horz3) &
                (pitch_vert >= vert1) & (pitch_vert < vert2), 'zone'] = 17
    pitches.loc[(pitch_horz >= horz3) & (pitch_horz <= horz4) &
                (pitch_vert >= vert1) & (pitch_vert < vert2), 'zone'] = 18
    pitches.loc[(pitch_horz > horz5) & (pitch_horz <= horz6) &
                (pitch_vert >= vert1) & (pitch_vert < vert3), 'zone'] = 19
    pitches.loc[(pitch_horz > horz4) & (pitch_horz <= horz6) &
                (pitch_vert >= vert1) & (pitch_vert < vert2), 'zone'] = 19

    return pitches


def append_plate_discipline(pitches):
    '''
    Determines whether the pitch resulted in a 'whiff', 'contact', or 'take'.
    '''

    whiff = ['Swinging Strike', 'Swinging Strike (Blocked)', 'Missed Bunt']
    contact = ['Foul', 'In play, out(s)', 'In play, run(s)', 'In play, no out',
               'Foul Tip', 'Foul (Runner Going)', 'Foul Bunt']
    take = ['Called Strike', 'Ball', 'Hit By Pitch', 'Ball In Dirt']

    pitches.loc[pitches['des'].isin(whiff), 'plate_dis'] = 'Whiff'
    pitches.loc[pitches['des'].isin(contact), 'plate_dis'] = 'Contact'
    pitches.loc[pitches['des'].isin(take), 'plate_dis'] = 'Take'

    return pitches


def get_zone_pmf(pitches):
    '''
    Creates a probability mass function for the zone distribution of pitches.
    zone_dist_pmf(x) = P(zone=x).
    '''

    pitch_zones = pitches['zone']
    # Need to create an empty Series to ensure that all zones are in the pmf
    zone_dist_pmf = pd.Series(float(0), index=ALL_ZONES)
    pandas_pmf = pitch_zones.value_counts(normalize=True).sort_index()
    zone_dist_pmf = (zone_dist_pmf + pandas_pmf).fillna(0)

    return zone_dist_pmf


def calc_plate_discipline(plate_dis_1, plate_dis_2):
    '''
    Returns a list of ratios for plate discipline stats for pitchers 1 and 2.

    Plate discipline stats are:
        z-swing: percentage of pitches in the strike zone that are swung at
        o-swing: percentage of pitches outside the strike zone that are swung at
        z-contact: percentage of swings that result in contact on pitches inside
            the stike zone
        o-contact: percentage of swings that result in contact on pitches
            outside of the strike zone.

    :param plate_dis_1: a series of plate discipline rates for pitcher 1 for a
                        specific pitch against batters of a specific hand.
    :param plate_dis_2: a series of plate discipline rates for pitcher 2 for a
                        specific pitch against batters of a specific hand.
    :return: returns a list of floats, which are equal to the 1 - the difference
             of the plate disciplinen rates for the relevant pitchers.
    '''

    plate_dis = []
    rates = ['z-swing', 'o-swing', 'z-contact', 'o-contact']
    # We raise to <power> to roughly match the magnitudes of the
    #     mean(<plate_dis>).
    for rate in rates:
        if rate == 'o-swing':
            power = 1
        elif rate == 'o-contact':
            power = 2
        elif rate == 'z-swing':
            power = 3
        else:
            power = 4

        if max(plate_dis_1[rate], plate_dis_2[rate]) == 0:
            plate_dis.append(0)
        else:
            plate_dis.append((min(plate_dis_1[rate], plate_dis_2[rate]) /
                              max(plate_dis_1[rate], plate_dis_2[rate]))**power)

    return plate_dis


def prep_plate_discipline(pitches):
    '''
    Returns a pandas Series of plate discipline rates.

    Plate discipline rates are:
        z-swing: percentage of pitches in the strike zone that are swung at
        o-swing: percentage of pitches outside the strike zone that are swung at
        z-contact: percentage of swings that result in contact on pitches inside
            the stike zone
        o-contact: percentage of swings that result in contact on pitches
            outside of the strike zone
        sw-str: percentage of pitches thrown that result in a whiff
        whiff: percentage of swings that result in a whiff
        zone: percentage of pitches thrown that are inside of the strike zone

    '''

    plate_dis = pd.Series(float(0), index=['z-swing', 'o-swing', 'z-contact',
                                           'o-contact', 'sw-str', 'whiff',
                                           'zone'])
    swing = ['Whiff', 'Contact']

    z_pitches = pitches[pitches['zone'].isin(S_ZONE)]
    o_pitches = pitches[pitches['zone'].isin(B_ZONE)]
    z_swings = z_pitches[z_pitches['plate_dis'].isin(swing)]
    o_swings = o_pitches[o_pitches['plate_dis'].isin(swing)]
    swings = pitches[pitches['plate_dis'].isin(swing)]

    plate_dis['zone'] = plate_dis_rate(pitches, z_pitches)
    plate_dis['z-swing'] = plate_dis_rate(z_pitches, z_swings)
    plate_dis['o-swing'] = plate_dis_rate(o_pitches, o_swings)
    plate_dis['z-contact'] = plate_dis_rate(z_swings, z_swings, ['Contact'])
    plate_dis['o-contact'] = plate_dis_rate(o_swings, o_swings, ['Contact'])
    plate_dis['sw-str'] = plate_dis_rate(pitches, swings, ['Whiff'])
    plate_dis['whiff'] = plate_dis_rate(swings, swings, ['Whiff'])

    return plate_dis


def plate_dis_rate(rel_pitches, rel_subset, plate_dis=None):
    '''
    Computes a subset's rate of occurence within rel_pitches, the relevant
    pitches. the relevant subset is either rel_subset or is contained in
    rel_subset. If the main set, rel_pitches, is empty we return 0.
    '''

    if len(rel_pitches) == 0:
        return 0

    if plate_dis is None:
        rate = len(rel_subset) / len(rel_pitches)
    else:
        events = rel_subset[rel_subset['plate_dis'].isin(plate_dis)]
        rate = len(events) / len(rel_pitches)
    return rate


def calc_ks_statistic(stat_data_1, stat_data_2):
    '''
    Returns 1 - the KS-statistic between the empirical distribution functions
    of observed data stat_data_1 and stat_data_2.

    The K-S test is particularly useful when comparing discrete distributions
    where the bins have a natural ordering.

    :param stat_data_1: a list or series of data points for the statistic being
                        compared for pitcher 1 when throwing a specific pitch
                        against batters of a specific batter hand.
    :param stat_data_2: a list or series of data points for the statistic being
                        compared for pitcher 2 when throwing a specific pitch
                        against batters of a specific batter hand.
    :return: a float in [0,1] representing the similarity of the statistic for
             pitchers 1 and 2 for a specific pitch type against batters of a
             specific batter hand.

    '''

    ks_statistic = ks_2samp(stat_data_1, stat_data_2)[0]
    similarity = 1 - ks_statistic

    return similarity


def calc_hellinger_distance(p, q):
    '''
    Returns 1 - the Hellinger distance between probability mass
    functions p and q. The Hellinger distance is useful when comparing discrete
    distributions where the bins do not have a natural ordering.
    '''

    hellinger_distance = np.linalg.norm(np.sqrt(p) - np.sqrt(q))/(np.sqrt(2))
    similarity = 1 - hellinger_distance

    return similarity


# TODO: Should we use pandas group by instead?
# TODO: can inputs be tuples or must they be lists?
def filter_pitches(pitches, pitch=None, hand=None, stand=None, pitcher=None):
    '''
    Returns filtered pitch data according to function arguments.
    pitch, hand, stand, and pitcher must be passed in as lists or None
    '''

    filtered_pitches = pitches

    filter_dict = {}
    if pitch is not None:
        filter_dict['pitch_type'] = pitch
    if hand is not None:
        filter_dict['p_throws'] = hand
    if stand is not None:
        filter_dict['stand'] = stand
    if pitcher is not None:
        filter_dict['pitcher'] = pitcher

    for key, val in filter_dict.items():
        filtered_pitches = filtered_pitches[filtered_pitches[key].isin(val)]

    return filtered_pitches


def blend_sim_scores(sim, cfip):
    """
    Combines the calculated similarity scores and cFIP into a blended
    similarity score.


    We create 5 possible blends:
        'similarity': calculated similarity score
        'sim_light': 2/3 calculated similarity score and 1/3 normalized cFIP
        'sim_med': 1/2 calculated similarity score and 1/2 normalized cFIP
        'sim_heavy': 1/3 calculated similarity score and 1/3 normalized cFIP
        'cfip': normalized cFIP

    Arguments:
        sim {DataFrame} -- A DataFrame containing pitcher ids and calculated
                           similarity scores. Columns are 'pit1', 'pit2', and
                           'similarity'.
        cfip {DataFrame} -- A Dataframe containg pitcher ids and the pitcher's
                            average cFIP over the releavant season(s).

    Returns:
        [DataFrame] -- A DataFrame of all the pitcher ids and all the blended
                       similarity scores. Columns are 'pit1', 'pit2',
                       'similarity', 'sim_light', 'sim_med', 'sim_heavy',
                       and 'cfip'.
    """

    # Performs feature scaling to normalize cfip to [0, 1]
    cfip['cfip'] = ((cfip['cfip'] - cfip['cfip'].min()) /
                    (cfip['cfip'].max() - cfip['cfip'].min()))
    cfip['pitcher'] = cfip['pitcher'].astype('int')
    cfip = cfip.set_index('pitcher')

    cfip_sim = 1 - abs(cfip.loc[sim['pit1'], 'cfip'].reset_index()['cfip'] -
                       cfip.loc[sim['pit2'], 'cfip'].reset_index()['cfip'])

    sim['sim_light'] = 0
    sim.loc[sim['similarity'] > 0, 'sim_light'] = ((2/3)*sim['similarity'] +
                                                   (1/3)*cfip_sim)
    sim['sim_med'] = 0
    sim.loc[sim['similarity'] > 0, 'sim_med'] = ((1/2)*sim['similarity'] +
                                                 (1/2)*cfip_sim)
    sim['sim_heavy'] = 0
    sim.loc[sim['similarity'] > 0, 'sim_heavy'] = ((1/3)*sim['similarity'] +
                                                   (2/3)*cfip_sim)
    sim['cfip'] = cfip_sim
    #sim.loc[sim['similarity'] == 0, 'cfip'] = 0

    return sim


class PitcherSimilarityScores():
    '''
    Creates a dictionary of similarity scores between every pair of pitches in a
    sample. The similarity score is in [0,1]. The greater the number the larger
    the similarity between two pitchers. A pitcher has a similarity score of 1
    with himself. A right-handed pitcher and a left-handed pitcher have a
    similarity score of 0 with each other.
    '''

    def __init__(self, pitch_types=['FA', 'FC', 'SI', 'CH', 'FS',
                                    'CU', 'SL', 'SC', 'KN', 'EP'],
                 pitcher_hand=['R', 'L'], batter_stand=['R', 'L'],
                 years=[2014, 2014], pitcher_ids=None):

        # TODO: How many years of data to analyze by default?
        self.min_year = years[0]
        self.max_year = years[1]

        if isinstance(pitch_types, str):
            # Allows single pitch type to be entered as a string
            self.all_pitch_types = [pitch_types]
        else:
            self.all_pitch_types = pitch_types

        if isinstance(pitcher_ids, int):
            # Allows single pitcher id to be entered as an int
            self.pitcher_ids = [pitcher_ids]
        else:
            self.pitcher_ids = pitcher_ids

        if pitcher_hand in ['R', 'L']:
            # Allows single pitcher hand to be entered as a string
            self.all_pitcher_hands = [pitcher_hand]
        else:
            self.all_pitcher_hands = pitcher_hand

        if batter_stand in ['R', 'L']:
            # Allows single batter stand to be entered as a string
            self.all_batter_stands = [batter_stand]
        else:
            self.all_batter_stands = batter_stand

        self.all_pitch_stats = ['start_speed', 'pfx_x', 'pfx_z', 'x0', 'z0']
        vel = 0.15
        movx = 0.10
        movy = 0.10
        relx = 0.05
        rely = 0.05
        zone = 0.15
        z_swing = 0.10
        o_swing = 0.10
        z_contact = 0.10
        o_contact = 0.10
        self.weightings = [vel, movx, movy, relx, rely, zone, z_swing, o_swing,
                           z_contact, o_contact]
        assert(.999 < sum(self.weightings) < 1.001)

        self.all_metrics = []

    def get_pss_dict(self, test=False, print_stats=False):
        '''
        Creates a dictionary of pitcher similarity scores for specified
        pitchers. Pitchers are specified by self.pitcher_ids. If not specificed
        then similarity scores are created for all pitchers.
        '''

        # self.all_metrics needs to be reset before each run
        # Collects a list of all metrics for all pitchers for anaysis
        self.all_metrics = []

        print("Collecting pitches.")
        pitches = self.get_pitches()

        all_pitchers, pitcher_index = self.get_rel_pitchers(pitches, test)

        print("Calculating pitcher metrics.")
        metrics = self.get_pitcher_metrics(pitches, all_pitchers)

        pss_dict = self.create_pss_dict(all_pitchers, pitcher_index, metrics)

        metric_names = ['vel', 'movx', 'movy', 'relx', 'rely', 'zone', 'zswing',
                        'oswing', 'zcontact', 'ocontact']
        self.all_metrics = pd.DataFrame(self.all_metrics, columns=metric_names)

        pss_data = []
        for key in pss_dict.keys():
            pss_data.append([key[0], key[1], pss_dict[key]])
        raw_pss = pd.DataFrame(pss_data, columns=['pit1', 'pit2', 'similarity'])

        cfip = get_cfip(self.min_year, self.max_year)

        sim_scores = blend_sim_scores(raw_pss, cfip)

        if print_stats:
            return sim_scores, self.all_metrics
        else:
            return sim_scores

    def create_pss_dict(self, all_pitchers, pitcher_index, metrics):
        '''
        Returns the calculated dictionary of pitcher similarity scores.
        '''

        pss_dict = {}
        for i, key in enumerate(itertools.product(pitcher_index, all_pitchers)):
            flip_key = (key[1], key[0])
            # Print status updates
            if i % (10*len(all_pitchers)) == 0:
                print("Computing similarity scores for pitcher id:", key[0])
                print("\t%d: %d" % (i/len(all_pitchers), len(pitcher_index)))
            # Avoid calculating duplicate entries
            if flip_key in pss_dict.keys():
                pss_dict[key] = pss_dict[flip_key]
            # Pitcher has similarity score 1 with himself
            elif key[0] == key[1]:
                pss_dict[key] = 1
            else:
                # Check if pitchers throw with the same hand
                if metrics[key[0]]['hand'] == metrics[key[1]]['hand']:
                    pss_dict[key] = self.get_sim_score(metrics[key[0]], metrics[key[1]])
                else:
                    pss_dict[key] = 0

        return pss_dict

    def get_sim_score(self, pit_1, pit_2):
        '''
        Returns a similarity score in [0,1] for the relevant pitchers.

        For <pitch_type>, calculates a 'pitch similarity score' in [0,1] and
        weights it by the frequency with which <pitch_type> was thrown by
        <pitcher1> or <pitcher2>. The pitch frequency is:
        P(pitch = <pitch_type> | pitcher = <pitcher1> or pitcher = <pitcher2>).

        :param pit_1: dictionary of all relevant pitch info for pitcher 1.
        :param pit_2: dictionary of all relevant pitch info for pitcher 2.
        :return: returns a float representing the similarity score for
                 pitchers 1 and 2.
        '''

        sim_score = 0
        total_pitches = pit_1['count'] + pit_2['count']
        for pitch_type in self.all_pitch_types:
            # Check if either pitcher has not thrown pitch <pitch_type>
            if pit_1[pitch_type]['count'] == 0 or pit_2[pitch_type]['count'] == 0:
                pass
            else:
                score = self.calc_pitch_score(pit_1[pitch_type],
                                              pit_2[pitch_type])
                count = pit_1[pitch_type]['count'] + pit_2[pitch_type]['count']
                freq = count / total_pitches
                sim_score += score * freq

        return sim_score

    def calc_pitch_score(self, pitch_info_1, pitch_info_2):
        '''
        Returns a pitch score for relavent pitchers.

        The pitch score is the average of the pitch scores when facing
        right-handed batters and the pitch score when facing left-handed
        batters, weighted by the distribution of pitches thrown to left and
        right handed batters. The pitch score represents the similarity of a
        specific pitch type for pitchers 1 and 2. The pitch score is in [0,1].

        :param pitch_info_1: a dictionary of relevant info for a pitches thrown
                             by pitcher 1 of some specific pitch_type.
        :param pitch_info_2: a dictionary of relevant info for a pitches thrown
                             by pitcher 2 of some specific pitch_type.
        :return: returns a float, which is the similarity score for the relevant
                 pitch for the relevant pitchers.
        '''

        # pmf of pitches to right-handed and left-handed batters: [rhb%, lhb%]
        pitch_splits = self.get_pitch_splits(pitch_info_1, pitch_info_2)
        stand_score = []
        for stand in self.all_batter_stands:
            pitch_stats = self.calc_pitch_stats(pitch_info_1[stand],
                                                pitch_info_2[stand])
            stand_score.append(np.dot(self.weightings, pitch_stats))
        # Weighted average of pitch scores when facing righty and lefty batters
        pitch_score = np.dot(pitch_splits, stand_score)

        return pitch_score

    def calc_pitch_stats(self, stand_info_1, stand_info_2):
        '''
        Calculates and returns a list of metrics used in determining the
        similarity scores.

        The metrics calulcated herein are with respect to the relevant pitchers
        throwing a specific pitch against batters with a specicific batter
        handedness. All metrics are in [0,1]

        :param stand_info_1: a dictionary containing relevant info for pitches
                             of a specific pitch type that are thrown by pitcher
                             1 against batters of a specific batter handedness.
        :param stand_info_2: a dictionary containing relevant info for pitches
                             of a specific pitch type that are thrown by pitcher
                             2 against batters of a specific batter handedness.
        :return: returns a list of floats representing pitch metrics that are
                 used to compute the pitch score for the respective pitch type,
                 batter hand, and pitchers.
        '''

        # Check if either pitcher has not thrown pitch 'pitch_type' against
        # batters of the relevant stance
        if stand_info_1['count'] == 0 or stand_info_2['count'] == 0:
            return [0]*len(self.weightings)
        pitch_statistics = []
        for stat in self.all_pitch_stats:
            pitch_statistics.append(calc_ks_statistic(stand_info_1[stat],
                                                      stand_info_2[stat]))
        pitch_statistics.append(calc_hellinger_distance(stand_info_1['zone_pmf'],
                                                        stand_info_2['zone_pmf']))
        pitch_statistics += calc_plate_discipline(stand_info_1['plate_dis'],
                                                  stand_info_2['plate_dis'])
        self.all_metrics.append(pitch_statistics)

        return pitch_statistics

    def get_pitches(self):
        '''
        Returns all relevant pitch data for calculating similarity scores.
        Collects pitch data from MySQL database, adjusts and appends collected
        pitch data, and filters edited pitch data as specified when the class
        is initialized.
        '''

        raw_pitchfx = collect_pitch_data(self.min_year, self.max_year)
        pitchfx = self.adjust_pitches(raw_pitchfx)
        filtered_pitchfx = filter_pitches(pitchfx,
                                          pitch=self.all_pitch_types,
                                          hand=self.all_pitcher_hands,
                                          stand=self.all_batter_stands)

        return filtered_pitchfx

    def adjust_pitches(self, pitches):
        '''
        Adjusts pitch data. Reclassifies pitch types. Labels the zone in which
        pitches were thrown. Displaces the pitcher release point from 50 feet
        away from home plate to 55 feet away from home plate. Appends plate
        discipline stats.
        '''

        pitches = relabel_pitch_type(pitches)
        pitches = adjust_release(pitches)
        pitches = label_zones(pitches)
        pitches = append_plate_discipline(pitches)

        return pitches

    def get_pitcher_metrics(self, pitches, pitcher_ids):
        '''
        Returns a dictionary of pitcher metrics for all <pitcher_ids>.
        '''

        metric_dict = {}
        for pitcher_id in pitcher_ids:
            metric_dict[pitcher_id] = self.prep_pitcher_metrics(
                filter_pitches(pitches, pitcher=[pitcher_id]))

        return metric_dict

    def prep_pitcher_metrics(self, pitches):
        '''
        Prepares pitch data for metrics to be calculated. Metrics include:
            velocity similarity, release similarity, pitch movement similarity,
            pitch location similarity, and plate discipline similarity.
        '''

        # Assumes no pitchers are ambidextrous. An ambidextrous pitcher would
        # be arbitrarily labelled as either lefty or righty based on the first
        # pitch seen in the data set that is thrown by them.
        pit_data = {'count': 0, 'hand': pitches.iloc[0]['p_throws']}
        for pitch_type in self.all_pitch_types:
            pit_data[pitch_type] = {'count': 0}
            # TODO: Can we use pandas group by sort pitches by <pitch_type>
            #       and possibly (all) other filters?
            pitch_type_pitches = filter_pitches(pitches, pitch=[pitch_type])
            for stand in self.all_batter_stands:
                rel_pitches = filter_pitches(pitch_type_pitches, stand=[stand])
                pit_data[pitch_type][stand] = self.get_stand_metrics(rel_pitches)
                pit_data[pitch_type]['count'] += pit_data[pitch_type][stand]['count']
            pit_data['count'] += pit_data[pitch_type]['count']

        return pit_data

    def get_stand_metrics(self, pitches):
        '''
        Returns a dictionary containg the relevant pitcher metrics to
        calculate pitcher similarity scores for a given pitch and batter stance.

        Dictionary for pitches of type <pitch_type> against batters
        of stance <stand>. Keys are the metrics being calculated.
        Values are relevant info from an associated pitcher needed to
        calculate pitcher similarity between two pitchers for metric.

        param: pitches: DataFrame of all relevant pitches to be considered
        return: dictionary of prepared and organized pitch info
        '''

        metrics = {}
        metrics['count'] = len(pitches)
        if metrics['count'] > 0:
            for stat in self.all_pitch_stats:
                metrics[stat] = pitches[stat]
            metrics['zone_pmf'] = get_zone_pmf(pitches)
            metrics['plate_dis'] = prep_plate_discipline(pitches)

        return metrics

    def get_rel_pitchers(self, pitches, test):
        '''
        Returns the list of all pitchers who threw a pitch in <pitches>.
        Returns a list of pitchers for whom we want to create similarity scores.
        '''

        all_pitchers = sorted(pitches['pitcher'].unique())

        if test:
            random.seed(13)
            self.pitcher_ids = random.sample(all_pitchers, 30)
            pitcher_index = sorted(self.pitcher_ids)
        elif self.pitcher_ids is None:
            pitcher_index = all_pitchers
        else:
            pitcher_index = sorted(self.pitcher_ids)

        return all_pitchers, pitcher_index

    def get_pitch_splits(self, pit_1, pit_2):
        '''
        Returns a list of the probability of pitches thrown to right-handed and
        left-handed batters, respectively. <pit_1> and <pit_2> are dictionaries
        referring to either all pitches thrown by the relevant pitchers or a
        specific pitch type thrown by the relevant pitchers.
        '''

        pitch_splits = []
        total_pitches = pit_1['count'] + pit_2['count']
        for stand in self.all_batter_stands:
            num_pitches = pit_1[stand]['count'] + pit_2[stand]['count']
            pitch_splits.append(num_pitches / total_pitches)

        return pitch_splits


if __name__ == '__main__':

    pitch_types = ['FA', 'FC', 'SI', 'CH', 'FS', 'CU', 'SL', 'SC', 'KN', 'EP']

    parser = argparse.ArgumentParser(
        description=(
            "Create a DataFrame of pitcher similarity scores between 0 and 1"))
    parser.add_argument("--hand", nargs='*', default=["R", "L"],
                        help="list of handedness of pitchers to compare")
    parser.add_argument("--stand", nargs='*', default=["R", "L"],
                        help="list of handedness of the batter to compare")
    parser.add_argument("--years", nargs='*', default=[2013, 2013], type=int,
                        help="list of range of years to collect pitches")
    parser.add_argument("--pitch", nargs='*', default=pitch_types,
                        help="list of pitch_types to compare")
    parser.add_argument("--pitcher_id", nargs='*', default=None, type=int,
                        help="list of pitcher ids to compare")
    parser.add_argument("--test", nargs='?', default='False',
                        help="test a random subset of pitchers")
    parser.add_argument("--stats", nargs='?', default='False',
                        help="print a csv of pitcher metrics")
    args = parser.parse_args()

    pss = PitcherSimilarityScores(args.pitch, args.hand, args.stand,
                                  args.years, args.pitcher_id)

    file_path = os.path.abspath(os.path.dirname(__file__)) + '/'

    if args.test.lower() == 'true' and args.stats.lower() == 'true':
        sim_scores, stats = pss.get_pss_dict(test=True, print_stats=True)
    elif args.test.lower() == 'true' and args.stats.lower() == 'false':
        sim_scores = pss.get_pss_dict(test=True, print_stats=False)
    elif args.test.lower() == 'false' and args.stats.lower() == 'true':
        sim_scores, stats = pss.get_pss_dict(test=False, print_stats=True)
    else:
        sim_scores = pss.get_pss_dict(test=False, print_stats=False)

    sim_scores.to_csv(file_path + 'sim_scores.csv')
    if args.stats.lower() == 'true':
        stats.to_csv(file_path + 'stats.csv')
