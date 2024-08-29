# NCAApy
Hi and welcome to NCAApy! The goal of this project is to provide the neccessary tools for scraping NCAA results. 
The project is best designed college basketball however, a lot of the functions can work for other sports. I welcome contributors
who would be interested in making this work for other sports. Idea for this project is based on the work of Jake Flancer with his BigBallR package. See his work here: https://github.com/jflancer/bigballR


Functions:

scrape_day(date, conference_id='0', tournament_id='', division=1, w=False, season_id=None):

    Using a date in the format of mm/dd/yyyy in a string, or a datetime format, this will scrape the game results for the day. 
    Make 'w'=True to change it to women's basketball. It will give you box score ids needed for scrape_game, and scrape_box, 
    schedule id's for the 'home' and 'away' team, as well as basic game information, like score, attendance, location, and event. 
    Altough teams are designated as 'home' and 'away' this is for simplicitiy and there is a is_neutral column to clarify whether 
    or not it is literally a home game. 


scrape_game(game_id): #basketball only

    This will scrape the play by play data of the given game which includes shot data, players on court, and possession
    counters. For now this feature can only be used on most games after the start of the 2019-2020 season and the ncaa
    tournament games of 2019. Before that the data is formatted differently, and will need a custom function for it to 
    work. 


def scrape_box(game_id): # basketball only

    This will scrape the box score which will return player and team stats for the game, as well as game information,
    refs, and ids for players and team schedule. If a team does not have an ID they are not NCAA affiliated, and thus
    the player_ids will not work for that team.


def scrape_player(player_id): # basketball only

    Scrapes the id of player for a given season, returning opponents, scores, and stats, and is the source of coach IDs.



def scrape_schedule(schedule_id):

    Scrapes the schedule of a team giving opponents, scores, and extra game info. ALso returns team_ids for historical
    scraping in scrape_team/


def scrape_team(team_id):

    Scrapes a teams historical record of the team including W-L, year, coach, coach ids, and season ids.


def scrape_coach(coach_id):

    Scrapes the history of a coach, their win loss records and teams coached as well as the team schedule ids for those
    years.
