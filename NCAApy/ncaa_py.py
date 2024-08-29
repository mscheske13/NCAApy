
# import time

# import NCAApy.day_scraper as ds
# import NCAApy.game_scraper as gs
# import NCAApy.teams_and_players as tp


# def scrape_game(game_id):
#     time.sleep(2)
#     return gs.make_game(game_id)


# def scrape_box(game_id):
#     time.sleep(2)
#     return gs.game_stats(game_id)


# def scrape_player(player_id):
#     time.sleep(2)
#     return tp.get_player(player_id)


# def scrape_schedule(schedule_id):
#     time.sleep(2)
#     return tp.get_schedule(schedule_id)


# def scrape_team(team_id):
#     time.sleep(2)
#     return tp.get_team(team_id)


# def scrape_coach(coach_id):
#     time.sleep(2)
#     return tp.get_coach(coach_id)


# def scrape_roster(roster_id):
#     time.sleep(2)
#     return tp.get_roster(roster_id)


# def scrape_day(
#     date,
#     conference_id="0",
#     tournament_id="",
#     division=1,
#     w=False,
#     season_id=None
# ):
#     return ds.get_day(
#         date,
#         conference_id,
#         tournament_id,
#         division,
#         w,
#         season_id
#     )
