# For functions that are not used directly in main

import copy
# from datetime import datetime, timedelta
# from io import StringIO

# import numpy as np
import pandas as pd
# import requests
# from bs4 import BeautifulSoup

# import NCAApy.variables as v

# pd.set_option("display.max_rows", None)
# pd.set_option("display.max_columns", None)
# pd.set_option("display.width", None)
# pd.set_option("display.max_colwidth", None)
# takes the play by play sheet and returns 5 starters

# TODO: Convert global variable `headers` into a function call
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " +
    "AppleWebKit/537.36 (KHTML, like Gecko) " +
    "Chrome/58.0.3029.110 Safari/537.3",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


def get_starters(pbp):
    col_names = pbp.columns.tolist()  # used to get the name of teams
    starters = [[], None, []]
    benches = [[], None, []]
    for n in [0, 2]:
        for event in pbp[f"{col_names[n + 1]}"].dropna():
            player = event.split(",")[0]
            if player == "Team":
                continue
            if "substitution in" in event:
                if player not in starters[n]:
                    benches[0].append(player)
            elif "substitution out" in event:
                if (
                    player not in starters[n]
                    and len(starters[n]) < 5
                    and player not in benches[n]
                ):
                    starters[n].append(player)
                if len(starters[n]) == 5:
                    break
            elif (
                player not in starters[n]
                and player not in benches[n]
                and len(event.split(",")) > 1
            ):
                starters[n].append(player)
                if len(starters[n]) == 5:
                    break
    starters.pop(1)
    return starters


def get_positions(stats):
    # dfs = pd.read_html(stats)[3:]
    away_positions = dict(zip(stats[0]["Name"], stats[0]["P"]))
    home_positions = dict(zip(stats[1]["Name"], stats[1]["P"]))
    return [away_positions, home_positions]


def order_players(players, positions):
    lineup = []
    roles = ["G", "F", "C"]
    for role in roles:
        for starter in players:
            if positions[starter] == role:
                lineup.append(starter)
    return lineup


def to_lineup_df(pbp, starters, positions, is_home):
    col_names = pbp.columns.tolist()
    if is_home:
        col = 3
    else:
        col = 1
    in_game = order_players(starters, positions)
    before = in_game
    finished_lists = []
    for event in pbp[f"{col_names[col]}"]:
        if pd.isna(event):
            finished_lists.append(before)
            continue
        if "substitution out" in event:
            in_game.remove(event.split(",")[0])
        if "substitution in" in event:
            in_game.append(event.split(",")[0])
        if len(in_game) == 5:
            before = in_game
        before = order_players(before, positions)
        finished_lists.append(before)

    to_add = pd.DataFrame(finished_lists)
    to_add.columns = [
        f"{col_names[col]}_1",
        f"{col_names[col]}_2",
        f"{col_names[col]}_3",
        f"{col_names[col]}_4",
        f"{col_names[col]}_5",
    ]
    return to_add


def split_event(event):
    if ", " in event:
        return event.split(", ", 1)[::-1]
    else:
        return [event, pd.NA]


def swap_rows(pbp, row_1, row_2):
    rows = pbp.index.tolist()
    old = copy.deepcopy(rows)
    temp = rows[rows.index(row_1)]
    rows[rows.index(row_1)] = row_2
    rows[old.index(row_2)] = temp
    pbp = pbp.reindex(rows)
    return pbp


def event_packer(pbp):
    packages = []
    extra = 1
    for index, time in enumerate(pbp["Time"]):
        package = []
        if extra > 1:
            extra -= 1
            continue
        extra = 1
        package.append(index)
        while index + extra < len(pbp) and time == pbp["Time"][index + extra]:
            package.append(index + extra)
            extra += 1
        packages.append(package)

    return packages


def time_convert(time_str, half, total_halves):
    # Split the time into minutes, seconds, and milliseconds
    minutes, seconds, _ = map(int, time_str.split(":"))

    # Calculate the total seconds passed in the current half
    if half <= 2:
        time_passed_in_seconds = 1200 - (minutes * 60 + seconds)
    else:
        time_passed_in_seconds = 300 - (minutes * 60 + seconds)

    # Determine if the current half is a regular half (1st or 2nd) or overtime
    if half <= 2:
        # 20-minute halves
        total_time_in_half = 1200
    else:
        # Overtime halves
        total_time_in_half = 300

    # Calculate remaining time in the current half
    remaining_in_current_half = total_time_in_half - time_passed_in_seconds

    # Calculate remaining time in all subsequent halves
    remaining_in_future_halves = 0
    for h in range(half + 1, total_halves + 1):
        if h <= 2:
            remaining_in_future_halves += 1200
        else:
            remaining_in_future_halves += 300

    # Total remaining time
    total_remaining_time = (
        remaining_in_current_half + remaining_in_future_halves
    )

    return total_remaining_time


def time_counter(time, half):
    minutes, seconds, _ = map(int, time.split(":"))
    time_played = minutes * 60 + seconds
    if half <= 2:
        time_played = 1200 - time_played
    else:
        time_played = 300 - time_played
    for n in range(half):
        if n == 1 or n == 2:
            time_played += 1200
        if n > 2:
            time_played + 300
    return time_played


def opponent_split(schedule, team):
    game_types = []
    locations = []
    events = []
    for index, opponent in enumerate(schedule["Opponent"]):
        team2 = schedule["Opponents"][index]
        # What are `x` and `y` used for?
        try:
            info = opponent.split(team2)[1].strip()
            y = opponent.split(team2)
        except:
            x = 0
        if opponent[0] == "@":
            game_types.append("Away")
            locations.append(team2)
        elif "@" in opponent:
            game_types.append("Neutral")
            locations.append(opponent.split("@")[-1].split("(")[0].strip())
        else:
            game_types.append("Home")
            locations.append(team)
        if len(info) > 1:
            events.append(info.split("(")[-1][:-1])
        else:
            events.append("Regular Season")

    schedule = schedule.drop(columns="Opponent")
    schedule["Event"] = events
    schedule["Venue"] = locations
    schedule["Game_type"] = game_types
    return schedule


def split_result(schedule, team):
    result = []
    team_score = []
    opp_score = []
    overtimes = []
    for index, res in enumerate(schedule["Result"]):
        if res == "Totals":
            result.append(pd.NA)
            team_score.append(pd.NA)
            opp_score.append(pd.NA)
            overtimes.append(pd.NA)
            continue
        if "W" in res:
            score_1 = int(res.split()[1].split("-")[0])
            score_2 = int(res.split()[1].split("-")[1])
            result.append("Win")
            if score_1 > score_2:
                team_score.append(score_1)
                opp_score.append(score_2)
            else:
                opp_score.append(score_1)
                team_score.append(score_2)
        elif "L" in res:
            score_1 = int(res.split()[1].split("-")[0])
            score_2 = int(res.split()[1].split("-")[1])
            result.append("Loss")
            if score_1 > score_2:
                opp_score.append(score_1)
                team_score.append(score_2)
            else:
                team_score.append(score_1)
                opp_score.append(score_2)
        else:
            opp_score.append(pd.NA)
            team_score.append(pd.NA)
            overtimes.append(pd.NA)
            result.append("Canceled")
            continue
        if "(" in res:
            overtimes.append(int(res.split("(")[1].split()[0]))
        else:
            overtimes.append(0)
    schedule = schedule.drop(columns="Result")
    schedule[f"{team}_score"] = team_score
    schedule["Opponent_score"] = opp_score
    schedule["Result"] = result
    schedule["Overtimes"] = overtimes
    return schedule


def clean_and_cast(player_stuff, column):
    new_col = []
    for index, cell in enumerate(player_stuff[column]):
        if isinstance(cell, str):
            cell = cell.split("/")[0]
            cell = int(cell)
            new_col.append(cell)
        else:
            cell = int(cell)
            new_col.append(cell)
    player_stuff[column] = new_col
    return player_stuff
