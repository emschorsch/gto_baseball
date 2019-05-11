NUM_STATS = 11

RBI = 0
RUN = 1
SINGLE = 2
DOUBLE = 3
TRIPLE = 4
HR = 5
BB = 6
HBP = 7
SB = 8
CS = 9
OUT = 10

# Make sure this is kept in sync with definitions above
stats = ('RBI', 'RUN', 'SINGLE', 'DOUBLE', 'TRIPLE', 'HR',
         'BB', 'HBP', 'SB', 'CS', 'OUT')

# DK points weighting for each stat corresponding to stats above
# WARNING: If order is changed above must change this order
DK_multiplier = [2, 2, 3, 5, 8, 10, 2, 2, 5, 0, 0]


def compute_dk_multiplier():
    """
    Helper method to compute what the dk_multiplier ought to be in order to
        match the order of the indexing in <stats>
    """
    multiplier = [0]*NUM_STATS
    dk_scores = {'RBI': 2, 'RUN': 2, 'SINGLE': 3, 'DOUBLE': 5, 'TRIPLE': 8,
                 'HR': 10, 'BB': 2, 'HBP': 2, 'SB': 5, 'CS': 0, 'OUT': 0}
    for key, val in dk_scores.items():
        multiplier[stats.index(key)] = val

    return multiplier
