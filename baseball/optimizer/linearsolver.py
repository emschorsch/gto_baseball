"""
Linear Solver for optimal Draftkings lineup
Author: Emanuel Schorsch 2015
"""

# Import PuLP modeller functions
import pulp

import pandas as pd
import time


def optimizeLineup(playerData, num_solutions=1):
    """
    Takes as input a pandas dataframe. Each row is a player
    Columns required are Team, DK posn, DK sal, DK pts, Name and MLB_ID
    Finds the lineup that produces maximum fantasy points.
    The lineup will satisfy DraftKings requirements
    """
    # List of all the players
    Players = playerData.index

    # Creates the player Variables as Integers
    player_vars = pulp.LpVariable.dicts("Player", Players, 0, 1, pulp.LpInteger)

    # Creates the game Variables as Integers
    game_vars = pulp.LpVariable.dicts("Game", playerData["game_id"].unique(),
                                      0, 1, pulp.LpInteger)

    # Creates the team stack Variables as Integers
    team_stack_vars = pulp.LpVariable.dicts("Team stack", playerData["Team"].unique(),
                                            0, 1, pulp.LpInteger)

    # Creates the 'prob' variable to contain the problem data
    prob = pulp.LpProblem(name="DFS Optimization", sense=pulp.LpMaximize)

    # Creates the objective function to maximize fantasy points
    prob += pulp.lpSum([player_vars[pid] * playerData.loc[pid, "custom DK pts pred"]
                        for pid in Players]), "Maximize DFS score"

    # TODO: would dividing salaries and constrains by 100 make this run faster?
    # Constraint that salary is below 50,000
    prob += pulp.lpSum([player_vars[pid] * playerData.loc[pid, "DK sal"]
                        for pid in Players]) <= 50000, "Salary constraint"

    # Constraint that lineup can only have 10 players
    prob += pulp.lpSum([player_vars[pid] for pid in Players]) == 10, "10 players"

    # Adds a constraint so that multi_position players are only chosen once
    grouped = playerData.groupby("MLB_ID")
    for mlb_id in grouped.groups:
        rows = grouped.get_group(mlb_id)
        if len(rows) != 1:
            prob += pulp.lpSum([player_vars[pid] for pid in rows.index]) <= 1

    # Sets up and enforces that we have chosen players from at least 2 games
    grouped = playerData.groupby("game_id")
    for game in grouped.groups:
        game_player_ids = grouped.get_group(game).index

        if len(game_player_ids) == 1:
            prob += pulp.lpSum([-1*game_vars[game]] + [game_player_ids[0]]) == 0
        else:
            # The game variable can't be 1 if 0 players from game are 1
            # NOTE: that game variable can always be 0 but that wouldn't help it
            # satisfy the linear constraint of >= 2 games
            prob += pulp.lpSum([-1*game_vars[game]] +
                               [player_vars[pid] for pid in game_player_ids]) >= 0, game + " indicator variable constraint"
    prob += pulp.lpSum(game_vars.values()) >= 2, "at least 2 games among players"

    # Sets up and enforces that we have at least 1 stack of <MIN_STACK_LENGTH>
    #    batters put in the lineup.
    grouped = playerData.groupby("Team")
    for team in grouped.groups:
        team_player_ids = grouped.get_group(team)
        team_hitters = team_player_ids[team_player_ids["DK posn"] != "P"].index

        if len(team_hitters) == 1:
            continue

        # Set this to 1 if no stack should be required
        MIN_STACK_LENGTH = 1
        # The team_stack variable can't be 1 if <4 players from game are 1
        # NOTE: that game variable can always be 0 but that wouldn't help it
        # satisfy the linear constraint of >= 1 stacked teams
        prob += pulp.lpSum([-1*MIN_STACK_LENGTH*team_stack_vars[team]] +
                           [player_vars[pid] for pid in team_hitters]) >= 0, team + " indicator variable constraint"
    prob += pulp.lpSum(team_stack_vars.values()) >= 1, "at least 1 stacked team"

    # Adds a constraint that we have at most 5 batters from any team
    grouped = playerData.groupby("Team")
    for team in grouped.groups:
        team_players = grouped.get_group(team)
        team_hitters = team_players[team_players["DK posn"] != "P"].index
        prob += pulp.lpSum([player_vars[pid] for pid in team_hitters]) <= 5, team + " restrict to 5 hitters"

    # Constraint that we have 2 pitchers
    pitchers = playerData.loc[playerData["DK posn"] == "P"].index
    prob += pulp.lpSum([player_vars[pid] for pid in pitchers]) == 2, "2 pitchers"

    # Constraint that we have 1 of each type
    for pos in ["C", "1B", "2B", "3B", "SS"]:
        pos_players = playerData.loc[playerData["DK posn"] == pos].index
        prob += pulp.lpSum([player_vars[pid] for pid in pos_players]) == 1, "1 of position: "+str(pos)

    # Constraint that we have 3 outfielders
    outfielders = playerData.loc[playerData["DK posn"] == "OF"].index
    prob += pulp.lpSum([player_vars[pid] for pid in outfielders]) == 3, "3 OF"

    # Initial empty frame to keep track of all the optimal lineups
    results = playerData[playerData["DK posn"] == -1]
    relevant_cols = ["MLB_ID", "Name", "Team", "game_id", "bat_hand", "switch_hitter",
                     "DK posn", "DK sal", "DK pts pred", "custom DK pts pred"]
    results = results[relevant_cols]

    # The problem data is written to an .lp file
    prob.writeLP("LineupOptimizer.lp")

    # TODO: check if sequentialSolve would make it go faster?
    # currently using actualSolve
    # How long does restoreObjective take too run in solve? because could cut
    # that out by just calling actualSolve directly:
    # https://github.com/coin-or/pulp/blob/master/src/pulp/pulp.py
    for i in range(1, num_solutions+1):
        if i % 50 == 0:
            print("on lineup# ", i, " time is: ", time.time())

        # The problem is solved using PuLP's choice of Solver
        prob.solve()

        # Copy structure from playerData
        lineup = results[results["DK posn"] == -1]
        lineupPids = []

        # Each of the variables is printed with it's resolved optimum value
        for v in prob.variables():
            if v.varValue == 1 and str(v)[:6] == "Player":
                ID = str(v).split('_')[1]  # extract the player id
                lineupPids.append(ID)
                info = playerData.loc[ID, relevant_cols]
                lineup = lineup.append(info)

        lineup["custom pred total"] = pulp.value(prob.objective)
        # Add a blank line after the lineup to make it visually easier
        lineup = lineup.append({}, ignore_index=True)
        lineup["Lineup"] = i
        results = results.append(lineup)

        if i == 1:
            # If no solution that satisfies constraints return early
            status = pulp.LpStatus[prob.status]
            if status != "Optimal":
                return results, status

        # Remove lineup from solution set
        prob += pulp.lpSum([player_vars[pid] for pid in lineupPids]) <= 9

    results = results.sort_values(by=['Lineup', 'DK posn']).reset_index()
    return (results[['Lineup'] + relevant_cols + ["custom pred total"]],
            pulp.LpStatus[prob.status])

if __name__ == "__main__":
    filename = "../../fixtures/playerInfo_9_04_14.csv"
    read_player_data = pd.read_csv(filename, sep=";")
    # playerData.loc[595191, "Date"]
    results, status = optimizeLineup(read_player_data, num_solutions=3)
    print(results, status)
