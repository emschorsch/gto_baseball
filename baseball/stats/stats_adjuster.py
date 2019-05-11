#!/usr/bin/python

"""
Idea is for stat_loader to only load historical stats
This class will then take those in along with zips steamer and other stuff
Do any adjustments necessary and then take the posterior rates produced and
    construct a team object
"""

# What's a good name?
# This class will create the team object
# Will take the observed stats and get the posterior and plug into team
# Handle small sample cases
# Handle relievers as well
# Handle unseen players

from baseball.simulator.team import Team
from baseball.simulator.pitcher import Pitcher
from baseball.simulator.player import Player
from baseball.simulator import batting_rates_index as br

from . import utils
from . import player_projections
from . import park_factors as pf
from . import player_splits as splits


def get_pinch_hitter_rates(info):
    # NOTE: pinch hitters are not adjusted for the SP because they will almost
    #       always bat against relief pitchers.
    stat_dict = player_projections.PINCH_HITTER_STATS.copy()
    # Assume all pinch hitters are switch hitters for now since in reality they
    #  will almost always be subbed in with opposite handedness to the pitcher
    info['bat_hand'] = 'S'
    adjusted_stats = pf.custom_park_adjust_stats(stat_dict, info, neutralize=False)
    normalized_stats = utils.normalize_dictionary(adjusted_stats)

    return utils.listify_stat_dict(normalized_stats)


def prepare_matchup_batting_rates(batter_stats, pitcher_stats, league_stats, stat_names):
    """
    Combines pitcher projections, batter projections, and league average
    statistics in order to predict the event probabilities for a specific
    batter vs pitcher matchup.

    While not necessary, for best results batter and pitcher projections should
    be of the same context. That is, both should be park neutral, park adjusted,
    splits adjusted, etc.

    Arguments:
        batter_stats {dict} -- dictionary of predicted batter batting event
                               frequency counts.
        pitcher_stats {dict} -- dictionary of predicted pitcher batting event
                                frequency counts.
        league_stats {dict} -- dictionary of predicted league average batting
                               event frequency counts.
        stat_names {list} -- list of batting event outcomes

    Returns:
        {dict} -- dictionary of batting event probabilities
    """
    stat_dict = {}
    batter_rates = utils.normalize_dictionary(batter_stats)
    pitcher_rates = utils.normalize_dictionary(pitcher_stats)
    league_rates = utils.normalize_dictionary(league_stats)

    for stat in stat_names:
        # TODO: is there a better way to handle hit by pitches?
        if stat == 'HBP':
            stat_dict['HBP'] = batter_rates['HBP']
        else:
            stat_dict[stat] = utils.predict_prob(batter_rates[stat],
                                                 pitcher_rates[stat],
                                                 league_rates[stat])

    # TODO: Is there a better way to adjust this so that P(sample) = 1
    normalized_stat_dict = utils.normalize_dictionary(stat_dict)

    return normalized_stat_dict


def custom_adjust_prior(prior, stat_dict):
    PRIOR_STRENGTH = 200
    prior_obs = sum(prior.values())
    for stat_name in stat_dict:
        # make the projection's strength as if there were <PRIOR_PA> PAs
        stat_rate = prior[stat_name] / prior_obs
        stat_dict[stat_name] += PRIOR_STRENGTH * stat_rate

    return stat_dict


def make_starter_adjustment(hitter_prior, similarity_dict, info, stat_names):
    """
    Adjusts batter projections for the startng pitcher faced.

    Adjusts projections for handedness of the pitcher, the stadium the game will
    be played in, the skill of the pitcher, and other custom adjustments.

    Arguments:
        hitter_prior {dict} -- batter's park neutral projections
        similarity_dict {dict} -- custom stat dictionary creating for adjusting
                                  batter's batting rates
        info {dict} -- dictionary of relevant game and player info
        stat_names {list} -- list of batting events

    Returns:
        {dict} -- dictionary of batting event probabilities
    """
    # get pitcher projections
    pitcher_prior = player_projections.get_pitcher_projection(info, stat_names)
    # estimate a pitcher's singles, doubles, and triples allowed from total hits
    pitcher_prior = player_projections.infer_hit_types(pitcher_prior, hitter_prior)

    # get the relevant bat hand that a switch hitter will use in the game
    info['bat_hand'] = get_game_bat_hand(info)

    # adjust priors for splits data
    hitter_splits = splits.adjust_splits(info, hitter_prior)
    pitcher_splits = splits.adjust_splits(info, pitcher_prior)
    # league average stats for the relevant batter handedness vs pitcher
    # handedness matchup
    league_splits = splits.get_league_stats(info)

    # TODO: do we want to make these adjustments for relievers or only starters?
    # NOTE: exactly when this adjustment is made depends on what adjustments
    #       this method is actually performing. If we add new features to
    #       custom_adjust_prior it will likely need to called in a different
    #       line in make_starter_adjustments
    adj_hitter_splits = custom_adjust_prior(hitter_splits, similarity_dict)

    # adjust projections for the games stadium
    hitter_rates = pf.custom_park_adjust_stats(adj_hitter_splits, info, neutralize=False)
    pitcher_rates = pf.custom_park_adjust_stats(pitcher_splits, info, neutralize=False)
    league_rates = pf.custom_park_adjust_stats(league_splits, info, neutralize=False)

    batting_rates = prepare_matchup_batting_rates(hitter_rates, pitcher_rates,
                                                  league_rates, stat_names)

    return batting_rates


def prepare_player_stats(info, stat_names, stat_dict):
    hitter_prior = player_projections.get_hitter_projection(info, stat_names)

    # TODO: Where and when to implement recent performance? Here?

    if info['pitcher_role'] == 'Starter':
        batting_rates = make_starter_adjustment(hitter_prior, stat_dict, info,
                                                stat_names)
    else:
        # NOTE: We assume relief pitchers are generic league average pitchers so
        #       we do not perform any pitcher specific adjustments for them
        hitter_rates = pf.custom_park_adjust_stats(hitter_prior, info, neutralize=False)
        batting_rates = utils.normalize_dictionary(hitter_rates)
    stat_list = utils.listify_stat_dict(batting_rates)

    return stat_list


def get_game_bat_hand(info):
    """

    Returns the bat hand of a switch hitter dependent on the starting pitcher

    Arguments:
        info {dict} -- A dictionary of relevant game info
    """
    if info['pitcher_role'] == 'Starter' and info['bat_hand'] == 'S':
        if info['opp_pitcher_hand'] == 'R':
            return 'L'
        elif info['opp_pitcher_hand'] == 'L':
            return 'R'
        else:
            print("Error! Invalid pitcher hand: %s" % info['opp_pitcher_hand'])
    else:
        return info['bat_hand']


def prepare_rel_info(data_handler, info, bat_order, mlb_id, team_type, bat_type):
    if team_type + "_bat_hands" in info:
        bat_hand = info[team_type + "_bat_hands"][bat_order]
    else:
        bat_hand = data_handler.get_batter_hand(mlb_id)

    team_id = info[team_type + '_team_id']
    if team_type == 'home':
        opp_team_id = info['away_team_id']
        opp_pitcher_id = info['away_pitcher_id']
        opp_pitcher_hand = info['away_pitcher_hand']
    elif team_type == 'away':
        opp_team_id = info['home_team_id']
        opp_pitcher_id = info['home_pitcher_id']
        opp_pitcher_hand = info['home_pitcher_hand']
    else:
        print('Error! Invalid team_type: %s' % team_type)

    rel_info = {'mlb_id': mlb_id, 'game_time': info['game_time'],
                'team_id': team_id, 'opp_team_id': opp_team_id,
                'stadium': info['stadium'], 'year_id': info['year_id'],
                'bat_hand': bat_hand, 'bat_order': bat_order,
                'opp_pitcher_id': opp_pitcher_id, 'opp_pitcher_hand': opp_pitcher_hand,
                'pitcher_role': 'Reliever', 'bat_type': bat_type,
                'is_pitcher': mlb_id == info[team_type + "_pitcher_id"]}
    # TODO: Are we adjusting with correct park factor year? Do we want the
    #       year of the game or the train year for the relevant park factor?
    # TODO: If optimizing live we should use current year park factors. If
    #       retrodicting we should use the training year park factors.
    rel_info['year_id'] = int(data_handler.train_year)

    return rel_info


def prepare_team_object(data_handler, info, team_type, bat_type):
    """
    data_handler is an instance of StatLoader with all the historical stats
    Takes as input the info dictionary with game info
    Normalizes cumulative player stats and puts them in the right order
    Creates a Team object and stores it back in the info dict
    team_type should be either 'away' or 'home'
    """
    team_pitcher_mlb_id = info[team_type + "_pitcher_id"]
    team_pitcher_hand = info[team_type + "_pitcher_hand"]
    # TODO: make sure that all parameters are right. e.g. bat_hand correct

    pitcher = Pitcher(role="Starter", pid=team_pitcher_mlb_id, hand=team_pitcher_hand)

    players = []

    stat_names = list(br.batting_events)

    for i, mlb_id in enumerate(info[team_type + '_batter_ids']):

        rel_info = prepare_rel_info(data_handler, info, i, mlb_id, team_type, bat_type)

        # Create predicted stats vs generic pitcher to be used for relievers
        rp_stat_dict = data_handler.get_player_stats(mlb_id, rel_info['pitcher_role'])
        rp_predicted_stats = prepare_player_stats(rel_info.copy(), stat_names, rp_stat_dict)

        rel_info['pitcher_role'] = 'Starter'
        # Create predicted stats vs starting pitcher
        sp_stat_dict = data_handler.get_player_stats(mlb_id, rel_info['pitcher_role'])
        sp_predicted_stats = prepare_player_stats(rel_info.copy(), stat_names, sp_stat_dict)

        assert(rel_info['pitcher_role'] == 'Starter')

        defensive_pos = info[team_type + "_fielder_pos"][i]
        if rel_info['bat_hand'] == 'S':
            switch_hitter = True
        else:
            switch_hitter = False
        # Sets switch hitters opposite starter's hand
        # Used for player_customizations that adjust certain handedness
        # NOTE: they are treated as that handedness against relievers as well
        rel_info['bat_hand'] = get_game_bat_hand(rel_info)

        player = Player(pid=mlb_id, position=defensive_pos,
                        bat_hand=rel_info['bat_hand'], switch_hitter=switch_hitter)
        player.set_sp_batting_rates(sp_predicted_stats)
        player.set_rp_batting_rates(rp_predicted_stats)

        if rel_info['is_pitcher']:
            pinch_hitter_rates = get_pinch_hitter_rates(rel_info)
            player.set_pinch_hitter_rates(pinch_hitter_rates)
            pitcher.batting_pos = i
        players.append(player)

    team = Team(lineup=players,
                team_id=info[team_type + "_team_id"],
                starting_pitcher=pitcher)
    info[team_type + "_team"] = team
    return team
