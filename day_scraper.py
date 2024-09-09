# All the functions needed for scrape_day

from datetime import datetime
import logging
import time

from bs4 import BeautifulSoup
import pandas as pd
import requests

import NCAApy.variables as v
from NCAApy.helpers import headers


# R: Properly working soup object of the webpage for the scoreboard results
# M: DataFrame 'day'
# E: Takes in DataFrame 'day' and collects the team names, and team_ids
def collect_teams(soup, day):
    away = []
    away_ids = []
    home = []
    home_ids = []  # initialize the columns
    teams_messy = soup.find_all(
        "td", class_="opponents_min_width"
    )  # Grabs all teams objects from webpage
    count = 0
    for team in teams_messy:
        # NCAA teams have a hyperlink which we're grabbing
        a_tag = team.find("a")
        temp = team.text.strip()  # Team name + Event location (if applicable)
        if len(temp.split("(")) > 1:
            # if event location is listed,  get only the team name
            team = " ".join(team.text.strip().split()[:-1]).strip()
        else:
            # otherwise its accurate
            team = temp
        if not a_tag:  # Team is not part of the NCAA, thus having no id
            if count % 2 == 0:  # Appends the team in the correct column
                away_ids.append(pd.NA)
                away.append(team)
            else:
                home_ids.append(pd.NA)
                home.append(team)
            count += 1
            # Work completed for iteration, thus no more needs to be done
            continue
        team_id = int(a_tag["href"].split("/")[-1])
        if count % 2 == 0:
            away_ids.append(team_id)
            away.append(team)
        else:
            home_ids.append(team_id)
            home.append(team)
        count += 1
    day["Away"] = away
    day["Home"] = home
    day["Away_id"] = away_ids
    day["Home_id"] = home_ids  # build the DataFrame column by column
    return day


# R: properly working soup object of scoreboard page
# M: DataFrame 'day'
# E: adds columns of information to the final DataFrame for all games
def collect_info(soup, day):
    game_infos = soup.find_all("td", colspan="10")  # grab all
    count = 0
    arenas = []
    events = []
    is_neutral = []
    times = []
    attendance = []  # Initialize Columns
    for index, info in enumerate(game_infos):
        info = info.text.split()
        if "/" not in info[0]:  # if there's no date, move on
            continue
        if len(info) < 4:
            # game was cancelled or is otherwise missing key information
            arenas.append(pd.NA)
            events.append(pd.NA)
            is_neutral.append(pd.NA)
            times.append(" ".join((info[1:])))
            attendance.append(pd.NA)
            count += 1
            continue
        if (
            index + 1 != len(game_infos)
            and "/" not in game_infos[index + 1].text.split()[0]
        ):
            description = game_infos[index + 1].text.split()
            if "@" not in description[0]:
                arenas.append(day["Home"][count])
                events.append(" ".join(description))
                is_neutral.append(False)
            for index2, part in enumerate(description):
                if "(" in part:
                    event = (
                        " ".join(description[index2:])
                        .replace("(", "")
                        .replace(")", "")
                    )
                    events.append(event)
                    break
                if "@" in part:
                    arena = " ".join(description[index2:])
                    arena = arena.replace("@", "").split("(")[0].strip()
                    arenas.append(arena)
                    is_neutral.append(True)
                    if "(" not in " ".join(description):
                        events.append("Regular Season")
        else:
            arenas.append(day["Home"][count])
            events.append("Regular Season")
            is_neutral.append(False)
        times.append(" ".join(info[1:3]))
        attendance.append(int(info[-1].replace(",", "")))
        count += 1
    day["Time"] = times
    day["Attendance"] = attendance
    day["Location"] = arenas
    day["Event"] = events
    day["is_Neutral"] = is_neutral
    return day


def collect_game_ids(soup, day):
    game_ids = []
    rows = soup.find_all("tr")
    count = 0
    for row in rows:
        try:
            if count % 4 == 0:
                if "Canceled" in row.get_text() or "Ppd" in row.get_text():
                    game_ids.append(pd.NA)
                else:
                    game_ids.append(int(row["id"].split("_")[-1]))
            count += 1
        except Exception as e:
            logging.warning(
                f"Unhandled exception in `collect_game_ids()`: `{e}`"
            )
            continue
    day["Game_id"] = game_ids
    return day


def collect_scores(soup, day):
    scores = soup.find_all("td", class_="totalcol")
    away_score = []
    home_score = []
    for index, score in enumerate(scores):
        if index % 2 == 0:
            away_score.append(score.text.strip())
        else:
            home_score.append(score.text.strip())
    day["Away_score"] = away_score
    day["Home_score"] = home_score
    return day


def get_day(date, conference_id, tournament_id, division, w, season_id):
    if isinstance(date, datetime):
        date = date.strftime("%m/%d/%Y")
    day = pd.DataFrame()
    year = int(date.split("/")[-1])
    if int(date.split("/")[0]) > 10:
        year += 1
    year_id = v.years[year]
    if division == 2:
        year_id += 2
    if division == 3:
        year_id += 4
    if w:
        year_id -= 1
    if season_id:
        year_id = season_id
    date2 = date.replace("/", "%2F")
    url = (
        "https://stats.ncaa.org/contests/livestream_scoreboards" +
        f"?utf8=%E2%9C%93&season_division_id={year_id}" +
        f"&game_date={date2}&conference_id={conference_id}" +
        f"&tournament_id={tournament_id}&commit=Submit"
    )
    response = requests.get(url, headers=headers)
    time.sleep(5)

    html_content = response.text
    soup = BeautifulSoup(html_content, "html.parser")
    day = collect_teams(soup, day)
    day = collect_info(soup, day)
    day = collect_game_ids(soup, day)
    day = day.dropna(subset=["Game_id"])
    day.reset_index(drop=True, inplace=True)
    day = collect_scores(soup, day)
    day["Date"] = date
    desired_order = [
        "Date",
        "Time",
        "Away",
        "Away_score",
        "Home",
        "Home_score",
        "Location",
        "Event",
        "is_Neutral",
        "Attendance",
        "Away_id",
        "Home_id",
        "Game_id",
    ]
    day = day[desired_order]
    return day
