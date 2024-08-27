from Helpers import *
import variables as v


def collect_teams(soup, day):
    aways = []
    away_ids = []
    homes = []
    home_ids = []
    teams_messy = soup.find_all('td', class_='opponents_min_width')
    count = 0
    for team in teams_messy:
        a_tag = team.find('a')
        temp = team.text.strip()
        if len(temp.split('(')) > 1:
            team = ' '.join(team.text.strip().split()[:-1]).strip()
        else:
            team = team.text.strip()
        if not a_tag:
            if count % 2 == 0:
                away_ids.append(pd.NA)
                aways.append(team)
            else:
                home_ids.append(pd.NA)
                homes.append(team)
            count += 1
            continue
        box = int(a_tag['href'].split('/')[-1])
        if count % 2 == 0:
            away_ids.append(box)
            aways.append(team)
        else:
            home_ids.append(box)
            homes.append(team)
        count += 1
    day['Away'] = aways
    day['Home'] = homes
    day['Away_id'] = away_ids
    day['Home_id'] = home_ids
    return day


def collect_info(soup, day):
    game_infos = soup.find_all('td', colspan='10')
    count = 0
    arenas = []
    events = []
    is_neutral = []
    times = []
    attendance = []
    for index, info in enumerate(game_infos):
        info = info.text.split()
        if '/' not in info[0]:
            continue
        if len(info) < 4:
            arenas.append(pd.NA)
            events.append(pd.NA)
            is_neutral.append(pd.NA)
            times.append(' '.join((info[1:])))
            attendance.append(pd.NA)
            count += 1
            continue
        if index + 1 != len(game_infos) and '/' not in game_infos[index + 1].text.split()[0]:
            description = game_infos[index + 1].text.split()
            if '@' not in description[0]:
                arenas.append(day['Home'][count])
                events.append(' '.join(description))
                is_neutral.append(False)
            for index2, part in enumerate(description):
                if '(' in part:
                    event = ' '.join(description[index2:]).replace('(', '').replace(')', '')
                    events.append(event)
                    break
                if '@' in part:
                    arena = ' '.join(description[index2:])
                    arena = arena.replace('@', '').split('(')[0].strip()
                    arenas.append(arena)
                    is_neutral.append(True)
                    if '(' not in ' '.join(description):
                        events.append('Regular Season')
        else:
            arenas.append(day['Home'][count])
            events.append('Regular Season')
            is_neutral.append(False)
        times.append(' '.join(info[1:3]))
        attendance.append(int(info[-1].replace(',', '')))
        count += 1
    day['Time'] = times
    day['Attendance'] = attendance
    day['Location'] = arenas
    day['Event'] = events
    day['is_Neutral'] = is_neutral
    return day


def collect_game_ids(soup, day):
    game_ids = []
    rows = soup.find_all('tr')
    count = 0
    for row in rows:
        try:
            if count % 4 == 0:
                if 'Canceled' in row.get_text() or 'Ppd' in row.get_text():
                    game_ids.append(pd.NA)
                else:
                    game_ids.append(int(row['id'].split('_')[-1]))
            count += 1
        except:
            continue
    day['Game_id'] = game_ids
    return day


def collect_scores(soup, day):
    scores = soup.find_all('td', class_='totalcol')
    away_score = []
    home_score = []
    for index, score in enumerate(scores):
        if index % 2 == 0:
            away_score.append(score.text.strip())
        else:
            home_score.append(score.text.strip())
    day['Away_score'] = away_score
    day['Home_score'] = home_score
    return day


def get_day(date, conference_id, tournament_id, division):
    if isinstance(date, datetime):
        date = date.strftime('%m/%d/%Y')
    day = pd.DataFrame()
    year = int(date.split('/')[-1])
    if int(date.split('/')[0]) > 10:
        year += 1
    year_id = v.years[year]
    if division == 2:
        year_id += 2
    if division == 3:
        year_id += 4
    date2 = date.replace('/', '%2F')
    url = (f'https://stats.ncaa.org/contests/livestream_scoreboards?utf8=%E2%9C%93&season_division_id='
           f'{year_id}&game_date={date2}&conference_id={conference_id}&tournament_id={tournament_id}&commit=Submit')
    response = requests.get(url, headers=headers)
    html_content = response.text
    soup = BeautifulSoup(html_content, 'html.parser')
    day = collect_teams(soup, day)
    day = collect_info(soup, day)
    day = collect_game_ids(soup, day)
    # if 'Canceled' in soup.getText():
    #     day = day.dropna(subset=['Attendance'])
    #     day.reset_index(drop=True, inplace=True)
    day = day.dropna(subset=['Game_id'])
    day.reset_index(drop=True, inplace=True)
    day = collect_scores(soup, day)
    day['Date'] = date
    desired_order = ['Date', 'Time', 'Away', 'Away_score', 'Home', 'Home_score',
                     'Location', 'Event', 'is_Neutral', 'Attendance', 'Away_id', 'Home_id', 'Game_id']
    day = day[desired_order]
    return day
