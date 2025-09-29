import pandas as pd
from io import StringIO
import numpy as np
from bs4 import BeautifulSoup as Soup
from datetime import date, datetime
from ncaa_stats_scraper.network.fetch import get_site


def scrape_coach(coach_id: int) -> pd.DataFrame():
    url: int = f"https://stats.ncaa.org/people/{coach_id}"
    site_content: StringIO = get_site(url)
    soup = Soup(site_content, "html.parser")
    rows = soup.find_all('tbody')[-1].find_all('tr')

    data = []
    for row in rows:
        mini = {}
        cols = row.find_all('td')
        mini["Year"] = cols[0].text.strip()
        mini["Team_id"] = cols[0].find('a').get("href").split("/")[-1]
        sport_code = cols[1].find('a').get("href").split("/")[-2]
        mini["Program"] = cols[1].text.strip()
        mini["Program_id"] = int(cols[1].find('a').get("href").split("/")[-1])

        if sport_code != "MFB":
            mini["Division"] = len(cols[2].text.strip()[2:])
        else:
            mini["Division"] = cols[2].text.strip()


        mini["Wins"] = int(cols[3].text.strip())  
        mini["Losses"] = int(cols[4].text.strip()) 
        mini["Ties"] = int(cols[5].text.strip()) 

        data.append(mini) 

    return pd.DataFrame(data)


if __name__ == "__main__":
    print(scrape_coach(36202))