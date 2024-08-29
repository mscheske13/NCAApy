import copy
import logging
from io import StringIO

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

from NCAApy.helpers import (
    event_packer,
    get_positions,
    get_starters,
    headers,
    split_event,
    swap_rows,
    time_convert,
    time_counter,
    to_lineup_df,
)

# example: str = "https://stats.ncaa.org/contests/5254095/play_by_play"


def build_lineups(pbp, stats):
    starters = get_starters(pbp)
    positions = get_positions(stats)
    # TODO: Reimplement this.
    # Why are we failing in the first place?
    # What's causing the `try` to fail?
    try:
        away_players = to_lineup_df(
            pbp, starters[0], positions[0], is_home=False
        )
    except Exception as e:
        logging.warning(
            "Unhandled exception in `NCAApy.game_scraper.build_lineups()`: " +
            e
        )
        away_players = pd.DataFrame()
        col_names = pbp.columns.tolist()
        for n in range(5):
            away_players[f'{col_names[1]}_{n + 1}'] = 'Unavailable'
    # TODO: Reimplement this.
    # Why are we failing in the first place?
    # What's causing the `try` to fail?
    try:
        home_players = to_lineup_df(
            pbp, starters[1], positions[1], is_home=True
        )
    except Exception as e:
        logging.warning(
            "Unhandled exception in `NCAApy.game_scraper.build_lineups()`: " +
            e
        )
        home_players = pd.DataFrame()
        col_names = pbp.columns.tolist()
        for n in range(5):
            home_players[f'{col_names[3]}_{n + 1}'] = 'Unavailable'
    df_combined = pd.concat([away_players, home_players], axis=1)
    pbp = pd.concat([pbp, df_combined], axis=1)
    return pbp


def cleanup(pbp):
    col_names = pbp.columns.tolist()
    pbp['Event'] = pbp[f'{col_names[1]}'].combine_first(pbp[f'{col_names[3]}'])
    pbp.drop(columns=[col_names[1], col_names[3]], inplace=True)
    pbp[['Description', 'Player']] = pbp['Event'].apply(split_event).apply(
        pd.Series
    )
    pbp.drop(columns=['Event'], inplace=True)
    pbp = pbp[
        ~pbp['Description'].str.contains('substitution', case=False)
    ]
    pbp = pbp[
        ~pbp['Description'].str.contains(
            'rebound offensivedeadball', case=False
        )
    ]
    pbp = pbp[
        ~pbp['Description'].str.contains(
            'jumpball startperiod', case=False
        )
    ]
    pbp = pbp[
        ~pbp['Description'].str.contains('game start', case=False)
    ]
    pbp = pbp[
        ~pbp['Description'].str.contains('period end confirmed', case=False)
    ]
    pbp.reset_index(drop=True, inplace=True)
    col_names = pbp.columns.tolist()
    # TODO: Reimplement this as a pd.reindex()
    pbp = pbp[[
        col_names[0],
        col_names[1],
        col_names[12],
        col_names[13],
        col_names[2],
        col_names[3],
        col_names[4],
        col_names[5],
        col_names[6],
        col_names[7],
        col_names[8],
        col_names[9],
        col_names[10],
        col_names[11]
    ]]
    return pbp


def event_sorter(pbp):
    indices = event_packer(pbp)
    priorities = [
        'assist',
        'jumpball',
        'steal',
        'turnover',
        'foul ',
        'foulon',
        'block',
        '2pt',
        '3pt',
        '1of2',
        '1of3',
        '2of3',
        '1of1',
        '2of2',
        '3of3',
        'timeout'
    ]
    if pbp['Description'][0] != 'jumpball lost':
        swap_rows(pbp, 0, 1)
    new_orders = []
    for index in indices[1:]:
        if len(index) == 1:
            continue
        new_order = {}
        for number in index:
            event = pbp['Description'][number]
            for n, priority in enumerate(priorities):
                if priority in event:
                    new_order[number] = n
        new_orders.append(new_order)
    for row_priority in new_orders:
        pbp = pbp.reset_index(drop=True)
        sorted_indices = sorted(row_priority, key=row_priority.get)
        non_sorted = list(row_priority.keys())
        while non_sorted != sorted_indices:
            old = copy.deepcopy(non_sorted)
            for index, key in enumerate(non_sorted):
                proper = sorted_indices[index]
                if key != proper:
                    pbp = swap_rows(pbp, key, proper)
                    temp = non_sorted[non_sorted.index(key)]
                    non_sorted[non_sorted.index(key)] = non_sorted[
                        non_sorted.index(proper)
                    ]
                    non_sorted[old.index(proper)] = temp
                    break
    pbp = pbp.reset_index(drop=True)
    pbp['To_delete'] = False
    prev_score = ''
    for index, event in enumerate(pbp['Description']):
        if 'foul ' in event:
            pbp.loc[index, 'To_delete'] = True
        if 'steal' in event:
            pbp.loc[index, 'To_delete'] = True
        if 'jumpball lost' in event:
            pbp.loc[index, 'To_delete'] = True
        if 'assist' in event:
            pbp.loc[index, 'To_delete'] = True
        if event == 'block':
            pbp.loc[index, 'To_delete'] = True
        if event == 'foulon':
            pbp.loc[index, 'Description'] = 'fouled'
        if 'game end confirmed' in event:
            pbp.loc[index, 'Description'] = 'Final'
            pbp.loc[index, 'Score'] = prev_score
        if 'timeout' in pbp.loc[index, 'Score']:
            pbp.loc[index, 'Score'] = prev_score
        prev_score = pbp.loc[index, 'Score']

    pbp['Description_2'] = pd.NA
    pbp['Player_2'] = pd.NA
    to_drop = []
    for index, delete in enumerate(pbp['To_delete']):
        if delete:
            pbp.loc[index + 1, 'Description_2'] = pbp.loc[index, 'Description']
            pbp.loc[index + 1, 'Player_2'] = pbp.loc[index, 'Player']
            to_drop.append(index)
    pbp.drop(index=to_drop, inplace=True)
    pbp = pbp.drop(columns='To_delete')
    col_names = pbp.columns.tolist()
    # TODO: Why can't this just be "away_score" and "home_score"?
    team_columns = [
        f'{col_names[4].split('_')[0]}_Score',
        f'{col_names[9].split('_')[0]}_Score'
    ]
    pbp[team_columns] = pbp['Score'].str.split('-', expand=True)
    pbp = pbp.drop(columns='Score')
    pbp = pbp.reset_index(drop=True)
    return pbp


def easy_features(pbp):
    prev = '50'
    half = 1
    half_column = []
    for index, time in enumerate(pbp['Time']):
        if time.split(':')[0] > prev:
            half += 1
        prev = time.split(':')[0]
        half_column.append(half)
    pbp['Period'] = half_column
    game_seconds_left = []
    game_seconds = []
    for index, time in enumerate(pbp['Time']):
        game_seconds_left.append(
            time_convert(time, pbp['Period'][index], half)
        )
        game_seconds.append(time_counter(time, pbp['Period'][index]))
    pbp['Game_seconds_left'] = game_seconds_left
    pbp['Game_seconds'] = game_seconds
    col_names = pbp.columns.tolist()
    # TODO: Use pd.reindex() instead of whatever this is
    pbp = pbp[[
        col_names[-3],
        col_names[0],
        col_names[-2],
        col_names[-1],
        col_names[1],
        col_names[2],
        col_names[3],
        col_names[4],
        col_names[5],
        col_names[6],
        col_names[7],
        col_names[8],
        col_names[-13],
        col_names[-12],
        col_names[-11],
        col_names[-10],
        col_names[-9],
        col_names[-8],
        col_names[-7],
        col_names[-6],
        col_names[-5],
        col_names[-4]
    ]]

    return pbp


def poss_counter(pbp, teams, team_players):
    poss_log = [None]
    poss_count = [1]
    poss = 1
    for index, event in enumerate(pbp['Description'][1:]):
        player = pbp['Player'][index + 1]
        if pd.isna(player) or 'timeout' in event:
            poss_count.append(poss)
            poss_log.append(poss_log[-1])
            continue
        if player in team_players[teams[0]]:
            poss_log.append(teams[0])
        elif player in team_players[teams[1]]:
            poss_log.append(teams[1])
        else:
            poss_log.append(poss_log[-1])
        if len(poss_log) > 2 and poss_log[-1] != poss_log[-2]:
            poss += 1
        poss_count.append(poss)
        if (
            'technical' in event or
            'flagrant' in event or
            'period start' in event
        ):
            poss += 1

    pbp['Possession'] = poss_log
    pbp['Possession_Count'] = poss_count
    col_names = pbp.columns.tolist()
    pbp = pbp[[
        col_names[0],
        col_names[15],
        col_names[16],
        col_names[2],
        col_names[1],
        col_names[14],
        col_names[13],
        col_names[18],
        col_names[17],
        col_names[3],
        col_names[4],
        col_names[5],
        col_names[6],
        col_names[7],
        col_names[8],
        col_names[9],
        col_names[10],
        col_names[11],
        col_names[12]
    ]]

    return pbp


def fix_bug(box, pbp):
    col_names = pbp.columns.tolist()
    for i in range(len(pbp)):
        if pbp.at[i, col_names[4]] == 'period start':
            if i > 0:
                pbp.at[i, col_names[4]] = pbp.at[i - 1, col_names[4]]
            else:
                pbp.at[i, col_names[4]] = 0
        if not pbp.at[i, col_names[5]]:
            if i > 0:
                pbp.at[i, col_names[5]] = pbp.at[i - 1, col_names[5]]
            else:
                pbp.at[i, col_names[5]] = 0
    pbp_score = {
        col_names[4].split('_')[0]: pbp[col_names[4]][len(pbp) - 1],
        col_names[5].split('_')[0]: pbp[col_names[5]][len(pbp) - 1]
    }
    box_score = {
        box[0][1]: box[box.shape[1] - 1][1],
        box[0][2]: box[box.shape[1] - 1][2]
    }
    if pbp_score != box_score:
        # TODO: Why?
        pbp.rename(
            columns={
                col_names[4]: col_names[5],
                col_names[5]: col_names[4]
            },
            inplace=True
        )
    return pbp


def shot_splitter(pbp):
    # find every shot modifier
    shot_value = []
    shot_type = []
    shot_result = []
    is_transition = []
    is_paint = []
    is_2nd = []
    for index, event in enumerate(pbp['Description']):
        if len(event.split('pt')) > 1:
            shot_value.append(event.split('pt')[0])
            shot_type.append(event.split()[1])
            if event.split()[-1] == 'made':
                shot_result.append('made')
            else:
                shot_result.append('missed')
            if 'fastbbreak' in event or 'fromturnover' in event:
                is_transition.append(True)
            else:
                is_transition.append(False)
            if 'pointsinthepaint' in event:
                is_paint.append(True)
            else:
                is_paint.append(False)
            if '2nd' in event:
                is_2nd.append(True)
            else:
                is_2nd.append(False)
        else:
            if 'freethrow' in event:
                shot_value.append(1)
                if 'fromturnover' in event:
                    is_transition.append(True)
                else:
                    is_transition.append(False)
            else:
                shot_value.append(pd.NA)
                is_transition.append(pd.NA)
            shot_type.append(pd.NA)
            shot_result.append(pd.NA)
            is_paint.append(pd.NA)
            is_2nd.append(pd.NA)

    pbp['Shot_Value'] = shot_value
    pbp['Shot_Type'] = shot_type
    pbp['Shot_Result'] = shot_result
    pbp['is_Transition'] = is_transition
    pbp['is_paint'] = is_transition
    pbp['is_2nd_chance'] = is_transition
    return pbp


def shot_clock(pbp):
    shot_clocks = []
    poss_length = []
    is_off = False
    for index, poss in enumerate(pbp['Possession_Count']):
        if index == 0:
            shot_clocks.append(pd.NA)
            poss_length.append(pd.NA)
            continue

        mins, seconds, _ = map(int, pbp['Time'][index - 1].split(':'))
        time = pbp['Game_seconds_left'][index]
        prev_time = pbp['Game_seconds_left'][index - 1]
        prev_poss = pbp['Possession_Count'][index - 1]
        lapsed = prev_time - time
        event = pbp['Description'][index]
        event2 = pbp['Description'][index - 1]
        if poss > prev_poss and event != 'period start':
            poss_length.append(lapsed)
        elif event != 'period start':
            poss_length.append(lapsed + poss_length[-1])
        else:
            poss_length.append(pd.NA)
        if event == 'period start':
            shot_clocks.append(pd.NA)
            is_off = False
            continue
        elif mins == 0 and seconds < 30 and poss > prev_poss:
            shot_clocks.append('Off')
            is_off = True
            continue
        if event == 'rebound offensive':
            if mins == 0 and seconds < 20:
                shot_clocks.append('Off')
                is_off = True
            else:
                shot_clocks.append(20)
        elif is_off:
            shot_clocks.append('Off')
        elif event == 'rebound defensive' or event == 'jumpball won':
            shot_clocks.append(30)
        elif poss >= prev_poss and event != 'Period start':
            if (
                len(event2.split('pt')) > 1 and
                event2.split()[-1] == 'made' and
                mins != 0 and
                'timeout' not in event2
            ):
                shot_clocks.append(38 - lapsed)
            elif event2 == 'offensive rebound':
                shot_clocks.append(20 - lapsed)
            else:
                shot_clocks.append(30 - lapsed)
        else:
            shot_clocks.append(lapsed)
    pbp['Shot_clock_est'] = shot_clocks
    pbp[['minutes', 'seconds']] = pbp['Time'].str.split(':', n=1, expand=True)

    pbp['seconds'] = pbp['seconds'].str[:2] + '.' + pbp['seconds'].str[3:]

    pbp['minutes'] = pd.to_numeric(pbp['minutes'], errors='coerce')
    pbp['seconds'] = pd.to_numeric(pbp['seconds'], errors='coerce')
    pbp = pbp.drop(columns=['Time'])
    pbp['Poss_Length'] = poss_length
    # TODO: Why?
    column_order = [
        0, 28, 29, 1, 2, 3, 4, 27, 30, 10, 9, 5, 6, 7, 8,
        21, 22, 23, 24, 25, 26, 11, 12, 13, 14, 15, 16,
        17, 18, 19, 20
    ]
    col_names = list(pbp.columns)

    pbp = pbp[[col_names[i] for i in column_order]]

    return pbp


def make_game(game_id):
    response = requests.get(
        f'https://stats.ncaa.org/contests/{game_id}/play_by_play',
        headers=headers
    )
    html_content = response.text
    html_buffer = StringIO(html_content)
    soup = BeautifulSoup(html_content, 'html.parser')
    date = soup.find_all('td', class_='grey_text')[7].text.split()[0]
    time = " ".join(
        soup.find_all('td', class_='grey_text')[7].text.split()[1:]
    )
    plays = pd.read_html(html_buffer)
    for index, play in enumerate(plays):
        plays[index] = play.drop_duplicates()
        plays[index].reset_index(drop=True, inplace=True)
    col_names = plays[3].columns.tolist()
    teams = [col_names[1], col_names[3]]
    stats = pd.read_html(
        f'https://stats.ncaa.org/contests/{game_id}/individual_stats'
    )
    team_players = {
        f'{stats[3]['Name'][len(stats[3]) - 1]}': stats[3]['Name'].tolist(),
        f'{stats[4]['Name'][len(stats[4]) - 1]}': stats[4]['Name'].tolist()
    }
    stats = stats[3:]
    full_sheet = pd.concat(plays[3:], ignore_index=True)
    full_sheet = build_lineups(full_sheet, stats)
    full_sheet = cleanup(full_sheet)
    full_sheet = event_sorter(full_sheet)
    full_sheet = poss_counter(full_sheet, teams, team_players)
    full_sheet = easy_features(full_sheet)
    full_sheet = fix_bug(plays[1], full_sheet)
    full_sheet = shot_splitter(full_sheet)
    full_sheet = shot_clock(full_sheet)
    full_sheet['Game_id'] = game_id
    full_sheet['Date'] = date
    full_sheet['Time'] = time
    cols = list(full_sheet.columns)
    new_order = cols[-2:] + cols[:-2]
    full_sheet = full_sheet[new_order]
    return full_sheet


def get_refs(game_id):
    response = requests.get(
        f'https://stats.ncaa.org/contests/{game_id}/officials',
        headers=headers
    )
    html_content = response.text
    soup = BeautifulSoup(html_content, 'html.parser')
    rows = soup.find('table', class_='dataTable display')
    rows = rows.find('tbody').find_all('tr')
    refs = []
    for row in rows:
        refs.append(row.text.strip())
    return refs


def game_stats(game_id):
    response = requests.get(
        f'https://stats.ncaa.org/contests/{game_id}/individual_stats',
        headers=headers
    )
    html_content = response.text
    html_buffer = StringIO(html_content)
    stats = pd.read_html(html_buffer)[3:]
    for index, team in enumerate(stats):
        team['Team'] = team['Name'][len(team) - 1]
        team.drop(len(team) - 2, inplace=True)
    soup = BeautifulSoup(html_content, 'html.parser')

    card_headers = soup.find_all('div', class_='card-header')
    team_ids = []
    for card in card_headers:
        if card.find('a').text == 'Period Stats':
            team_ids.append(pd.NA)
            continue
        team_ids.append(card.find('a')['href'].split('/')[-1])
    for index, team in enumerate(team_ids):
        stats[index][f'{stats[index]['Team'][0]}_id'] = team
    full_sheet = pd.concat(stats, ignore_index=True)
    col_names = full_sheet.columns.tolist()
    full_sheet[col_names[-1]] = full_sheet[col_names[-1]][len(full_sheet) - 1]
    full_sheet[col_names[-2]] = full_sheet[col_names[-2]][len(full_sheet) - 2]
    tables = soup.find_all('tbody')
    player_ids = []
    for table in tables:
        for a_tag in table.find_all('a'):
            player_ids.append(a_tag['href'].split('/')[-1])
        player_ids.append(pd.NA)
    full_sheet['Player_id'] = pd.NA
    for index, position in enumerate(full_sheet['P']):
        if position != 'G' and position != 'F' and position != 'C':
            full_sheet.loc[index, 'P'] = 'G'
        full_sheet.loc[index, 'Player_id'] = player_ids[index]
    date = soup.find_all('td', class_='grey_text')[7].text.split()[0]
    time = " ".join(
        soup.find_all('td', class_='grey_text')[7].text.split()[1:]
    )
    location = soup.find_all('td', class_='grey_text')[8].text
    attendance = int(
        soup.find_all('td', class_='grey_text')[9].text.split()[-1].replace(
            ",", ""
        )
    )
    full_sheet['Date'] = date
    full_sheet['Time'] = time
    full_sheet['Location'] = location
    full_sheet['Attendance'] = attendance
    refs = get_refs(game_id)
    for i, ref in enumerate(refs):
        full_sheet[f'Ref_{i + 1}'] = ref
    full_sheet = full_sheet.replace({np.nan: pd.NA})
    return full_sheet


if __name__ == "__main__":
    game_stats(8174404)
