'''
TUTORTIAL!

Goal: Find the team who scored the most points in a team, and get all their information
'''

from ncaa_stats_scraper import * # Import every function from library
import pandas as pd # Get our data analysis tool ready and give it a new name (pd)
from datetime import timedelta

'''
get_site # used to ping a website and get its html content. 

# Daily scores
scrape_day_scores  # with a date, code, and division, gives dataframes of games to happen that day

# Program search and scraping 
search_programs  # Used to find programs for a given school and sport. DataFrame contains every
                season the school has played, a coach, their ids, and basic W/L info. 
scrape_program  # Returns same of search_programs but takes a program id instead of searching by name

# Page scraping, all below take a team or player_id

scrape_schedule  # Dataframe of all games to happen to a team in a season for a sport
scrape_stadiums  # Dataframes of stadiums affiliated with a team for sport. Most often just 1 row
scrape_coaches  # Dataframe of every head coach to coach a game for a season. Most often just 1 row
scrape_indivual_leaders  # Gives a small stats overview of players leading certain stat categories
scrape_team_stats  # gives general stats for entre team
scrape_roster  # gives list of players, some stats, and player_ids
batch_team_scrape  # gives all the information above with a single id. Saves ping requests 

Below takes player_ids
scrape_player_game_stats  # gives stats for every game of a season for a player 
scrape_player_career  # gives every season they have played and which team
scrape_player_attributes  # gives height, weight, school, etc of player
batch_player_scrape  # gives all player_ids functions in one ping

scrape_coach  # gives coach history and programs coached given a coach_id

# Sport information
season_dates  # gives the start and end date of a season given a sport code and year
scrape_rankings  # Not finished
scrape_divisions  # Gives which teams belong to which division
'''

'''
0                   Baseball        MBA
1           Men's Basketball        MBB
2                   Football        MFB
3           Men's Ice Hockey        MIH
4             Men's Lacrosse        MLA
5               Men's Soccer        MSO
6               Men's Tennis        MTE
7           Men's Volleyball        MVB
8           Men's Water Polo        MWP
9         Women's Basketball        WBB
10           Women's Bowling        WBW
11              Field Hockey        WFH
12        Women's Ice Hockey        WIH
13          Women's Lacrosse        WLA
14                  Softball        WSB
15            Women's Soccer        WSO
16  Women's Beach Volleyball        WSV
17            Women's Tennis        WTE
18        Women's Volleyball        WVB
19        Women's Water Polo        WWP
'''


def main():
    test = pd.read_parquet("ncaa_stats_scraper/data/sport_codes.parquet")

    print(test)

    1 / 0

    season = pd.DataFrame() # empty dataframe (think dataframe as spreadsheet)


    # season_dates gives a tuple of start and end of season. sport_code says the sport "MBB == Men's basketball" for the year 2025
    start_date, end_date = season_dates(sport_code="MBB", year=2025)


    while start_date <= end_date:

        # scrape_day_scores gives every game to happen in a day under parameters given
        df = scrape_day_scores(sport_code="MBB", day=start_date, division=1, keep_seeds=False)

        # after we get the scores, we will advance the day for the next set of games
        start_date += timedelta(days=1)

        if df.empty:
            continue # if no games took place, don't bother

        print(start_date) # give progress check
        
        # makes season spreadsheet out of each indivual dataframe
        season = pd.concat([season, df], ignore_index=True)
    
    # gets highest score of season for the away and home team
    max_home = season["Home_Score"].max()
    max_away = season["Away_Score"].max()

    # Determine which is the overall max and which column it came from
    if max_home >= max_away:
        best_game = season.loc[season["Home_Score"] == max_home].iloc[0]
        team_id = best_game["Home_id"]
        team_name = best_game["Home_Team"]
        score = best_game["Home_Score"]
        opponent = best_game["Away_Team"]
    else:
        best_game = season.loc[season["Away_Score"] == max_away].iloc[0]
        team_id = best_game["Away_id"] # these are ids needed for scraping info
        team_name = best_game["Away_Team"]
        opponent = best_game["Home_Team"]
        score = best_game["Away_Score"]

    print(f"Highest scoring team: {team_name} (ID {team_id}) with {score} points")
    print("Full game info:")
    print(best_game)

    team_info: list[pd.DataFrame] = batch_team_scrape(team_id) # gives a list of dataframes of team information

    '''
    batch_team_scrape dataframes given = {
        "header": _scrape_header_helper,
        "available_sports": _scrape_available_sports_helper,
        "history": _scrape_history_helper,
        "schedule": _scrape_schedule_helper,
        "individual_stat_leaders": _scrape_indivual_leaders_helper,
        "team_stat_ranks": _scrape_team_stats_helper,
        "coaches": _scrape_coaches_helper,
        "stadiums": _scrape_stadiums_helper
    }
    '''

    # Gets name of coach who coached most games in season
    coach: str = team_info[-2].iloc[0]["Name"] 
    roster: pd.DataFrame = scrape_roster(team_id) # use the team_id to get their roster

    players = roster["Name"].to_list()

    print(f"Team {team_name} scored {score} points vs. {opponent}.")

    print(f"{team_name} was coached by {coach} and had players {players}")
    return


if __name__ == "__main__":
    main()



       


    

if __name__ == '__main__':
    main() # good practice but not neccessary
