from typing import Optional

from astrbot.api import AstrBotConfig

from .http import Http, get_http
from ..api.exception import ArgsOrNullException
from ..api.model import (
    SteamOwnerResponse,
    SteamProfileResponse,
    SteamAchievementsResponse,
    SteamGameResponse,
)
from ..api.type import SteamData


class SteamRequest:
    def __init__(self):
        self.owner_url = (
            "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
        )
        self.profile_url = (
            "http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/"
        )
        self.achievement_url = (
            "http://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001/"
        )
        self.recently_url = (
            "http://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v0001/"
        )

        self.http: Optional[Http] = None

    async def initialize(self, config: AstrBotConfig):
        self.http = get_http()

        await self.http.initialize(config)

    async def terminate(self):
        await self.http.terminate()

    async def request_owner(self, data: SteamData) -> SteamOwnerResponse:
        payload = {
            "key": data.key,
            "steamid": data.steam_id,
            "include_appinfo": 1,
            "include_played_free_games": 1,
        }
        res = await self.http.get(self.owner_url, "json", params=payload)
        resp = res.get("response", None)

        if resp is None:
            raise ArgsOrNullException
        else:
            return SteamOwnerResponse.model_validate(resp)

    async def request_profile(self, data: SteamData) -> SteamProfileResponse:
        payload = {"key": data.key, "steamids": data.steam_id}
        res = await self.http.get(self.profile_url, "json", params=payload)
        return SteamProfileResponse.model_validate(
            res.get("response", {}).get("players", [])[0]
        )

    async def request_achievement(self, data: SteamData, appid: int) -> float | str:
        payload = {"key": data.key, "steamid": data.steam_id, "appid": appid}
        res = await self.http.get(self.achievement_url, "json", params=payload)
        if not res["playerstats"]["success"]:
            return "-无成就系统-"

        achi = res["playerstats"]["achievements"]
        done = [i for i in achi if i["achieved"]]
        return round(len(done) / len(achi), 2)

    async def request_recently(self, data: SteamData) -> list[SteamGameResponse]:
        payload = {"key": data.key, "steamid": data.steam_id}
        res = await self.http.get(self.recently_url, "json", params=payload)
        return [SteamGameResponse.model_validate(i) for i in res["response"]["games"]]


_steam_request: Optional[SteamRequest] = None


def get_steam_request():
    global _steam_request
    if _steam_request is None:
        _steam_request = SteamRequest()
    return _steam_request
