
import pandas as pd
from io import StringIO
import re
import numpy as np
from datetime import date, datetime
from bs4 import BeautifulSoup as Soup
from ncaa_stats_scraper.network.fetch import get_site



def scrape_day_scores(sport_code: str, day: date = date.today(), division: int = 1, FCS: bool = False, keep_seeds = True) ->pd.DataFrame:
    '''
    Gathers all the scores for the day for a particular sport and division. 
    Gives game logs IDs (if they exist), Home and Away Ids and event information.
    Parameters:

        sport_code - Three letter string of the sport code. Use 
                    sport_codes() to get DataFrame listing code mapping

        day - date object to specify the day you want to scrape
              defaults to the current day

        division - between 1 and 3, division of sport.

        FCS - Only valid when sport is Football (MFB) this allows user to 
        scrape FCS scores

        keep_seeds - During tournament games, the seed is shown next to the team. Turning this
        off will sync the names from the database to the teams listed but lose seeding info. 
    '''

    assert division >= 1 and division <= 3, "Divisions must be between 1 and 3 inclusive"

    if FCS and sport_code.upper() != "MFB":
        raise ValueError("The 'FCS' flag is only valid when the sport is Football (MFB).")

    if FCS:
        division = 12
    elif sport_code.upper() == "MFB" and division == 1:
        division = 11

    str_date = day.strftime("%m/%d/%Y").replace("/", "%2F")
    year = day.year

    if day.month >= 8:
        year += 1

    url = f"https://stats.ncaa.org/contests/livestream_scoreboards?&sport_code={sport_code}&division={division}&game_date={str_date}&academic_year={year}"

    site_content: StringIO = get_site(url)
    soup = Soup(site_content, 'html.parser')


    game_cards = soup.find_all(class_="table-responsive")

    if not game_cards:
        return pd.DataFrame()

    data = []
    for game_card in game_cards:
        mini = {}
        rows = game_card.find('tbody').find_all('tr', recursive=False)
        if not rows[-1].find('a'):
            continue # skip games that didn't happen
        mini["Game_id"] = int(rows[-1].find('a').get("href").split("/")[-2])

        scores = game_card.find_all('td', class_="totalcol")
        if len(scores) < 2:
            continue # sometimes they choose to hide cancelled games instead of just not posting a dead link

        home_team: str = rows[-2].find_all('td')[1].text.strip()
        away_team: str = rows[-3].find_all('td')[1].text.strip() 

        try:
            mini["Home_score"] = int(scores[1].text.strip())
        except ValueError:
            mini["Home_score"] = np.nan
        try:
            mini["Away_score"] = int(scores[0].text.strip())
        except ValueError:
            mini["Away_score"] = np.nan

        try:
            attendance = rows[0].find_all('div')[2].text.strip().split()[-1].replace(",", "")
        except IndexError:
            pass
            attendance = ""
        if attendance == 'Attend': #sometimes none is given
            mini["Attendance"] = int(attendance)
        else:
            mini["Attendance"] = np.nan





        formats = [
            '%m/%d/%Y %I:%M %p',  # Can list as either Datetime or Date
            '%m/%d/%Y',           
        ]

        date_str = rows[0].find_all('div')[1].text.strip()
        if 'AM' in date_str or 'PM' in date_str:
            date_str = " ".join(date_str.split()[:3]).split("*")[0]
        else:
            date_str = date_str.split()[0]

        for fmt in formats:
            try:
                game_day = datetime.strptime(date_str, fmt)
            except ValueError:
                game_day = day

        mini["Date_time"] = game_day


        if rows[-2].find('a'):
            if bool(re.search(r"\(\d+-\d+\)$", home_team)):
                mini["Home_wins"] = int(home_team.split("(")[-1].split("-")[0])
                mini["Home_losses"] = int(home_team.split("(")[-1].split("-")[1][:-1])
                home_team = home_team[:home_team.rfind(' (')]
            else:
                mini["Home_wins"] = np.nan
                mini["Home_losses"] = np.nan
            mini["Home_id"] = int(rows[-2].find('a').get("href").split("/")[-1])
            if not keep_seeds and home_team[0] == '#':
                home_team = " ".join(home_team.split()[1:])
        else:
            mini["Home_wins"] = np.nan
            mini["Home_losses"] = np.nan
            mini["Home_id"] = np.nan

        if rows[-3].find('a'):
            if bool(re.search(r"\(\d+-\d+\)$", away_team)):
                mini["Away_wins"] = int(away_team.split("(")[-1].split("-")[0])
                mini["Away_losses"] = int(away_team.split("(")[-1].split("-")[1][:-1])
                away_team = away_team[:away_team.rfind(' (')]
            else:
                mini["Away_wins"] = np.nan
                mini["Away_losses"] = np.nan
            mini["Away_id"] = int(rows[-3].find('a').get("href").split("/")[-1])
            if not keep_seeds and away_team[0] == '#':
                away_team = " ".join(away_team.split()[1:])
        else:
            mini["Away_wins"] = np.nan
            mini["Away_losses"] = np.nan
            mini["Away_id"] = np.nan

      
        mini["Location"] = home_team
        mini["Neutral"] = False
        mini["Away_team"] = away_team
        mini["Home_team"] = home_team
        mini["Event"] = np.nan
        if len(rows) == 5: # handles games with event info
            if "@" not in rows[1].text: # for when its an event but not neutral site
                mini["Event"] = rows[1].text.strip()
            elif "(" not in rows[1].text:
                mini["Location"] = rows[1].text.strip().split("(")[-1][1:]
            else:
                mini["Location"] = " ".join(rows[1].text.strip().split(" (")[:-1])[1:]
                mini["Event"] = rows[1].text.strip().split("(")[-1][:-1]
                mini["Neutral"] = True

        if not mini["Event"]:
            mini["Event"] = "Regular Season"

        data.append(mini)

    if not data: # ridiculous edge case where every game gets cancelled but it has happened (s/o covid)
        return pd.DataFrame()

    new_order = [
    "Game_id",
    "Event",
    "Location",
    "Neutral",
    "Attendance",
    "Date_time",

    "Home_team",
    "Home_id",
    "Home_score",
    "Home_wins",
    "Home_losses",

    "Away_team",
    "Away_id",
    "Away_score",
    "Away_wins",
    "Away_losses"
    ]


    games = pd.DataFrame(data)[new_order]
    
    return games


if __name__ == "__main__":

    df = scrape_day_scores("MBB", day= date(2024, 11, 26), division=1)

