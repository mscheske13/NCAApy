import logging
import time
from datetime import date, datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup
from dateutil import parser

import NCAApy.variables as v

# from NCAApy.helpers import *
from NCAApy.helpers import headers


def _collect_teams(soup, day):
    away_arr = []
    away_ids_arr = []
    home_arr = []
    home_ids_arr = []
    teams_messy = soup.find_all("td", class_="opponents_min_width")
    count = 0
    for team in teams_messy:
        a_tag = team.find("a")
        temp = team.text.strip()
        if len(temp.split("(")) > 1:
            team = " ".join(team.text.strip().split()[:-1]).strip()
        else:
            team = team.text.strip()
        if not a_tag:
            if count % 2 == 0:
                away_ids_arr.append(pd.NA)
                away_arr.append(team)
            else:
                home_ids_arr.append(pd.NA)
                home_arr.append(team)
            count += 1
            continue
        box = int(a_tag["href"].split("/")[-1])
        if count % 2 == 0:
            away_ids_arr.append(box)
            away_arr.append(team)
        else:
            home_ids_arr.append(box)
            home_arr.append(team)
        count += 1
    day["Away"] = away_arr
    day["Home"] = home_arr
    day["Away_id"] = away_ids_arr
    day["Home_id"] = home_ids_arr
    return day


def _collect_info(soup, day):
    game_infos = soup.find_all("td", colspan="10")
    count = 0
    arenas = []
    events = []
    is_neutral = []
    times = []
    attendance = []
    for index, info in enumerate(game_infos):
        info = info.text.split()
        if "/" not in info[0]:
            continue
        if len(info) < 4:
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
                        " ".join(description[index2:]).replace(
                            "(", ""
                        ).replace(")", "")
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


def _collect_game_ids(soup, day):
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
                "Unhandled exception in " +
                f"`NCAApy.day_scraper.collect_game_ids()`: {e}"
            )
    day["Game_id"] = game_ids
    return day


def _collect_scores(soup, day):
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


def get_day(
    game_date: datetime | date | str,
    season_id: int,
    conference_id: int = 0,
    tournament_id: int = None,
    division: int = None,
    is_women_basketball: bool = False,
):
    date_str = ""

    if isinstance(game_date, str):
        date_str = parser.parse(date_str)
    elif isinstance(game_date, datetime):
        date_str = game_date.strftime("%m/%d/%Y")
    elif isinstance(game_date, date):
        game_datetime = datetime(
            year=game_date.year,
            month=game_date.month,
            day=game_date.day,
            hour=0,
            minute=0,
            second=0
        )
        date_str = game_datetime.strftime("%m/%d/%Y")
        del date_str
        # del game_datetime

    day_df = pd.DataFrame()
    year = int(date_str.split("/")[-1])
    if int(date_str.split("/")[0]) > 10:
        year += 1
    year_id = v.years[year]

    if division == 2:
        year_id += 2
    elif division == 3:
        year_id += 4

    if is_women_basketball:
        year_id -= 1

    if season_id:
        year_id = season_id

    date_str = date_str.replace("/", "%2F")
    # url = (
    #     "https://stats.ncaa.org/contests/livestream_scoreboards" +
    #     "?utf8=%E2%9C%93&season_division_id=" +
    #     f"{year_id}&game_date={date2}&conference_id={conference_id}" +
    #     f"&tournament_id={tournament_id}&commit=Submit"
    # )

    url = (
        f"https://stats.ncaa.org/season_divisions/{season_id}/" +
        "livestream_scoreboards?utf8=%E2%9C%93&" +
        f"season_division_id=&game_date={date_str}" +
        f"&conference_id={conference_id}&tournament_id={tournament_id}" +
        "&commit=Submit"
    )
    response = requests.get(url, headers=headers)
    time.sleep(5)

    html_content = response.text
    soup = BeautifulSoup(html_content, "html.parser")
    day_df = _collect_teams(soup, day_df)
    day_df = _collect_info(soup, day_df)
    day_df = _collect_game_ids(soup, day_df)
    day_df = day_df.dropna(subset=["Game_id"])
    day_df.reset_index(drop=True, inplace=True)
    day_df = _collect_scores(soup, day_df)
    day_df["Date"] = game_date
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
    day_df = day_df[desired_order]
    return day_df
