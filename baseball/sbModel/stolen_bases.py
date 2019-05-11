import pandas as pd
import math
import random
import os

from baseball.simulator import utils


logger = utils.setup_logger('sb_logger', 'logs/sb.log')


# Converts the logodds into a propbability
def logodds_to_prob(x):
    prob = math.exp(x)/(1+math.exp(x))
    return prob


# Determines whether a random event occurs with porbability = prob_occur
def sucess_or_failure(prob_occur):

    if random.random() < prob_occur:
        return True
    else:
        return False


# Creates a dictionary from a csv
def createDict(csv_name):
    reader = pd.read_csv(csv_name)
    # pd.read_csv(csv_name, dtype={'key': 'str', 'result': 'float'})
    reader.columns = ['key', 'result']
    reader.key = reader.key.astype(str)
    reader_dict = dict(zip(reader.key, reader.result))
    return reader_dict


class StolenBases:
    def __init__(self):

        file_path = os.path.dirname(os.path.abspath(__file__)) + '/../../fixtures/'
        # TODO: looking in sb.log this is loaded once for each game when using
        # optimizer. Turn this into singleton to be faster?
        logger.info("Initializing from path: %s" % file_path)

        # fixef dictionaries contain the values of each of the fixed effects
        # terms for the stolen base probit regression model.
        attempt_fixef = createDict(file_path + 'sba_fixef.csv')
        success_fixef = createDict(file_path + 'sbs_fixef.csv')
        self.fixef = {"attempt": attempt_fixef, "success": success_fixef}

        attempt_runner = createDict(file_path + 'sba_runner.csv')
        attempt_pitcher = createDict(file_path + 'sba_pitcher.csv')
        attempt_catcher = createDict(file_path + 'sba_catcher.csv')
        attempt_ranef = {"runner": attempt_runner,
                         "pitcher": attempt_pitcher,
                         "catcher": attempt_catcher}
        success_runner = createDict(file_path + 'sbs_runner.csv')
        success_pitcher = createDict(file_path + 'sbs_pitcher.csv')
        success_catcher = createDict(file_path + 'sbs_catcher.csv')
        success_ranef = {"runner": success_runner,
                         "pitcher": success_pitcher,
                         "catcher": success_catcher}
        self.ranef = {"attempt": attempt_ranef, "success": success_ranef}

    def calc_prob_sb(self, sb_info, steal_phase):

        """
        Returns the probability of either an attempted stolen base or
        a successful stolen base attempt depending on parameter prob_type.
        sb_info contains all relevant situational info for determining the
        respective probability of success, including runner, pitcher, catcher,
        running_team, pitcher_hand, and inning state.
        """

        fixed_effects = self.calc_fixed_effects(sb_info, steal_phase)
        random_effects = self.calc_random_effects(sb_info, steal_phase)

        sum_effects = fixed_effects + random_effects
        prob_occur = logodds_to_prob(sum_effects)

        # Returns the probability of a stolen base attempt occurring
        return prob_occur

    # Returns the logodds of the random effects
    # Random effects are pitcher, runner, and catcher
    # If a player's not in the sample, then it's assumed his random effect is 0
    # TODO: Should runners defualt to leauge average, league min, or other?
    #
    # Runners print an error if we have no observations of them being on base
    # in a steal situation or attempting a steal.
    def calc_random_effects(self, sb_info, steal_phase):
        """
        Returns the random effects of the probit regression model.
        """

        ranef_dict = self.ranef[steal_phase]
        random_effects = 0
        # Add random effects for each position: 'runner', 'pitcher', 'catcher'
        for position in ranef_dict:
            pid = str(sb_info[position])
            # TODO: Should we remove 'Default' from ranef pitcher csv?
            if pid in ranef_dict[position]:
                random_effects += ranef_dict[position][pid]
            elif position == "runner" and steal_phase == "success":
                random_effects += 0
            else:
                logger.info("SB {} error! + {} ={}".format(steal_phase,
                                                           position, pid))
                ranef_dict[position][pid] = 0.0  # so it only logs once

        return random_effects

    # Returns the logodds of the fixed effects
    def calc_fixed_effects(self, sb_info, steal_phase):
        """
        Returns the fixed effects of the probit regression model.
        """

        if steal_phase == "attempt":
            fixef_fields = ['pitcher_hand', 'inning_state', 'runner_team']
            fixef_interaction_fields = ['runner_team:pitcher_hand',
                                        'runner_team:inning_state',
                                        'pitcher_hand:inning_state',
                                        'runner_team:pitcher_hand:inning_state']
        else:
            fixef_fields = ['pitcher_hand', 'inning_state']
            fixef_interaction_fields = ['pitcher_hand:inning_state']

        fixef_dict = self.fixef[steal_phase]
        fixed_effects = fixef_dict['(Intercept)']
        for fixef_field in fixef_fields:
            key = sb_info[fixef_field]
            # TODO: Allow errors until nosetests is edited.
            #       Remove if/else once nosetests is updated.
            if key in fixef_dict:
                fixed_effects += fixef_dict[key]
            else:
                logger.critical("Fatal SB error! {} ={}".format(fixef_field,
                                                                key))

        for interaction_field in fixef_interaction_fields:
            interaction_key = sb_info[interaction_field]
            fixed_effects += fixef_dict.get(interaction_key, 0)

        return fixed_effects
