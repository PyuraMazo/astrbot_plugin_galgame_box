import json

from astrbot.api import AstrBotConfig

from .http import get_http
from .api import const
from .api.type import CommandType, CommandBody, AnimeTraceModel
from .api.model import VNDBVnResponse, VNDBCharacterResponse, VNDBProducerResponse, TouchGalResponse, ResourceResponse, AnimeTraceResponse
from .api.exception import ResponseException, NoResultException, InternetException, CodeException


class VNDBRequest:
    kana_url = 'https://api.vndb.org/kana/'


    def __init__(self, config: AstrBotConfig, command_body: CommandBody):
        self.config = config
        self.producer_vns: int = config.get('searchSetting', {}).get('producerVns', 10) \
            if self.config.get('searchSetting', {}).get('producerVns', 10) != 0 \
            else 0
        self.type = command_body.type
        self.value = command_body.value
        self.url = self.kana_url + self.type.value

        self.http = None

    async def initialize(self):
        if not self.http:
            self.http = await get_http(self.config)

    def _build_self_payload(self) -> dict[str, object]:
        if self.type == CommandType.ID:
            fields = const.vndb_command_fields[const.id2command[self.value[0]]]
            return {
                "filters": ["id", "=", self.value],
                "fields": fields,
            }
        else:
            fields = const.vndb_command_fields[self.type.value]
            return {
                "filters": ["search", "=", self.value],
                "fields": fields,
            }


    async def request_simply(self) -> list[VNDBVnResponse] | list[VNDBCharacterResponse]:
        await self.initialize()

        payload = self._build_self_payload()
        res = await self.http.post(self.url, payload)
        if not res:
            raise ResponseException(self.url)
        if not res["results"]:
            raise NoResultException(f'{self.type}-{self.value}')

        if self.type == CommandType.VN:
            return [VNDBVnResponse.model_validate(i) for i in res["results"]]
        elif self.type == CommandType.CHARACTER:
            return [VNDBCharacterResponse.model_validate(i) for i in res["results"]]
        else: raise NotImplementedError

    async def request_by_producer(self) -> tuple[list[VNDBProducerResponse], list[list[VNDBVnResponse]]]:
        await self.initialize()

        pro_payload = self._build_self_payload()
        unformat_res = await self.http.post(self.url, pro_payload)
        if not unformat_res:
            raise ResponseException(self.url)

        pro_res = [VNDBProducerResponse.model_validate(i) for i in unformat_res["results"]]
        if not pro_res:
            raise NoResultException(f'{self.type}-{self.value}')


        vn_url = self.kana_url + CommandType.VN.value
        vn_fields = const.vndb_command_fields['vn_short']
        vns: list[list[VNDBVnResponse]] = []
        for item in pro_res:
            vn_payload = {
                "filters": ['developer', '=', ['id', '=', item.id]],
                "fields": vn_fields,
                "sort": 'rating',
                "reverse": True,
                "results": self.producer_vns
            }

            vns_res = (await self.http.post(vn_url, vn_payload))['results']
            vns.append([VNDBVnResponse.model_validate(i) for i in vns_res])

        return pro_res, vns

    async def request_by_id(self) \
            -> list[VNDBVnResponse] | list[VNDBCharacterResponse] | tuple[list[VNDBProducerResponse], list[list[VNDBVnResponse]]]:
        await self.initialize()

        if self.value[0] == CommandType.VN.value[0]:
            self.url = self.kana_url + CommandType.VN.value
            self.type = CommandType.VN
            return await self.request_simply()
        elif self.value[0] == CommandType.CHARACTER.value[0]:
            self.url = self.kana_url + CommandType.CHARACTER.value
            self.type = CommandType.CHARACTER
            return await self.request_simply()
        elif self.value[0] == CommandType.PRODUCER.value[0]:
            self.url = self.kana_url + CommandType.PRODUCER.value
            return await self.request_by_producer()
        else: raise NotImplementedError

    async def request_by_find(self, character: str, vn: str) -> list[VNDBCharacterResponse]:
        await self.initialize()

        self.url = self.kana_url + CommandType.CHARACTER.value
        fields = const.vndb_command_fields['character_short']
        payload = {
            "filters": ['and', ["search", "=", character], ['vn', '=', ['search', '=', vn]]],
            "fields": fields,
            "results": 1
        }
        res = await self.http.post(self.url, payload)
        return [VNDBCharacterResponse.model_validate(i) for i in res["results"]]


class TouchGalRequest:
    base_url = 'https://www.touchgal.top/'
    search_api = base_url + 'api/search/'


    def __init__(self, config: AstrBotConfig):
        self.config = config
        self.nsfw = {'kun-patch-setting-store|state|data|kunNsfwEnable': 'all' if self.config['searchSetting']['enableNSFW'] else 'sfw'}
        self.http = None

    async def initialize(self):
        if self.http is None:
            self.http = await get_http(self.config)

    async def request_vn_by_search(self, keyword: str) -> tuple[list[TouchGalResponse], int]:
        await self.initialize()

        query_string = json.dumps([{"type": "keyword", "name": keyword}])
        payload = {
            "queryString": query_string,
            "limit": 10,
            "searchOption": {
                "searchInIntroduction": False,
                "searchInAlias": True,
                "searchInTag": False,
            },
            "page": 1,
            "selectedType": "all",
            "selectedLanguage": "all",
            "selectedPlatform": "all",
            "sortField": "resource_update_time",
            "sortOrder": "desc",
            "selectedYears": ["all"],
            "selectedMonths": ["all"]
        }
        res = await self.http.post(self.search_api, payload, cookies=self.nsfw)

        return [TouchGalResponse.model_validate(i) for i in res['galgames']], res['total']

    async def request_random(self) -> str:
        await self.initialize()
        return (await self.http.get(self.base_url + 'api/home/random', 'json', cookies=self.nsfw))['uniqueId']

    async def request_html(self, unique_id: str) -> str:
        await self.initialize()
        return await self.http.get(self.base_url + unique_id, cookies=self.nsfw)

    async def request_resources(self, touchgal_id: int) -> list[ResourceResponse]:
        await self.initialize()
        resource_url = f'{self.base_url}api/patch/resource?patchId={touchgal_id}'
        res = await self.http.get(resource_url, 'json', cookies=self.nsfw)
        return [ResourceResponse.model_validate(i) for i in res]


class AnimeTreceRequest:
    api_url = 'https://api.animetrace.com/v1/search'

    def __init__(self, config: AstrBotConfig):
        self.config = config

        self.http = None

    async def initialize(self):
        if self.http is None:
            self.http = await get_http(self.config)

    async def request(self, url: str, model: AnimeTraceModel) -> AnimeTraceResponse:
        await self.initialize()

        resp = await self.http.post(self.api_url, self._build_payload(model, url))
        # 特定检测状态码
        code = resp.get('code', 400)
        if code != 200 and code != 0:
            raise CodeException(code)

        return AnimeTraceResponse.model_validate(resp)

    def _build_payload(self, model: AnimeTraceModel, url: str):
        return {
            'model': model.value,
            'ai_detect': 1,
            'url': url
        }