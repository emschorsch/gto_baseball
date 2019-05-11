#!/usr/bin/python

import numpy as np
import pandas as pd

import argparse

import unidecode
import os
import datetime

directory = os.path.dirname(os.path.abspath(__file__)) + '/../fixtures/'
id_map = pd.read_csv(directory + "sfbb_playeridmap.csv", dtype="str", encoding="latin-1")
id_map = id_map[["MLBID", "TEAM", "POS", "PLAYERNAME", "DRAFTKINGSNAME", "BATS", "THROWS"]]
# If the DKNAME for a player is missing just use PLAYERNAME
null_dk_rows = pd.isnull(id_map["DRAFTKINGSNAME"])
id_map.loc[null_dk_rows, "DRAFTKINGSNAME"] = id_map.loc[null_dk_rows, "PLAYERNAME"]
del id_map["PLAYERNAME"]

full_team_map = pd.read_csv(directory + "sfbb_mlbteammap.csv", dtype="str")
team_map = full_team_map[["DKTEAM", "SFBBTEAM", "RETROTEAM", "DIFFTOEST"]].copy()
team_map["DIFFTOEST"] = team_map["DIFFTOEST"].astype(int)
id_map = id_map.merge(team_map, left_on="TEAM", right_on="SFBBTEAM")
id_map = id_map.drop(["TEAM", "SFBBTEAM", "DIFFTOEST"], axis=1)


def process_dk_lineups(year, date):
    """
    Assumes DKSalaries.csv (from exportData in contest on DK) is in Downloads.
    For each player tries to find corresponding MLB_ID and bat order if starting.
    Prints out unmerged players.
    Writes processed player info to fixtures/salaries/dk so optimizer can run.
    """
    # TODO: If date is today get DKSalaries. Else get DKSalaries_<date>

    downloaded_dk_file = os.path.expanduser("~/Downloads/DKSalaries.csv")
    player_data = process_dk_data(year, date, downloaded_dk_file)

    live_lineups = collect_lineup_info(player_data["Team"].unique(), year, date)
    merged_data = merge_lineup_info(player_data, live_lineups)

    os.rename(downloaded_dk_file, downloaded_dk_file[:-4] + "_old.csv")

    file_format = "fixtures/salaries/dk/{}/playerInfo_{}.csv"
    filename = file_format.format(year, date.lstrip("0"))
    merged_data = merged_data.sort_values(by=["local hour", "GameInfo", "Team",
                                              "starter", "Bat order", "Name"])
    merged_data.to_csv(filename, index=False)
    return merged_data


def process_dk_data(year, date, dk_salaries_filename):
    """
    Reads in the player info downloaded from DK.
    Attempts to get MLB_IDs from id_map by merging on DKNAME.
    Crashes if multiple players with same name
    """
    player_data = pd.read_csv(dk_salaries_filename, sep=",", encoding="latin-1")
    player_data = player_data.rename(columns={"Name": "orig name"})
    player_data["Date"] = str(year) + date

    player_data = prepare_player_data(player_data)

    # Hard to handle players who've changed teams like Ruben Tejada.
    # For now merge on name only.
    # Should merge on Team after that way it'll be clear the merge is incomplete
    # but we won't have to look up the mlb_id again if it's correct.
    # better to merge and create duplicate rows if 2 players share a name
    # Then mlb_id easily accessible. All we have to do is delete the column.
    # TODO: will break if two players have the same name in id_map?
    orig_num_players = len(player_data)
    player_data = player_data.merge(id_map, how="left",
                                    left_on=["Name"],
                                    right_on=["DRAFTKINGSNAME"],
                                    ).sort_values(by="Team")
    del player_data["DRAFTKINGSNAME"]
    del player_data["DKTEAM"]
    player_data.rename(columns={'RETROTEAM': 'mapped Team'}, inplace=True)

    # Make sure didn't eliminate or duplicate players while merging
    assert(orig_num_players == len(player_data))

    switch_map = {"B": "S"}
    player_data.replace(to_replace={'BATS': switch_map,
                                    'THROWS': switch_map}, inplace=True)
    # Set batters to not have a throwing hand
    pitchers = player_data["POS"] == "P"
    player_data.loc[~pitchers, "THROWS"] = ''

    return player_data.rename(columns={'Salary': 'DK sal', 'Position': 'DK posn',
                                       'MLBID': 'MLB_ID',
                                       'BATS': 'bat_hand', 'THROWS': 'pit_hand'})


def prepare_player_data(player_data):
    """
    Manipulates the DK player info into a mergeable format.
    Infers info like day_night and local time and standardizes Team and pos.
    """
    num_orig_players = len(player_data)

    # Replace accents and other non-ascii characters
    player_data["Name"] = player_data["orig name"].apply(lambda x: unidecode.unidecode(x))
    assert((player_data["Name"].str.len() == player_data["Name"].str.len()).all())

    player_data["Position"] = player_data["Position"].str.replace("SP", "P")
    player_data["Position"] = player_data["Position"].str.replace("RP", "P")

    # Extract Stadium ID and map it to corresponding RETROTEAM ID
    player_data["stadium"] = player_data["GameInfo"].apply(
        lambda x: x.split(' ')[0].split('@')[1].upper())
    player_data = player_data.merge(team_map[["DKTEAM", "RETROTEAM", "DIFFTOEST"]],
                                    left_on="stadium", right_on="DKTEAM")
    assert(len(player_data) == num_orig_players), player_data["stadium"].value_counts()
    player_data["stadium"] = player_data["RETROTEAM"]
    del player_data["DKTEAM"]
    del player_data["RETROTEAM"]

    # Makes sure all the times are in ET
    assert(player_data["GameInfo"].apply(lambda x: x.split(' ')[2] == 'ET').all())
    # Now map to local time zones and check if day or night game (5pm or later)
    player_data["local hour"] = player_data["GameInfo"].apply(
        lambda x: datetime.datetime.strptime(x.split(' ')[1], '%I:%M%p').hour)
    player_data["day_night"] = player_data["local hour"] + player_data["DIFFTOEST"]
    player_data["day_night"] = np.where(player_data["day_night"] >= 17, "N", "D")

    # Map the player's Team ID to the corresponding RETROTEAM ID
    player_data["teamAbbrev"] = player_data["teamAbbrev"].str.upper()
    player_data = player_data.merge(team_map[["DKTEAM", "RETROTEAM"]],
                                    left_on="teamAbbrev", right_on="DKTEAM")
    assert(len(player_data) == num_orig_players), player_data["teamAbbrev"].value_counts()
    player_data["Team"] = player_data["RETROTEAM"]

    return player_data.drop(["DKTEAM", "teamAbbrev", "RETROTEAM"], axis=1)


def merge_lineup_info(player_data, live_lineups):
    """
    Partially merges the DK salary and player info with the projected lineups.
    For successfully merged teams non-starting players are removed.
    For unmerged players as much information as can be mapped is added.
    The rest is left to be filled in by the user.
    """
    orig_team_counts = live_lineups["Team"].value_counts().to_dict()

    # Try to merge on MLB_ID and handle players without MLB_IDs in player_data
    right_merge = live_lineups.merge(player_data, on="MLB_ID", how="left",
                                     indicator=True)
    unmerged_players = right_merge[right_merge["_merge"] == "left_only"]
    unmerged = live_lineups[live_lineups["MLB_ID"].isin(unmerged_players["MLB_ID"])]
    name_merge = player_data.merge(unmerged, on=["Name", "Team"], how="right",
                                   suffixes=["", "_bpress"], indicator=True)
    for i, row in name_merge.iterrows():
        if row["_merge"] != "both":
            continue
        # These are all players whose DRAFTKINGSNAME is wrong in sfbb_idmap.
        # TODO: Should probably fix in sfbb_idmap at some point.
        team_match = player_data["Team"] == row["Team"]
        name_match = player_data["Name"] == row["Name"]
        assert((team_match & name_match).sum() == 1)
        matching_row = (team_match & name_match).tolist()
        player_data.loc[matching_row, "MLB_ID"] = row["MLB_ID_bpress"]

    merged_data = player_data.merge(live_lineups, on="MLB_ID", how="left",
                                    suffixes=["", "_bpress"], indicator=True)

    unmapped_players = name_merge[name_merge["_merge"] == "right_only"]
    if len(unmapped_players) == 0:
        print("All players in lineups mapped")
    else:
        print("----/" * 12)
        print("\n\tUNMAPPED PLAYERS in lineups!!:\n\t ", unmapped_players)
        print("----/" * 12)
    del name_merge

    for team, counts in live_lineups["Team"].value_counts().to_dict().items():
        assert(counts == orig_team_counts[team])

        # If we have all the players delete the rest from player_data
        if counts == 10 and (merged_data["Team_bpress"] == team).sum() == 10:
            # Have complete lineup so throw out non starting players on team
            team_players = (merged_data["Team_bpress"] == team)
            other_team_players = (merged_data["Team"] != team)
            merged_data = merged_data[team_players | other_team_players]

    # Overwrite where succesfuly merged.
    # Uses the more accurate baseballpress info. Then removes redundant columns
    matched_rows = merged_data["_merge"] == "both"
    redundant_cols = ["Team_bpress", "bat_hand_bpress", "pit_hand_bpress", "Position"]
    scraped_data = merged_data.loc[matched_rows, redundant_cols].values
    merged_data.loc[matched_rows, ["Team", "bat_hand", "pit_hand", "POS"]] = scraped_data

    merged_data["DK name"] = merged_data["orig name"]
    cols_to_drop = ["DIFFTOEST", "mapped Team", "game_id", "Name_bpress",
                    "orig name", "_merge"]
    return merged_data.drop(redundant_cols + cols_to_drop, axis=1)


def collect_lineup_info(elig_teams, year, date):
    """
    Retrieve the projected lineup for <date>.
    Restrict to players in games eligible for the chosen DK contest
    """
    # baseballpress_scraper imports scrapy so keep import in this function
    from tools import baseballpress_scraper
    live_lineups = baseballpress_scraper.run(year, date)
    live_lineups = live_lineups.merge(full_team_map[["BASEBALLPRESSTEAM", "RETROTEAM"]])
    del live_lineups["BASEBALLPRESSTEAM"]
    live_lineups.rename(columns={"RETROTEAM": "Team"}, inplace=True)
    live_lineups["MLB_ID"] = live_lineups["MLB_ID"].astype(str)

    # Restrict to players that are eligible for the considered DK contest
    relevant_players = live_lineups["Team"].isin(elig_teams)
    return live_lineups[relevant_players].copy()


def handle_lineup_uploading(year, date):
    # TODO: call this after we check the file by hand and the bat_spots are all
    # correct. It will make sure there's 10 per team and the right positions.
    # Then it will push it to the server. and maybe run the simulator as well
    file_format = "fixtures/salaries/dk/{}/playerInfo_{}.csv"
    filename = file_format.format(year, date.lstrip("0"))

    player_data = pd.read_csv(filename, encoding="latin-1")

    starters = player_data[player_data["starter"].notnull()]
    sanity_checks(starters)

    import ipdb; ipdb.set_trace()  # XXX BREAKPOINT
    return player_data


def sanity_checks(starters):
    """
    Performs basic checks on the lineups to make sure they're plausible.
    Ensures the csv is written using the expected format with 10 players per team
        and the pitcher appearing twice in the NL
    """
    # TODO: raise meaningful exceptions instead of these assertions (if compile
    # with -O these could be silently turned off)
    grouped = starters.groupby("Team")
    for team in grouped.groups:
        team_players = grouped.get_group(team)
        # TODO: use 0s and 1s instead of Null Not Null?

        assert(len(team_players) == 10), team_players
        # Make sure one player for each spot in batting order
        assert((team_players["Bat order"].value_counts() == 1).all()), team_players
        # Make sure bat order has 0-8 spots and a pitcher
        assert((team_players["Bat order"].isnull() | (team_players["Bat order"] < 9)).all()), team_players

    # Makes sure that SP and RP aren't in POS
    valid_positions = set(['P', 'C', '1B', '2B', '3B', 'SS',
                           'OF', 'RF', 'CF', 'LF', 'DH'])
    if not set(starters["POS"].unique()).issubset(valid_positions):
        valid_pos_players = starters["POS"].isin(valid_positions)
        print("NOT VALID POSITIONS\n", starters[~valid_pos_players]["POS"].unique())
        print(starters[~valid_pos_players])
        raise AssertionError("Invalid positions")

    # Make sure each batter only appears once
    batters = starters[starters["Bat order"].notnull()]
    assert((batters["MLB_ID"].value_counts() == 1).all())
    assert(set(batters["bat_hand"].unique()).issubset(["R", "L", "S"])), batters["bat_hand"].unique()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Processes the DK salary info for <year> and <date>')
    parser.add_argument("--year", nargs='?', default='2016',
                        help="the year to collect data for")
    parser.add_argument("--date", nargs='?',
                        help="the date the DK lineup file is for")
    parser.add_argument("--upload", nargs='?', default='false',
                        help="the date the DK lineup file is for")

    args = parser.parse_args()
    if args.date is None:
        raise TypeError("Must specify the date the DK file is for")

    if args.upload.lower() == "false":
        process_dk_lineups(args.year, args.date)
    else:
        handle_lineup_uploading(args.year, args.date)
