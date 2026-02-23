import json
from typing import Optional

from astrbot.core import AstrBotConfig

from .http import Http, get_http
from ..api.model import TouchGalResponse, ResourceResponse


class TouchGalRequest:
    def __init__(self):
        self.base_url = 'https://www.touchgal.top/'
        self.search_api = self.base_url + 'api/search/'
        self.touchgal_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ0b3VjaGdhbCIsImF1ZCI6InRvdWNoZ2FsX2FkbWluIiwidWlkIjozOTY2NDEsIm5hbWUiOiJQeXVyYSIsInJvbGUiOjEsImlhdCI6MTc3MTM5NDg1OSwiZXhwIjoxNzczOTg2ODU5fQ.BihJjjqjoeHIX1IjgEQrzlTwu520YInfvUOrjnvG1iI'


        self.http: Optional[Http] = None
        self.cookies: Optional[dict] = None

    async def initialize(self, config: AstrBotConfig):
        self.http = get_http()

        await self.http.initialize(config)

        nsfw = 'all' if config.get('internetSetting', {}).get('enableNSFW', 'False') else 'sfw'
        cf_clearance = config.get('basicSetting', {}).get('clearanceCookie', '')
        self.cookies = {
            'kun-galgame-patch-moe-token': self.touchgal_token,
            'kun-patch-setting-store|state|data|kunNsfwEnable': nsfw,
            'cf_clearance': cf_clearance
        }

    async def terminate(self):
        await self.http.terminate()

    async def request_vn_by_search(self, keyword: str, **kwargs) -> tuple[list[TouchGalResponse], int]:
        query_string = json.dumps([{"type": "keyword", "name": i} for i in keyword.strip().split(' ')])
        payload = {
            "queryString": query_string,
            "limit": kwargs.get('limit', 12),
            "searchOption": {
                "searchInIntroduction": False,
                "searchInAlias": kwargs.get('searchInAlias', True),
                "searchInTag": kwargs.get('searchInTag', False),
            },
            "page": kwargs.get('page', 1),
            "selectedType": "all",
            "selectedLanguage": "all",
            "selectedPlatform": "all",
            "sortField": "resource_update_time",
            "sortOrder": "desc",
            "selectedYears": ["all"],
            "selectedMonths": ["all"]
        }
        res = await self.http.post(self.search_api, payload, cookies=self.cookies)
        return [TouchGalResponse.model_validate(i) for i in res['galgames']], res['total']

    async def request_random(self) -> str:
        return (await self.http.get(self.base_url + 'api/home/random', 'json', cookies=self.cookies))['uniqueId']

    async def request_html(self, unique_id: str) -> str:
        return await self.http.get(self.base_url + unique_id, cookies=self.cookies)

    async def request_download(self, touchgal_id: int) -> list[ResourceResponse]:
        resource_url = f'{self.base_url}api/patch/resource?patchId={touchgal_id}'
        res = await self.http.get(resource_url, 'json', cookies=self.cookies)
        return [ResourceResponse.model_validate(i) for i in res]


_touchgal_request: Optional[TouchGalRequest] = None
def get_touchgal_request():
    global _touchgal_request
    if _touchgal_request is None:
        _touchgal_request = TouchGalRequest()
    return _touchgal_request