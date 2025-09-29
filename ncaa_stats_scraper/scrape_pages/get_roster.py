import pandas as pd
from io import StringIO
import numpy as np
from bs4 import BeautifulSoup as Soup
from ncaa_stats_scraper.network.fetch import get_site



def scrape_roster(team_id: int) -> pd.DataFrame:
    '''
    Although this uses a team id, it requires a seperate ping from the 
    functions in get_team to use, so it's placed in it's own module. 
    Returns the dataframe basically as is, used to get player_ids for
    scrape_player
    '''

    url: str = f"https://stats.ncaa.org/teams/{team_id}/roster"
    site_content: StringIO = get_site(url)
    roster = pd.read_html(site_content)[-1]
    rows = Soup(site_content, "html.parser").find_all('tbody')[-1].find_all('tr')

    player_ids = []
    for row in rows:
        if row.find('a'):
            player_ids.append(int(row.find('a').get('href').split("/")[-1]))
        else:
            player_ids.append(np.nan)

    roster["Player_id"] = player_ids

    def height_convert(height_str: str):
        if height_str == '-' or height_str[-1] == '-':
            return np.nan
        feet = int(height_str.split('-')[0])
        inches = int(height_str.split('-')[1])
        return feet * 12 + inches


    if "Height" in roster.columns:
        roster["Height_inches"] = roster["Height"].apply(height_convert)
        roster.drop("Height", axis=1, inplace=True)

    return roster
    

if __name__ == '__main__':
    df = scrape_roster(590769)
    print(df.types)