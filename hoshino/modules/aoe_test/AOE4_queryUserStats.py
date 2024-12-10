import json
import requests
from logging import getLogger
from .player import Player
from bs4 import BeautifulSoup

from hoshino import Service, priv


proxies = {"http": "", "https": ""}
logger = getLogger(__name__)
session = requests.session()

request_header = {'User-agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36'}


# 一个方法 获取游戏角色的信息，比如胜率 ，排名 elo等
def queryUserStats(text: str) -> str:
    """ Tries to find a player based on a text containing either name, steam_id or profile_id
    Returns the player name and rank if found, otherwise returns None"""

    # 首先确认是否是profile id
    try:

        url = f"https://aoe4world.com/api/v0/players/search?query={text}"
        logger.info(url)
        resp = json.loads(session.get(url).text)
        logger.info(f"resp: {resp}")
        #{'total_count': 1, 'page': 1, 'per_page': 50, 'count': 1, 'offset': 0, 'filters': {'query': 'badistricia', 'exact': False}, 'players': [{'name': 'Badistricia', 'profile_id': 18026182, 'steam_id': '76561198815746443', 'avatars': {'small': None, 'medium': None, 'full': None}, 'country': 'cn', 'social': {}, 'last_game_at': '2024-03-23T13:00:23.000Z', 'leaderboards': {'rm_solo': {'rank_level': 'unranked', 'streak': 0, 'games_count': 0, 'wins_count': 0, 'losses_count': 0, 'season': 7, 'previous_seasons': [{'rating': 1002, 'rank': 15977, 'rank_level': 'platinum_1', 'streak': -1, 'games_count': 5, 'wins_count': 4, 'losses_count': 1, 'disputes_count': 0, 'drops_count': 0, 'last_game_at': '2024-02-21T16:13:21.000Z', 'win_rate': 80.0, 'season': 6}]}, 'rm_team': {'rank_level': 'unranked', 'streak': 0, 'games_count': 0, 'wins_count': 0, 'losses_count': 0, 'season': 7, 'previous_seasons': [{'rating': 1088, 'rank': 15124, 'rank_level': 'platinum_1', 'streak': 8, 'games_count': 99, 'wins_count': 53, 'losses_count': 46, 'disputes_count': 0, 'drops_count': 0, 'last_game_at': '2024-03-16T16:39:15.000Z', 'win_rate': 53.5, 'season': 6}]}, 'rm_3v3_elo': {'rating': 1151, 'rank': 8618, 'rank_level': None, 'streak': 1, 'games_count': 25, 'wins_count': 14, 'losses_count': 11, 'disputes_count': 0, 'drops_count': 0, 'last_game_at': '2024-03-07T13:42:41.000Z', 'win_rate': 56.0}, 'rm_4v4_elo': {'rating': 1129, 'rank': 11280, 'rank_level': None, 'streak': 8, 'games_count': 67, 'wins_count': 36, 'losses_count': 31, 'disputes_count': 0, 'drops_count': 0, 'last_game_at': '2024-03-16T16:39:15.000Z', 'win_rate': 53.7}, 'qm_3v3': {'rating': 1113, 'rank': 21415, 'rank_level': None, 'streak': 1, 'games_count': 19, 'wins_count': 11, 'losses_count': 8, 'disputes_count': 0, 'drops_count': 0, 'last_game_at': '2024-03-12T13:06:24.000Z', 'win_rate': 57.9}, 'qm_4v4': {'rating': 1257, 'rank': 9629, 'rank_level': None, 'streak': 2, 'games_count': 26, 'wins_count': 17, 'losses_count': 9, 'disputes_count': 0, 'drops_count': 0, 'last_game_at': '2024-03-15T13:25:34.000Z', 'win_rate': 65.4}}}]}
        if 'players' in resp and len(resp['players']) > 0:
            #根据群号判断player json中 本群是否有这个 里是否有这个玩家，如果有则继续，否则存入这个玩家的name profile_id
            #
            exact_user = resp['players'][0];
            user = Player(name=exact_user['name'], profile_id=exact_user['profile_id'], steam_id=exact_user['steam_id'], avatars=exact_user['avatars'], country=exact_user['country'],last_game_at=exact_user['last_game_at'],user_data={})
            leaderBoards = exact_user["leaderboards"]
            profile_id = user.profile_id
            player_name = user.name
            # steam_id = resp['players'][0].get('steam_id')

            logger.info(f"user : {user}")
            logger.info(f"leaderBoards : {leaderBoards}")

            logger.info(
                f"Found player by query: {player_name} ({profile_id})"
            )

            # 查看数据，比如rm qm等的数据
            rm_solo_data = leaderBoards.get("rm_solo",None)
            pre_rm_solo_data = leaderBoards.get("rm_solo",None).get("previous_seasons",None)
            rm_team_data = leaderBoards.get("rm_team",None)
            pre_rm_team_data = leaderBoards.get("rm_team",None).get("previous_seasons",None)
            rm_3v3_elo_data = leaderBoards.get("rm_3v3_elo",None)
            rm_4v4_elo_data = leaderBoards.get("rm_4v4_elo",None)
            qm_3v3_data = leaderBoards.get("qm_3v3",None)
            qm_4v4_data = leaderBoards.get("qm_4v4",None)

            user_data = {}






            if rm_solo_data != None:
                user_data["rm_solo_rank_rating"] = rm_solo_data.get("rating", None)
                user_data["rm_solo_rank_level"] = rm_solo_data.get("rank_level", None)
                user_data["rm_solo_rank"] = rm_solo_data.get("rank", None)
                user_data["rm_solo_games_count"] = rm_solo_data.get("games_count",None)
                user_data["rm_solo_wins_count"] = rm_solo_data.get("wins_count",None)
                user_data["rm_solo_win_rate"] = rm_solo_data.get("win_rate",None)
                user_data["rm_solo_season"] = rm_solo_data.get("season",None)

            if pre_rm_solo_data != None:
                logger.info(f"pre_rm_solo_data : {pre_rm_solo_data}")
                user_data["pre_rm_solo_rating"] = pre_rm_solo_data[0].get("rating", None)
                user_data["pre_rm_solo_rank"] = pre_rm_solo_data[0].get("rank", None)
                user_data["pre_rm_solo_rank_level"] = pre_rm_solo_data[0].get("rank_level", None)
                user_data["pre_rm_solo_games_count"] = pre_rm_solo_data[0].get("games_count",None)
                user_data["pre_rm_solo_wins_count"] = pre_rm_solo_data[0].get("wins_count",None)
                user_data["pre_rm_solo_win_rate"] = pre_rm_solo_data[0].get("win_rate",None)

            if rm_team_data != None:
                user_data["rm_team_rank_level"] = rm_team_data.get("rank_level",None)
                user_data["rm_team_rank_rank"] = rm_team_data.get("rank", None)
                user_data["rm_team_rank_rating"] = rm_team_data.get("rating", None)
                user_data["rm_team_games_count"] = rm_team_data.get("games_count",None)
                user_data["rm_team_wins_count"] = rm_team_data.get("wins_count",None)
                user_data["rm_team_win_rate"] = rm_team_data.get("win_rate",None)
                user_data["rm_team_season"] = rm_team_data.get("season",None)

            if pre_rm_team_data!=None:
                user_data["pre_rm_team_rating"] = pre_rm_team_data[0].get("rating", None)
                user_data["pre_rm_team_rank"] = pre_rm_team_data[0].get("rank", None)
                user_data["pre_rm_team_rank_level"] = pre_rm_team_data[0].get("rank_level", None)
                user_data["pre_rm_team_games_count"] = pre_rm_team_data[0].get("games_count",None)
                user_data["pre_rm_team_wins_count"] = pre_rm_team_data[0].get("wins_count",None)
                user_data["pre_rm_team_win_rate"] = pre_rm_team_data[0].get("win_rate",None)

            if rm_3v3_elo_data != None:
                user_data["rm_3v3_elo_rating"] = rm_3v3_elo_data.get("rating", None)
                user_data["rm_3v3_elo_rank"] = rm_3v3_elo_data.get("rank", None)
                user_data["rm_3v3_elo_rank_level"] = rm_3v3_elo_data.get("rank_level", None)
                user_data["rm_3v3_elo_games_count"] = rm_3v3_elo_data.get("games_count",None)
                user_data["rm_3v3_elo_wins_count"] = rm_3v3_elo_data.get("wins_count",None)
                user_data["rm_3v3_elo_win_rate"] = rm_3v3_elo_data.get("win_rate",None)

            if rm_4v4_elo_data != None:
                user_data["rm_4v4_elo_rating"] = rm_4v4_elo_data.get("rating", None)
                user_data["rm_4v4_elo_rank"] = rm_4v4_elo_data.get("rank", None)
                user_data["rm_4v4_elo_rank_level"] = rm_4v4_elo_data.get("rank_level", None)
                user_data["rm_4v4_elo_games_count"] = rm_4v4_elo_data.get("games_count",None)
                user_data["rm_4v4_elo_wins_count"] = rm_4v4_elo_data.get("wins_count",None)
                user_data["rm_4v4_elo_win_rate"] = rm_4v4_elo_data.get("win_rate",None)

            if qm_3v3_data != None:
                user_data["qm_3v3_rating"] = qm_3v3_data.get("rating", None)
                user_data["qm_3v3_rank"] = qm_3v3_data.get("rank", None)
                user_data["qm_3v3_rank_level"] = qm_3v3_data.get("rank_level", None)
                user_data["qm_3v3_games_count"] = qm_3v3_data.get("games_count",None)
                user_data["qm_3v3_wins_count"] = qm_3v3_data.get("wins_count",None)
                user_data["qm_3v3_win_rate"] = qm_3v3_data.get("win_rate",None)

            if qm_4v4_data != None:
                user_data["qm_4v4_rating"] = qm_4v4_data.get("rating", None)
                user_data["qm_4v4_rank"] = qm_4v4_data.get("rank", None)
                user_data["qm_4v4_rank_level"] = qm_4v4_data.get("rank_level", None)
                user_data["qm_4v4_games_count"] = qm_4v4_data.get("games_count",None)
                user_data["qm_4v4_wins_count"] = qm_4v4_data.get("wins_count",None)
                user_data["qm_4v4_win_rate"] = qm_4v4_data.get("win_rate",None)
            logger.info(f"user_data : {user_data}")

            return;













            return player_name, profile_id

        return;

    except json.decoder.JSONDecodeError:
        logger.error("Not a valid profile_id")
    except Exception:
        logger.exception("An unexpected error occurred when checking player: %s", e)

    # 然后尝试查询
    try:
        url = f"https://aoe4world.com/api/v0/players/search?query={text}"
        resp = json.loads(session.get(url).text)
        if resp['players']:
            profile_id = resp['players'][0]['profile_id']
            player_name = resp['players'][0]['name']
            # steam_id = resp['players'][0].get('steam_id')
            logger.info(
                f"Found player by query: {player_name} ({profile_id})"
            )
            return player_name, profile_id
    except Exception:
        logger.exception("")

    logger.info(f"Failed to find a player with: {text}")
    return None, None


