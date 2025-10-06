import pandas as pd
from io import StringIO
import numpy as np
from bs4 import BeautifulSoup as Soup
from datetime import date, datetime
from ncaa_stats_scraper.network.fetch import get_site



def _clean_column(col):
        '''
        Clean up all the annoying idiosyncrasies of the stat columns
        '''
        try:
            return (
                col.fillna("0") 
                .astype(str)                               
                .str.rstrip('/')            
                .replace('', '0')           
                .astype(float)                
            )
        except ValueError:
            return (
                col.fillna("0")
                .astype(str)                               
                .str.rstrip('/')            
                .replace('', '0')
            )


def _scrape_player_attributes_helper(site_content) -> pd.DataFrame:
    soup = Soup(site_content, "html.parser")
    table = soup.find_all('dl', class_="row mb-0 text-nowrap")[2]
    mini = {}
    cols = table.find_all('dt')
    answers = table.find_all('dd')

    for col, answer in enumerate(answers):
        true_col = cols[col].text.strip()[:-1]
        try:
            true_answer = float(answer.text.strip())
        except ValueError:
            true_answer = answer.text.strip()

        if true_col == "Height":
            if true_answer == '-':
                mini["Height_inches"] = np.nan
                continue
            true_answer = int(true_answer.split("-")[0]) * 12 + int(true_answer.split("-")[1])
            mini["Height_inches"] = true_answer
        else:
            mini[true_col] = true_answer

    return pd.DataFrame([mini])


def scrape_player_attributes(player_id: int) -> pd.DataFrame:

    url: str = f"https://stats.ncaa.org/players/{player_id}"
    site_content: StringIO = get_site(url)    

    return _scrape_player_attributes_helper(site_content)


def _scrape_player_career_helper(site_content) -> pd.DataFrame:

    # magic numbers kinda getting out of hand but just trust me its here
    years = pd.read_html(site_content)[-5]
    years = years.iloc[:-1]
    soup = Soup(site_content, "html.parser")
    rows = soup.find_all('tbody')[-2].find_all('tr')
    
    data = []
    for row in rows:
        mini = {}
        cols = row.find_all('td')
        
        mini["Year"] = cols[0].text.strip()
        if cols[0].find('a'):
            mini["Player_id"] = cols[0].find('a').get('href').split("/")[-1]
        else:
            mini["Player_id"] = np.nan

        mini["Team"] = cols[1].text.strip()
        if cols[1].find('a'):
            mini["Team_id"] = cols[1].find('a').get('href').split("/")[-1]
        else:
            mini["Team_id"] = np.nan
        
        data.append(mini)


    years = years.drop(columns=['Year', 'Team'], errors='ignore').apply(_clean_column)

    years = pd.concat([pd.DataFrame(data), years], axis=1)

    return years



def scrape_player_career(player_id: int) -> pd.DataFrame:

    url: str = f"https://stats.ncaa.org/players/{player_id}"
    site_content: StringIO = get_site(url)

    return _scrape_player_career_helper(site_content)


def _scrape_player_game_stats_helper(site_content) -> pd.DataFrame:

    stats = pd.read_html(site_content)[-2]
    stats = stats.iloc[:-1] # cut off the cumulative totals since we scrape those seperately
    soup = Soup(site_content, "html.parser")
    rows = soup.find_all('tbody')[-1].find_all('tr')
    team = soup.find_all('img')[1].get('alt')
    

    # filthy code duplication alert, see _scrape_schedule_helper 
    data = []
    for row in rows:
        mini = {}
        cols = row.find_all('td')

        mini["Date"] = datetime.strptime(cols[0].text.split("(")[0], "%m/%d/%Y").date()
        mini["Neutral"] = False
        if cols[1].find('br'): 
            event_info = cols[1].contents[cols[1].contents.index(cols[1].find('br')) + 1].strip()
            if event_info[0] == "@":
                mini["Location"] = event_info.split(" (")[0][1:]
                mini["Neutral"] = True
                if " (" in event_info:
                    mini["Event"] = event_info.split(" (")[-1][:-1]
            else:
                mini["Event"] = event_info
                mini["Location"] = team
        
        else:
            location = cols[1].text.strip()
            if location[0] == "@":
                mini["Location"] = location[2:]
            else:
                mini["Location"] = team

        game_result = cols[2].text.strip()

        mini["Result"] = game_result[0]
        game_result = game_result[2:].split(" (")[0]
        mini["Team_score"] = int(game_result.split("-")[0])
        mini["Opponent_score"] = int(game_result.split("-")[1])

        if cols[1].find('a'):
            mini["Opponent_id"] = int(cols[1].find_all('a')[-1].get('href').split("/")[-1])
        
        if cols[2].find('a'):
            mini["Game_id"] = int(cols[2].find('a').get('href').split("/")[-2])


        if "Event" not in mini:
            mini["Event"] = "Regular Season"

        data.append(mini)


    stats = stats.drop(columns=['Date', 'Opponent', 'Result'], errors='ignore').apply(_clean_column)

    stats = pd.concat([pd.DataFrame(data), stats], axis=1)

    return stats
        

def scrape_player_game_stats(player_id: int) -> pd.DataFrame:
    
    url: str = f"https://stats.ncaa.org/players/{player_id}"
    site_content: StringIO = get_site(url)
    

    return _scrape_player_game_stats_helper(site_content)


def batch_player_scrape(player_id: int, which: list[str] = []) -> list[pd.DataFrame]:


    valid_functions = {
        "game_stats": _scrape_player_game_stats_helper,
        "career": _scrape_player_career_helper,
        "attributes": _scrape_player_attributes_helper
    }

    if not which:
        which = list(valid_functions.keys())
    
    for need in which:
        if need.lower() not in valid_functions.keys():
            print(f"{need} is not a supported function, please make it one of the following:")
            for _ in valid_functions.keys():
                print(f"    {_}")
            raise AssertionError

    url: str = f"https://stats.ncaa.org/players/{player_id}"
    site_content: StringIO = get_site(url, use_playwright=True)
    

    function_results = []
    for need in which:
        cloned_content = StringIO(site_content)
        df = valid_functions[need](cloned_content)
        if not df.empty:
            function_results.append(df)

    return function_results


if __name__ == "__main__":
    print(batch_player_scrape(8762537))