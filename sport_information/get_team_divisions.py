import pandas as pd
from ncaa_stats_scraper.network.fetch import get_site
from bs4 import BeautifulSoup as Soup


def scrape_divisions(year: int, division: int, sport_code: str, FCS: bool = False) -> pd.DataFrame:
    
    '''
    Given a year, division, and sport, gets the name and org_id for every team 
    that supports this support in the division at the year. FCS switch for football
    else its useless
    '''

    if division == 1 and FCS and sport_code== "MFB":
        division = 12
    elif division == 1 and not FCS and sport_code == "MFB": 
        division = 11
    url = f"https://stats.ncaa.org/rankings/ranking_summary?academic_year={year}&division={division}&sport_code={sport_code}"
        
    site_content = get_site(url)
    soup = Soup(site_content, "html.parser")
    teams_soup = soup.find('select', {"name": "org_id"}).find_all('option')[1:]
    
    data = []

    for team in teams_soup:
        mini = {}
        mini["Team"] = team.text
        mini["Org_id"] = team.get("value")
        data.append(mini)

    return pd.DataFrame(data)
