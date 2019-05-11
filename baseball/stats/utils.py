#!/usr/bin/python

from baseball.simulator import batting_rates_index as br


# TODO: Add testing for utils file

def normalize_dictionary(freq_dict):
    """
    Nomarlizes a numerical dictionary so that the sum of all values equals 1.
    """
    prob_dict = {}
    obs = sum(freq_dict.values())
    for key in freq_dict:
        prob_dict[key] = freq_dict[key] / obs

    return prob_dict


def prob_to_odds(prob):
    """
    Converts a probability to an odds ratio.

    Arguments:
        prob {float} -- a probabilty in [0, 1]
    """
    return prob / (1 - prob)


def odds_to_prob(odds):
    """
    Converts and odds ratio to a probability.

    Arguments:
        odds {float} -- an odds ratio
    """
    return odds / (1 + odds)


def predict_prob(bat_prob, pit_prob, lg_prob):
    """
    Predicts the probablity of an outcome given the batter, pitcher, and league
    average probabilities of success.

    Based on Bill James' log5 method as described in:
    https://en.wikipedia.org/wiki/Log5
    http://www.baseballthinkfactory.org/btf/scholars/levitt/articles/batter_pitcher_matchup.htm

    Arguments:
        bat_prob {float} -- batter's probabilty of success
        pit_prob {float} -- pitcher's probability of success
        lg_prob {float} -- league average probability of success

    Returns:
        success_prob {float} -- the estimated probability of success for the
                                relevant matchup
    """
    bat_odds = prob_to_odds(bat_prob)
    pit_odds = prob_to_odds(pit_prob)
    lg_odds = prob_to_odds(lg_prob)
    success_odds = pit_odds * bat_odds / lg_odds
    success_prob = odds_to_prob(success_odds)

    return success_prob


def listify_stat_dict(stat_dict):
    stats = []
    for stat_name in br.batting_events:
        stats.append(stat_dict.get(stat_name, 0))
    return stats
