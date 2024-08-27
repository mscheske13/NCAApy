from Teams_and_players import get_player, get_team, get_schedule, get_coach, get_roster
from day_scraper import get_day
from Game_Scraper import make_game, game_stats
import time


def scrape_game(game_id):
    time.sleep(2)
    return make_game(game_id)


def scrape_box(game_id):
    time.sleep(2)
    return game_stats(game_id)


def scrape_player(player_id):
    time.sleep(2)
    return get_player(player_id)


def scrape_schedule(schedule_id):
    time.sleep(2)
    return get_schedule(schedule_id)


def scrape_team(team_id):
    time.sleep(2)
    return get_team(team_id)


def scrape_coach(coach_id):
    time.sleep(2)
    return get_coach(coach_id)


def scrape_roster(roster_id):
    time.sleep(2)
    return get_roster(roster_id)


def scrape_day(date, conference_id='0', tournament_id='', division=1):
    time.sleep(2)
    return get_day(date, conference_id, tournament_id, division)


def helpme():
    with open('HelpMe.txt', 'r') as file:
        content = file.read()
    print(content)

