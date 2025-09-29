from io import StringIO
import re
from datetime import date, datetime
from bs4 import BeautifulSoup as Soup
from ncaa_stats_scraper.network.fetch import get_site



def season_dates(sport_code: str, year: int) -> tuple[date, date]:
     
    url = f"https://stats.ncaa.org/contests/livestream_scoreboards?&sport_code={sport_code}&academic_year={year}"
    site_content: StringIO = get_site(url)
    soup = Soup(site_content, 'html.parser')
    date_code = soup.find_all('script')[4].text

    min_date_str = re.search(r"minDate:\s*'(\d{2}/\d{2}/\d{4})'", date_code).group(1)
    max_date_str = re.search(r"maxDate:\s*'(\d{2}/\d{2}/\d{4})'", date_code).group(1)

    min_date = datetime.strptime(min_date_str, "%m/%d/%Y").date()
    max_date = datetime.strptime(max_date_str, "%m/%d/%Y").date()

    return min_date, max_date