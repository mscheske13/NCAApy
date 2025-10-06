import pandas as pd
from io import StringIO
import numpy as np
import re
from datetime import date, datetime
from bs4 import BeautifulSoup as Soup
from pathlib import Path
from ncaa_stats_scraper.network.fetch import get_site

from datetime import datetime, time

def _parse_game_date(date_str: str):
    """
    Parses a date string like:
    - '08/23/2025'
    - '10/04/2025 12:00 PM'
    - '11/15/2025 TBA'
    
    Returns a datetime object. If time is TBA, sets it to 12:00 PM by default.
    """
    date_str = date_str.split("(")[0].strip()  # remove anything in parentheses

    # Default time for TBA
    default_time = time(12, 0)  # 12:00 PM

    try:
        # Try full datetime with time first
        return datetime.strptime(date_str, "%m/%d/%Y %I:%M %p")
    except ValueError:
        pass

    if "TBA" in date_str.upper():
        # Parse only the date and add default time
        dt = datetime.strptime(date_str.replace("TBA", "").strip(), "%m/%d/%Y")
        return datetime.combine(dt.date(), default_time)
    
    # Just a date, no time
    dt = datetime.strptime(date_str, "%m/%d/%Y")
    return datetime.combine(dt.date(), default_time)



def _scrape_available_sports_helper(soup) -> pd.DataFrame:
    '''
    This is actually useful compared to program finder because it 
    only finds sports that the school actually supports in the 
    current academic year
    '''

    data_folder = Path(__file__).resolve().parent.parent / "data"

    sport_codes = pd.read_parquet(data_folder / "sport_codes.parquet")
    sports = soup.find_all('option')
    if not sports:
        return pd.DataFrame()

    data = []
    for sport in sports:
        if "-" in sport.text:
            continue # hacky way to get only the sports
        
        mini = {}
        sport_name = sport.text.strip()
        mini["Sport"] =  sport_name
        mini["Sport_code"] = sport_codes[sport_codes["sport_name"] == sport_name]["sport_code"].iloc[0]
        mini["Sport_id"] = int(sport.get("value"))
        data.append(mini)

    return pd.DataFrame(data)

def scrape_available_sports(team_id: int) -> pd.DataFrame:

    url: str = f"https://stats.ncaa.org/teams/{team_id}"
    site_content: StringIO = get_site(url)
    soup = Soup(site_content, "html.parser")


def _scrape_history_helper(soup) -> pd.DataFrame:

    years = soup.find_all('option')
    if not years:
        return pd.DataFrame()

    data = []
    for year in years:
        if "-" not in year.text:
            break # hacky way to get only the years, not other sports
        
        mini = {}
        mini["Year"] =  year.text.strip()
        mini["Team_id"] = int(year.get("value"))
        data.append(mini)

    return pd.DataFrame(data)

def scrape_history(team_id) -> pd.DataFrame:
    '''
    Very similar to get_program, but gives less information
    and doesn't have any search feature. Still saves a ping
    so it's worth to add
    '''

    url: str = f"https://stats.ncaa.org/teams/{team_id}"
    site_content: StringIO = get_site(url)
    soup = Soup(site_content, "html.parser")

    return _scrape_history_helper(soup)



def _scrape_header_helper(soup) -> pd.DataFrame:

    mini = {}

    team = soup.find_all('img')[1].get('alt')

    mascot = soup.find(class_="card-header").find('a').text.replace(team, "").strip()

    mini["School"] = team
    mini["Team_name"] = mascot
    coach_summary = soup.find_all('form')[1].find_all('a')[-1]
    mini["Coach_history_id"] = int(coach_summary.get('href').split("/")[-1])
    mini["Sport"] =  coach_summary.get('href').split("/")[-2]

    if soup.find(string="Individual Leaders"):
        table = soup.find_all('tbody')[-2]
    elif not soup.find(string=lambda text: text and "Team Stats - Through games" in text):
        mini["Team_id"] = int(soup.find('option', selected="selected").get("value")) 
        return pd.DataFrame([mini])
    else:
        table = soup.find_all('tbody')[-1]

    sport_code = (table.find('a').get("href").split("/")[2])
    division = int(table.find('a').get("href").split("/")[4])
    if sport_code == "MFB":
        match division:
            case 11:
                level = "FBS"
            case 12:
                level = "FCS"
            case 2:
                level = "II"
            case 3:
                level = "III"
        mini["Division"] = level
    else:
        mini["Division"] = division

    mini["Team_id"] = int(soup.find('option', selected="selected").get("value")) 

    return pd.DataFrame([mini])


def scrape_header(team_id: int) -> pd.DataFrame:
    '''
    Returns 1 dimensional DF containing school name, sportcode, id, mascot, and division
    '''


    url: str = f"https://stats.ncaa.org/teams/{team_id}"
    site_content: StringIO = get_site(url)
    soup = Soup(site_content, "html.parser")

    return _scrape_header_helper(soup)

def _scrape_indivual_leaders_helper(soup) -> pd.DataFrame:
    if soup.find(string="Individual Leaders"):
        table = soup.find_all('tbody')[-1]
    elif not soup.find(string=lambda text: text and "Team Stats - Through games" in text):
        return pd.DataFrame()
    else:
        return pd.DataFrame()

    rows = table.find_all('tr')
    if not rows:
        return pd.DataFrame()

    data = []
    for row in rows:
        mini = {}
        cols = row.find_all("td")

        mini["Stat"] = cols[0].text.strip()
        mini["Player"] = cols[1].text.strip()
        if mini["Player"]: # sometimes no player is listed
            mini["Player_id"] = int(cols[1].find('a').get('href').split("/")[-1])
            mini["Value"] = float(cols[2].text.strip().replace(",", ""))
        else:
            mini["Player"] = np.nan
            mini["Value"] = np.nan

        if "-" == cols[3].text.strip() or not cols[3].text.strip():
            mini["PG"] = np.nan
        else:
            mini["PG"] = float(cols[3].text.strip().replace(",", ""))

        
        data.append(mini)

    return pd.DataFrame(data)


def scrape_indivual_leaders(team_id: int) -> pd.DataFrame:
    url: str = f"https://stats.ncaa.org/teams/{team_id}"
    site_content: StringIO = get_site(url)
    soup = Soup(site_content, "html.parser")

    return _scrape_indivual_leaders_helper(soup)


def _scrape_team_stats_helper(soup) -> pd.DataFrame:

    # yes I know this a stupid way to do this, no I couldn't find a better way
    if soup.find(string="Individual Leaders"):
        table = soup.find_all('tbody')[-2]
    elif not soup.find(string=lambda text: text and "Team Stats - Through games" in text):
        return pd.DataFrame()
    else:
        table = soup.find_all('tbody')[-1]

    rows = table.find_all('tr')
    if not rows:
        return pd.DataFrame()

    data = []
    for row in rows:
        mini = {}
        cols = row.find_all("td")

        mini["Stat"] = cols[0].text.strip()

        if cols[0].find('a'):
            mini["Stat_id"] = int(cols[0].find('a').get("href").split("/")[-2])
            mini["Date_id"] = int(cols[0].find('a').get("href").split("/")[-1])
        else:
            mini["Stat_code"] = np.nan
        if "T" in cols[1].text:
            mini["Tied"] = True
            mini["Rank"] = int(cols[1].text[2:])
        else:
            mini["Tied"] = False
            mini["Rank"] = int(cols[1].text)

        try:
            mini["Value"] = float(cols[2].text.strip())
        except ValueError:
            if cols[2].text.strip() == "-":
                mini["Value"] = np.nan
            mini["Value"] = cols[2].text.strip()
        data.append(mini)

    return pd.DataFrame(data)



def scrape_team_stats(team_id: int) -> pd.DataFrame:
    url: str = f"https://stats.ncaa.org/teams/{team_id}"
    site_content: StringIO = get_site(url)
    soup = Soup(site_content, "html.parser")

    return _scrape_team_stats_helper(soup)



def _scrape_stadiums_helper(soup) -> pd.DataFrame:
    stadiums = soup.find('div', class_="col p-0").find_all(class_="row mb-0 text-nowrap")

    if not stadiums:
        return pd.DataFrame()


    data = []

    for stadium in stadiums:
        mini = {}
        cols = stadium.find_all('dt')
        answers = stadium.find_all('dd')

        for col, answer in enumerate(answers):
            true_col = cols[col].text.strip()[:-1]
            true_answer = answer.text.strip()
            if true_col == "Capacity":
                if true_answer:
                    mini[true_col] = int(true_answer.replace(",", ""))
            elif true_col == "Year Built":
                if true_answer:
                    mini[true_col] = int(true_answer)
            elif true_col == "Primary Venue":
                mini["is_Primary"] = True if true_answer == 'true' else False
            else:
                mini[true_col] = true_answer

        data.append(mini)

    stadiums_info = pd.DataFrame(data)

    return stadiums_info 


def scrape_stadiums(team_id: int) -> pd.DataFrame:
    '''
    Given a team_id, gets information on stadiums
    '''


    url: str = f"https://stats.ncaa.org/teams/{team_id}"
    site_content: StringIO = get_site(url)
    soup = Soup(site_content, "html.parser")

    return _scrape_stadiums_helper(soup)

    
def _scrape_coaches_helper(soup) -> pd.DataFrame:
    coaches = soup.find_all('div', class_="col p-0")[1].find_all(class_="row mb-0 text-nowrap")

    if not coaches:
        return pd.DataFrame()

    data = []
    for coach in coaches:
        mini = {}
        cols = coach.find_all('dt')
        answers = coach.find_all('dd')

    

        for col, answer in enumerate(answers):
            true_col = cols[col].text.strip()[:-1]
            true_answer = answer.text.strip()
            
            if true_col == "Alma Mater":
                mini["Alma_mater"] = true_answer.split(" -")[0]
                mini["Graduation_year"] = int(true_answer.split("- ")[1])
            elif true_col == "Start Date":
                mini["Start_date"] = datetime.strptime(true_answer, "%m/%d/%Y").date()
            elif true_col == "End Date":
                mini["End_date"] = datetime.strptime(true_answer, "%m/%d/%Y").date()
            elif true_col == "Name":
                mini["Name"] = true_answer
                if answer.find('a'):
                    mini["Coach_id"] = int(answer.find('a').get("href").split("?")[0].split("/")[-1])
            elif true_col == "Record":
                mini["Wins"] = int(true_answer.split("-")[0])
                mini["Losses"] = int(true_answer.split("-")[1])
            elif true_col == "Seasons":
                x = 0
                mini["Seasons"] = int(true_answer.split()[0])
            else:
                mini[true_col] = true_answer            
        data.append(mini)

    coaches_info = pd.DataFrame(data)

    return coaches_info



def scrape_coaches(team_id: int) -> pd.DataFrame:
    url: str = f"https://stats.ncaa.org/teams/{team_id}"
    site_content: StringIO = get_site(url)
    soup = Soup(site_content, "html.parser")

    return _scrape_coaches_helper(soup)


def _scrape_schedule_helper(soup) -> pd.DataFrame:
    team = soup.find_all('img')[1].get('alt')
    tables = soup.find_all('table')
    games = []
    for table in tables:
        # really ugly and hacky but couldn't find a better way that would work 
        # with both the new and old site layout 
        if "Date" in table.text:
            games = table.find_all('tr')
            break

    if not games:
        return pd.DataFrame()

    data = []
    if games[0].find_all('td'):
        sliced: slice = slice(2, None, None)
    else:
        sliced: slice = slice(1, None, 2)
    for game in games[sliced]:
        
        mini = {}
        cols = game.find_all('td')

        mini["Date"] = _parse_game_date(cols[0].text.split("(")[0])
        mini["Neutral"] = False

        if cols[1].find('br', recursive=False): # this means it's a special location
            event_info = cols[1].contents[-1]
            location = cols[1].text[:-len(event_info)].strip()
            event_info = event_info.strip()
            mini["Opponent"] = location
            if event_info[0] == "@":
                mini["Location"] = event_info.split(" (")[0][1:]
                mini["Neutral"] = True
                if " (" in event_info:
                    mini["Event"] = event_info.split(" (")[-1][:-1]
            else:
                mini["Event"] = event_info
                if location[0] == "@":
                    mini["Location"] = location[2:]
                else:
                    mini["Location"] = team


        else:
            location = cols[1].text.strip()
            if location[0] == "@":
                mini["Location"] = location[2:]
                mini["Opponent"] = location[2:]
            else:
                mini["Location"] = team
                mini["Opponent"] = location

    

        if cols[1].find('a'):
            mini["Opponent_id"] = int(cols[1].find('a').get('href').split("/")[-1])
        else:
            mini["Opponent_id"] = np.nan

        game_result = cols[2].text.strip()
        if game_result == "Canceled" or game_result == "Ppd" or not game_result:
            continue # skip games that didn't happen
        mini["Result"] = game_result[0]
        game_result = game_result[2:].split(" (")[0]
        mini["Team_score"] = int(game_result.split("-")[0])
        mini["Opponent_score"] = int(game_result.split("-")[1])
        
        if cols[2].find('a'):
            mini["Game_id"] = int(cols[2].find('a').get('href').split("/")[-2])
        else:
            mini["Game_id"] = np.nan

        if len(cols) == 4 and cols[3]:
            mini["Attendance"] = int(cols[3].text.replace(",", ""))
        else:
            mini["Attendance"] = np.nan

        if "Event" not in mini:
            mini["Event"] = "Regular Season"

        data.append(mini)

    new_order = [
    'Game_id',        
    'Date',           
    'Location',       
    'Event',        
    'Opponent',  
    'Opponent_id',    
    'Result',         
    'Team_score',     
    'Opponent_score', 
    'Attendance'   
    ]

    season = pd.DataFrame(data)[new_order]
    return season


def scrape_schedule(team_id: int) -> pd.DataFrame:
    '''
    Given a team_id, returns their season results. 

    '''


    url: str = f"https://stats.ncaa.org/teams/{team_id}"
    site_content: StringIO = get_site(url)
    soup = Soup(site_content, "html.parser")

    return _scrape_schedule_helper(soup)


def batch_team_scrape(team_id: int, which: list[str] = []) -> list[pd.DataFrame]:
    '''
    To prevent re pinging of the server for all of these, if a user needs to use more than
    one per team, they should use this specifying which data they need. By default, uses every function
    else if a user provides an invalid function, throws an error and lists the valid functions
    '''

    valid_functions = {
        "header": _scrape_header_helper,
        "available_sports": _scrape_available_sports_helper,
        "history": _scrape_history_helper,
        "schedule": _scrape_schedule_helper,
        "individual_stat_leaders": _scrape_indivual_leaders_helper,
        "team_stat_ranks": _scrape_team_stats_helper,
        "coaches": _scrape_coaches_helper,
        "stadiums": _scrape_stadiums_helper
    }

    if not which:
        which = list(valid_functions.keys())
    
    for need in which:
        if need.lower() not in valid_functions.keys():
            print(f"{need} is not a supported function, please make it one of the following:")
            for i, _ in enumerate(valid_functions.keys()):
                print(f"    {i}. {_}")
            raise AssertionError

    
    url: str = f"https://stats.ncaa.org/teams/{team_id}"
    site_content: StringIO = get_site(url)
    soup = Soup(site_content, "html.parser")

    function_results = []
    for need in which:
        df = valid_functions[need](soup)
        if not df.empty:
            function_results.append(df)

    return function_results
    

    


if __name__ == "__main__":
    dfs = batch_team_scrape(62754)

    for df in dfs:
        print(df)