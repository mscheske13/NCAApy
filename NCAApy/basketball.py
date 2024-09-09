import pandas as pd

from NCAApy.game_scraper import _game_stats, _make_game
from NCAApy.teams_and_players import (
    _get_coach,
    _get_player,
    _get_roster,
    _get_schedule,
    _get_team,
)


def scrape_mbb_game_pbp(game_id: int) -> pd.DataFrame:
    """ """
    game_pbp_df = _make_game(game_id=game_id)
    return game_pbp_df


def scrape_mbb_game_box(game_id: int) -> pd.DataFrame:
    """ """
    game_box_df = _game_stats(game_id=game_id)
    return game_box_df


def scrape_mbb_player_stats(player_id: int) -> pd.DataFrame:
    """ """

    player_df = _get_player(player_id=player_id)
    return player_df


def scrape_mbb_team_schedule(team_id: int) -> pd.DataFrame:
    """ """
    schedule_df = _get_schedule(team_id=team_id)
    return schedule_df


def scrape_mbb_team_history(school_id: int) -> pd.DataFrame:
    """ """
    team_df = _get_team(school_id=school_id)
    return team_df


def scrape_coach_info(coach_id: int) -> pd.DataFrame:
    """ """
    coach_df = _get_coach(coach_id)
    return coach_df


def scrape_team_roster(team_id: int) -> pd.DataFrame:
    """ """
    roster_df = _get_roster(team_id)
    return roster_df
