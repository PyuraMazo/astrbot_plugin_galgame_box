import json

from astrbot.api import AstrBotConfig

from ..type.exceptions import AuthorityException, NoResultException
from ..type.inner_models import CommandType
from ..type.touchgal_models import TouchGalResourceResponse, TouchGalWorkResponse
from .http import Http


class TouchGal:
    base_url = "https://www.touchgal.ink/"
    headers = {
        "Content-Type": "application/json",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
        "referer": base_url,
        "x-requested-with": "kun-fetch",
    }

    @classmethod
    async def initialize(cls, config: AstrBotConfig):
        from ..services import Services

        cls.http = Services.get(Http)
        safety_setting = config.get("safetySetting", {})

        cls.proxy = safety_setting.get("proxy", None)

        nsfw_enable = (
            "all" if config.get("safetySetting", {}).get("enableNSFW", False) else "sfw"
        )
        token = safety_setting.get("touchgalToken", "")
        cf = safety_setting.get("cfClearance", "")
        cls.cookies = {"kun-patch-setting-store|state|data|kunNsfwEnable": nsfw_enable}
        if token:
            cls.cookies["kun-galgame-patch-moe-token"] = token
        if cf:
            cls.cookies["cf_clearance"] = cf

        return cls()

    async def request_vn_by_search(
        self, cmd: CommandType, keyword: str, **kwargs
    ) -> tuple[list[TouchGalWorkResponse], int]:
        query_string = json.dumps(
            [{"type": "keyword", "name": i} for i in keyword.strip().split(" ")]
        )
        payload = {
            "queryString": query_string,
            "limit": kwargs.get("limit", 12),
            "searchOption": {
                "searchInIntroduction": False,
                "searchInAlias": kwargs.get("searchInAlias", True),
                "searchInTag": kwargs.get("searchInTag", False),
            },
            "page": kwargs.get("page", 1),
            "selectedType": "all",
            "selectedLanguage": "all",
            "selectedPlatform": "all",
            "sortField": "resource_update_time",
            "sortOrder": "desc",
            "selectedYears": ["all"],
            "selectedMonths": ["all"],
        }
        res = await self.http.post(
            self.base_url + "api/search/",
            payload,
            cookies=self.cookies,
            headers=self.headers,
            proxy=self.proxy,
            handle_cf=True,
        )
        if isinstance(res, dict):
            if res["galgames"] and res["total"] > 0:
                return [
                    TouchGalWorkResponse.model_validate(i) for i in res["galgames"]
                ], res["total"]
            else:
                raise NoResultException(cmd, keyword)
        else:
            raise AuthorityException(str(res))

    async def request_random(self) -> str:
        resp = await self.http.get(
            self.base_url + "api/home/random",
            "json",
            cookies=self.cookies,
            proxy=self.proxy,
            handle_cf=True,
        )
        if isinstance(resp, dict):
            return resp["uniqueId"]
        else:
            raise AuthorityException(str(resp))

    async def request_html(self, unique_id: str) -> str:
        return await self.http.get(
            self.base_url + unique_id,
            cookies=self.cookies,
            proxy=self.proxy,
            handle_cf=True,
        )

    async def request_download(
        self, touchgal_id: int
    ) -> list[TouchGalResourceResponse]:
        resource_url = f"{self.base_url}api/patch/resource?patchId={touchgal_id}"
        res = await self.http.get(
            resource_url,
            "json",
            cookies=self.cookies,
            proxy=self.proxy,
            handle_cf=True,
        )
        return [TouchGalResourceResponse.model_validate(i) for i in res]
