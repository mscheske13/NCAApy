from Helpers import *
import time

def get_schedule(schedule_id):
    response = requests.get(f'https://stats.ncaa.org/teams/{schedule_id}', headers=headers)
    html_content = response.text
    html_buffer = StringIO(html_content)
    schedule = pd.read_html(html_buffer)[0]
    schedule = schedule.dropna(how='all')
    schedule = schedule[~schedule['Opponent'].str.contains('exempt', case=False)]
    soup = BeautifulSoup(html_content, 'html.parser')
    a_tags = soup.find_all('a')
    team_id = pd.NA
    for a_tag in a_tags:
        if a_tag.text == 'Team History':
            team_id = a_tag['href'].split('/')[-1]
            break
    team = soup.find('a', class_='nav-link skipMask dropdown-toggle').text.strip().rsplit(' ', 1)[0]
    coach = soup.find('div', class_='card').find_all('a')[4].text
    coach_id = soup.find('div', class_='card').find_all('a')[4]['href'].split('?')[0].split('/')[-1]
    rows = soup.find('tbody').find_all('tr', class_='underline_rows')
    team_ids = []
    game_ids = []
    opponents = []
    schedule.reset_index(drop=True, inplace=True)
    for index, row in enumerate(rows):
        a_tags = row.find_all('a')
        if len(a_tags) == 2:
            opponents.append(a_tags[0].text.strip())
            game_ids.append(int(a_tags[1]['href'].split('/')[-2]))
            team_ids.append(int(a_tags[0]['href'].split('/')[-1]))
        elif len(a_tags) == 1:
            if 'box_score' in a_tags[0]['href']:
                game_ids.append(int(a_tags[0]['href'].split('/')[-2]))
                opponents.append(schedule['Opponent'][index].split('@')[-1].strip())
                team_ids.append(pd.NA)
            else:
                game_ids.append(pd.NA)
                opponents.append(schedule['Opponent'][index].split('@')[-1].strip())
                team_ids.append(int(a_tags[0]['href'].split('/')[-1]))
        else:
            opponents.append(schedule['Opponent'][index].split('@')[-1].strip())
            game_ids.append(pd.NA)
            team_ids.append(pd.NA)

    schedule['Opponents'] = opponents
    schedule['Game_id'] = game_ids
    schedule['Game_id'] = schedule['Game_id'].replace('teams', pd.NA, regex=True)
    schedule['Opponent_id'] = team_ids
    schedule = opponent_split(schedule, team)
    schedule = split_result(schedule, team)
    schedule['Coach'] = coach
    schedule['Coach_id'] = coach_id
    schedule['Team_id'] = team_id
    desired_order = [0, 4, 8, 9, 11, 10, 6, 7, 5, 12, 13, 2, 3, 1, 14]
    schedule = schedule.iloc[:, desired_order]
    return schedule


def get_roster(roster_id):
    response = requests.get(f'https://stats.ncaa.org/teams/{roster_id}/season_to_date_stats', headers=headers)
    html_content = response.text
    soup = BeautifulSoup(html_content, 'html.parser')
    html_buffer = StringIO(html_content)
    a_tags = soup.find_all('a')
    for a_tag in a_tags:
        if 'people' in a_tag['href']:
            coach_id = int(a_tag['href'].split('/')[2].split('?')[0])
            break
    roster = pd.read_html(html_buffer)[0]
    rows = soup.find('tbody').find_all('tr')
    player_ids = []
    for row in rows[:-3]:
        a_tag = int(row.find('a')['href'].split('/')[-1])
        player_ids.append(a_tag)
    for _ in range(3):
        player_ids.append(pd.NA)
    roster.fillna(0, inplace=True)
    roster.replace('-', pd.NA, inplace=True)
    roster.rename(columns={'Avg.1': 'Avg_Rebs'}, inplace=True)
    roster.rename(columns={'Avg': 'Avg_Pts'}, inplace=True)
    columns_to_convert = [
        'FGM', 'FGA', '3FG', '3FGA', 'FT', 'FTA', 'PTS',
        'ORebs', 'DRebs', 'Tot Reb', 'AST', 'TO',
        'STL', 'BLK', 'Fouls', 'Dbl Dbl', 'Trpl Dbl', 'DQ', 'Tech Fouls', 'Effective FG Pct.'
    ]

    roster[columns_to_convert] = roster[columns_to_convert].astype(float).astype(int)
    columns_to_convert = ['FT%', 'Avg_Pts', 'Avg_Rebs']
    roster[columns_to_convert] = roster[columns_to_convert].astype(float)
    roster['Player_id'] = player_ids
    roster['Coach_id'] = int(coach_id)
    return roster


def get_player(player_id):
    pd.set_option('future.no_silent_downcasting', True)
    attempts = 0
    while attempts < 5:
        try:
            response = requests.get(f'https://stats.ncaa.org/players/{player_id}', headers=headers)

            if response.status_code == 200:
                break
        except requests.exceptions.RequestException:
            attempts += 1
            time.sleep(5)
    if attempts == 5:
        print('Server timed out, please give server some time to cool down')
        return 1
    html_content = response.text
    html_buffer = StringIO(html_content)
    player_stuff = pd.read_html(html_buffer)[1]
    player_stuff['MP'] = player_stuff['MP'].fillna('00:00')
    soup = BeautifulSoup(html_content, 'html.parser')
    player_stuff['Date'] = player_stuff['Date'].replace({'/': 'z'}, regex=True)
    player_stuff = player_stuff.replace({'/': ''}, regex=True)
    player_stuff['Date'] = player_stuff['Date'].replace({'z': '/'}, regex=True)
    a_tags = soup.find_all('a')
    for a_tag in a_tags:
        if 'people' in a_tag['href']:
            coach_id = int(a_tag['href'].split('/')[2].split('?')[0])
            break
    rows = soup.find_all('tbody')[1].find_all('tr')
    team_ids = []
    game_ids = []
    opponents = []
    for index, row in enumerate(rows):
        a_tags = row.find_all('a')
        if len(a_tags) == 0:
            opponents.append(player_stuff['Opponent'][index].split('@')[-1].strip())
            game_ids.append(pd.NA)
            team_ids.append(pd.NA)
            continue
        if 'java' in a_tags[0]['href']:
            a_tags.pop(0)
        if len(a_tags) == 2:
            opponents.append(a_tags[0].text.strip())
            game_ids.append(int(a_tags[1]['href'].split('/')[-2]))
            team_ids.append(int(a_tags[0]['href'].split('/')[-1]))
        elif len(a_tags) == 1:
            if 'box_score' in a_tags[0]['href']:
                game_ids.append(int(a_tags[0]['href'].split('/')[-2]))
                opponents.append(player_stuff['Opponent'][index].split('@')[-1].strip())
                team_ids.append(pd.NA)
            else:
                game_ids.append(pd.NA)
                opponents.append(player_stuff['Opponent'][index].split('@')[-1].strip())
                team_ids.append(int(a_tags[0]['href'].split('/')[-1]))
    team_ids.append(pd.NA)
    game_ids.append(pd.NA)
    opponents.append(pd.NA)
    player_stuff['Opponents'] = opponents
    team = soup.find('a', class_='nav-link skipMask dropdown-toggle').text.strip().rsplit(' ', 1)[0]
    coach = soup.find('div', class_='card').find_all('a')[4].text
    player_stuff = opponent_split(player_stuff, team)
    player_stuff = split_result(player_stuff, team)
    player_stuff['Coach'] = coach
    player_stuff[['Minutes', 'Seconds']] = player_stuff['MP'].str.split(':', expand=True)
    player_stuff['Did_play'] = player_stuff['GP'].apply(lambda y: True if y == 1 else False if pd.isna(y) else None)
    player_stuff = player_stuff.fillna(0)
    player_stuff['Minutes'] = player_stuff['Minutes'].astype(int)
    player_stuff['Seconds'] = player_stuff['Seconds'].astype(int)
    player_stuff = player_stuff.drop(columns=['MP'])
    player_stuff = player_stuff.drop(columns=['GP'])
    pd.set_option('future.no_silent_downcasting', True)
    player_stuff = player_stuff.replace({np.nan: 0})
    player_stuff['Opponent_id'] = team_ids
    player_stuff['Game_id'] = game_ids
    player_stuff.loc[len(player_stuff) - 1, 'Did_play'] = False
    player_stuff.loc[len(player_stuff) - 1, 'Event'] = pd.NA
    player_stuff.loc[len(player_stuff) - 1, 'Venue'] = pd.NA
    player_stuff.loc[len(player_stuff) - 1, 'Game_type'] = pd.NA
    player_stuff.loc[len(player_stuff) - 1, 'Opponents'] = pd.NA
    columns_to_clean = ['FGM', 'FGA', '3FG', '3FGA', 'FT', 'FTA', 'PTS', 'ORebs', 'DRebs', 'Tot Reb', 'AST',
                        'TO', 'STL', 'BLK', 'Fouls', 'Tech Fouls']
    if 'DQ' in player_stuff.columns:
        columns_to_clean.append('DQ')
    player_stuff[columns_to_clean] = player_stuff[columns_to_clean].astype(float).astype(int)
    player_stuff['Coach_id'] = coach_id
    desired_order = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 26, 27, 28, 21, 22, 24, 23, 25, 31,
                     30, 29]
    player_stuff = player_stuff.iloc[:, desired_order]
    player_stuff.loc[len(player_stuff) - 1, 'Result'] = pd.NA
    return player_stuff


def get_coach(coach_id):
    response = requests.get(f'https://stats.ncaa.org/people/{coach_id}?sport_code=MBB', headers=headers)
    html_content = response.text
    html_buffer = StringIO(html_content)
    soup = BeautifulSoup(html_content, 'html.parser')
    coach = soup.find_all('dd')[0].text
    coach_stuff = pd.read_html(html_buffer)[1]
    coach_stuff.drop(columns=['Notes', 'Ties'], inplace=True)
    coach_stuff['Coach'] = coach
    a_tags = soup.find('tbody').find_all('a')
    year_ids = []
    for index, a_tag in enumerate(a_tags):
        if index % 2 == 0:
            year_ids.append(a_tag['href'].split('/')[-1])
    for year in coach_stuff['Year']:
        if '-' not in year:
            year_ids.append(pd.NA)
    coach_stuff['Team_tags'] = year_ids
    return coach_stuff


def get_team(team_id):
    response = requests.get(f'https://stats.ncaa.org/teams/history/MBB/{team_id}', headers=headers)
    html_content = response.text
    html_buffer = StringIO(html_content)
    soup = BeautifulSoup(html_content, 'html.parser')
    team = pd.read_html(html_buffer)[0]
    team = team.replace({np.nan: pd.NA})
    team['Conference'] = team['Conference'].replace({'-': pd.NA})
    team.drop(columns='Notes', inplace=True)
    a_tags = soup.find('tbody').find_all('a')
    coach_ids = []
    team_ids = []
    for index, a_tag in enumerate(a_tags):
        if index % 2 == 0:
            team_ids.append(a_tag['href'].split('/')[-1])
        else:
            coach_ids.append(a_tag['href'].split('/')[-1])
    coach_ids.append(pd.NA)
    team_ids.append(pd.NA)
    team['Coach_id'] = coach_ids
    team['Season_id'] = team_ids
    return team


if __name__ == '__main__':
    print(get_player(7673842))
