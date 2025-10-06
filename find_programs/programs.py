import pandas as pd
from io import StringIO
from ncaa_stats_scraper.network.fetch import get_site
from pathlib import Path
from bs4 import BeautifulSoup as Soup
from rapidfuzz import process, fuzz
import numpy as np
Data_Store = Path(__file__).resolve().parent.parent / "data"


def _update_ids() -> None:
    site_content = Soup(get_site("https://stats.ncaa.org/teams/history"), 'html.parser')
    menus = site_content.find_all(class_="chosen-select")
    for i, menu in enumerate(menus):
        relationship: dict[str:int] = {}
        options = menu.find_all('option')

        for option in options:
            if not option or not option["value"]:
                continue
            if not i:
                relationship[option.text] = int(option["value"])
            else:
                relationship[option.text] = option["value"]
        if not i:
            path = Data_Store / "school_ids.parquet"
            pd.Series(relationship, name="school_id").rename_axis("school_name").reset_index().to_parquet(path)
        else:
            path = Data_Store / "sport_codes.parquet"
            pd.Series(relationship, name="sport_code").rename_axis("sport_name").reset_index().to_parquet(path)


def scrape_program(program_id: int, sport_code: str) -> pd.DataFrame:

    url = f"https://stats.ncaa.org/teams/history?&org_id={program_id}&sport_code={sport_code}"
    site_content: StringIO = get_site(url)
    team_history: pd.DataFrame = pd.read_html(site_content)[0]
    rows = Soup(site_content, 'html.parser').find(id="team_history_data_table").find('tbody').find_all('tr')

    if not rows or rows[0].text.strip() == "No data available in table":
        return pd.DataFrame()

    data = []
    for row in rows[:-1]:
        mini = {}
        cols = row.find_all("td")
        if not cols:
            continue
        mini["Team_id"] = int(cols[0].find('a').get('href').split("/")[-1])
        mini["Year"] = cols[0].text
        coach_elem = cols[1].find('a')
        if coach_elem:
            mini["Coach_id"] = int(coach_elem.get('href').split("/")[-1])
            mini["Coach"] = coach_elem.text.split("(")[0].strip()
        else:
            mini["Coach_id"] = np.nan
            mini["Coach"] = np.nan
        data.append(mini)
    
    df = pd.DataFrame(data)
    new_order = [
        "Year",
        "Coach",
        "Division",
        "Conference",
        "Wins",
        "Losses",
        "Ties",
        "Team_id",
        "Coach_id",
    ]
    team_history = (team_history.merge(df, on="Year", how="left")
                    [new_order]
                    .iloc[:-1]
                    )

    return team_history


def search_programs(team: str, sport_code: str = "", update: bool=False) -> pd.DataFrame:
    '''
    Used to find programs for a given school and sport. DataFrame contains every
    season the school has played, a coach, their ids, and basic W/L info. 
    Querries are not case sensitive. Lots of random user input/output to handle.
    True function starts at url declaration

    Parameters:
        team - string name of the school, if an exact match not being found, 
        will use fuzzy to try to find close matches.

        sport_code - Uses the sport code provided to return program history. If no
        code is provided, lists all the sports to let user choose. 

        update - Only needs to be toggled if a new sport or school is added. Storing own copy of the dictionary
        saves a request per team lookup
    '''
    

    if update:
        _update_ids()

    sport_code = sport_code.upper()
    sports = pd.read_parquet(Data_Store / "sport_codes.parquet")
    schools = pd.read_parquet(Data_Store / "school_ids.parquet")

    team_lc = team.lower()
    schools["no_case"] = schools["school_name"].str.lower()

    exact_match = schools[schools["no_case"] == team_lc]
    if exact_match.empty:
        print("Exact match not found, choose a similar team below")

        lower_map = dict(zip(schools["no_case"], schools["school_name"]))
        results = process.extract(team_lc, list(lower_map.keys()), scorer=fuzz.WRatio, limit=10)

        for i, (match_lc, score, _) in enumerate(results):
            print(f"{i}: {lower_map[match_lc]}")

        choice = input("Choose one of the following teams, or type 'x' to exit: ")

        if choice.lower() == "x":
            print("Exiting...")
            return

        try:
            team_name = lower_map[results[int(choice)][0]]
            program_id = schools[schools["school_name"] == team_name].iloc[0]["school_id"]
        except (ValueError, IndexError):
            print("Invalid selection. Exiting...")
            return
    elif not exact_match.empty:
        program_id = exact_match.iloc[0]["school_id"]

    if sports[sports["sport_code"] == sport_code].empty:
        print("No valid sports code provided, pick the sport below")
        sport_names = sports["sport_name"].to_list()
        for i, sport in enumerate(sport_names):
            print(f"{i}: {sport}")

        choice = input("Choose one of the following sports, or type 'x' to exit: ")

        if choice.lower() == "x":
            print("Exiting...")
            return
        
        try:
            sport_name = sport_names[int(choice)]
            sport_code = sports[sports["sport_name"] == sport_name].iloc[0]["sport_code"]
        except (ValueError, IndexError):
            print("Invalid selection. Exiting...")
            return
        
    else:
        sport_name = sports[sports["sport_code"] == sport_code]["sport_name"].iloc[0]

    return scrape_program(program_id, sport_code)



if __name__ == "__main__":
    print(pd.read_parquet(Data_Store / "sport_codes.parquet"))
