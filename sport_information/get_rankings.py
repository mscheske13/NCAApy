import pandas as pd
from io import StringIO
import numpy as np
import re
from datetime import date, datetime
from bs4 import BeautifulSoup as Soup
from pathlib import Path
from ncaa_stats_scraper.network.fetch import get_site





def _scrape_date_ids_helper(site_content: StringIO) -> pd.DataFrame:
    soup = Soup(site_content, "html.parser")
    dates = soup.find("select", {"name": "rp"}).find_all('option')

    data = []
    for _date in dates:
        mini = {}
        mini["Date"] = datetime.strptime(_date.text.split("-")[0].strip(), "%m/%d/%Y").date()
        mini["Date_id"] = int(_date.get("value")[:-2]) 
        data.append(mini)
        
    return pd.DataFrame(data)


def scrape_date_ids(sport_code: str, season_start: date, stat_id: int, division: int = 1, FCS: bool = False) -> pd.DataFrame:
    assert division >= 1 and division <= 3, "Divisions must be between 1 and 3 inclusive"

    if FCS and sport_code.upper() != "MFB":
        raise ValueError("The 'FCS' flag is only valid when the sport is Football (MFB).")

    if FCS:
        division = 12
    elif sport_code.upper() == "MFB" and division == 1:
        division = 11

    year: int = season_start.year
    if season_start.month >= 8:
        year += 1

    url = f"https://stats.ncaa.org/rankings/{sport_code}/{year}/{division}/{stat_id}/2.0"
    return _scrape_date_ids_helper(get_site(url))



def _scrape_rankings_helper(site_content: StringIO) -> pd.DataFrame:
    rankings = pd.read_html(site_content)[-1]
    soup = Soup(site_content, "html.parser")
    rows = soup.find('tbody').find_all('tr')

    team_ids = []
    for row in rows:
        cols = row.find_all('td')
        if cols[1].find('a'):
            team_ids.append(int(cols[1].find('a').get('href').split("/")[-1]))
        else:
            team_ids.append(np.nan)

    for _ in range(len(rankings) - len(team_ids)):
        # yucky, but needed to deal with reclassifying teams that don't get a team_id listed
        team_ids.append(np.nan)

    rankings["Team_id"] = team_ids
    rankings = rankings[rankings["Team"] != "Reclassifying"]
    rankings["Conference"] = rankings["Team"].str.extract(r"\(([^()]*)\)\s*$")
    rankings["Team"] = rankings["Team"].str.replace(r"\s*\([^()]*\)\s*$", "", regex=True)
    if "W-L" in rankings.columns:
        rankings["Wins"] = rankings["W-L"].str.split("-").str[0].astype(int)
        rankings["Losses"] = rankings["W-L"].str.split("-").str[1].astype(int)
        rankings = rankings.drop(["W-L"], axis=1)

    def _clean_columns(col):
        try:
            return col.astype(float)
        except ValueError:
            return col
        
    rankings = rankings.apply(_clean_columns)

    rankings["Team_id"] = rankings["Team_id"].astype("Int64")
    
    return rankings




def scrape_rankings(sport_code: str, season_start: date, stat_id: int, date_id: int, division: int = 1, FCS: bool = False) -> pd.DataFrame:
    assert division >= 1 and division <= 3, "Divisions must be between 1 and 3 inclusive"

    if FCS and sport_code.upper() != "MFB":
        raise ValueError("The 'FCS' flag is only valid when the sport is Football (MFB).")

    if FCS:
        division = 12
    elif sport_code.upper() == "MFB" and division == 1:
        division = 11

    year: int = season_start.year
    if season_start.month >= 8:
        year += 1

    url = f"https://stats.ncaa.org/rankings/{sport_code}/{year}/{division}/{stat_id}/{date_id}"
    return _scrape_rankings_helper(get_site(url))



if __name__ == "__main__":
    df = scrape_date_ids("MFB", date(day=1, month=8, year=2014), 21)
    print(df)