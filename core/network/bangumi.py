from astrbot.api import AstrBotConfig, logger

from ..type.bangumi_models import BangumiSubjectResponse
from ..type.exceptions import NoResultException
from ..type.inner_models import CommandType
from .http import Http


class Bangumi:
    bangumi_url = "https://api.bgm.tv/"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "PyuraMazo/astrbot_plugin_galgame_box (https://github.com/PyuraMazo/astrbot_plugin_galgame_box)",
    }

    @classmethod
    async def initialize(cls, config: AstrBotConfig):
        from ..services import Services

        cls.http = Services.get(Http)

        safety_setting = config.get("safetySetting", {})

        cls.nsfw_enable = safety_setting.get("enableNSFW", False)
        token = safety_setting.get("bangumiToken", "")
        cls.headers["Authorization"] = f"Bearer {token}"
        if cls.nsfw_enable and not token:
            logger.warning("Bangumi Access Token不存在，无法开启NSFW模式。")

        cls.proxy = safety_setting.get("proxy", None)

        return cls()

    async def request_game_title(
        self, keyword: str, extra_filter: dict = None
    ) -> list[BangumiSubjectResponse]:
        url = f"{self.bangumi_url}v0/search/subjects"

        filter_body = {
            "type": [4],
            "nsfw": self.nsfw_enable,
        }
        if extra_filter:
            filter_body += extra_filter
        body = {
            "keyword": keyword,
            "sort": "rank",
            "filter": filter_body,
        }
        res = await self.http.post(url, body, headers=self.headers, proxy=self.proxy)

        return [BangumiSubjectResponse.model_validate(i) for i in res.get("data", [])]

    async def request_by_vndb_id(
        self, cmd: CommandType, keyword: str, vndb_id: str
    ) -> list[BangumiSubjectResponse]:
        unfiltered = await self.request_game_title(keyword)

        res = []
        for game in unfiltered:
            for info in game.infobox:
                if (
                    info is not None
                    and info.key == "链接"
                    and isinstance(info.value, list)
                ):
                    for kv in info.value:
                        if (
                            kv.get("k", "").upper() == "VNDB"
                            and kv.get("v", "./.").split("/")[-1] == vndb_id
                        ):
                            res.append(game)
        if not res:
            raise NoResultException(cmd, keyword)
        return res
