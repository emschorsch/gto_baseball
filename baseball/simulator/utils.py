import pandas as pd
import numpy as np

from baseball.simulator import batting_rates_index as br
from baseball.simulator import misc_rates_index as mr

from baseball.simulator.player import Player

from functools import wraps
from time import time

import logging
import sys


def normalize_stats(stats):
        """
        Takes cumulative integer statistics and normalizes so sum is 1
        """
        if stats.ndim == 1:
            return stats/sum(stats)

        else:
            raise NotImplementedError("NOT IMPLEMENTED FOR 2d arrays")


def listify_stat_dict(stat_dict):
    stats = []
    for stat_name in br.batting_events:
        stats.append(stat_dict.get(stat_name, 0))
    return np.array(stats)


def lineup_from_batting_rates(rates):
    players = []
    for i in range(9):
        player = Player()
        player.set_sp_batting_rates(rates.ix[i])
        player.set_rp_batting_rates(rates.ix[i])
        players.append(player)
    return players


def lineup_zeroed_batting_rates():
    events = br.batting_events
    return pd.DataFrame(np.zeros((9, len(events))), columns=events)


def lineup_zeroed_misc_rates():
    events = mr.misc_events
    return pd.DataFrame(np.zeros((9, len(events))), columns=events)


def timing(f):
    @wraps(f)
    def wrap(*args, **kw):
        ts = time()
        result = f(*args, **kw)
        te = time()
        print('func:%r args:[%r, %r] took: %2.4f sec' %
              (f.__name__, args, kw, te - ts))
        return result
    return wrap


def setup_logger(name, log_name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(fmt='[%(asctime)s] %(levelname)s:%(name)s:%(message)s')

    file_handler = logging.FileHandler(log_name, mode='w')
    file_handler.setLevel(level=logging.DEBUG)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.WARNING)
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger
