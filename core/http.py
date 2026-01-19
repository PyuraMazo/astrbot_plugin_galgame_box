import aiohttp
import json
import asyncio
from typing import Optional

from astrbot.api import AstrBotConfig, logger

from .api import const
from .api.type import CommandType, CommandBody
from .api.model import VNDBVnResponse, VNDBCharacterResponse, VNDBProducerResponse, TouchGalResponse, ResourceResponse
from .api.exception import *


class Http:
    _instance: Optional['Http'] = None
    _initialized: bool = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config):
        if self.__class__._initialized:
            return

        self.timeout_times = config['basicSetting']['requestTimeout']
        self.headers = {
            "Content-Type": "application/json"
        }
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=config['basicSetting']['requestTime'])
        )

        self.__class__._initialized = True




    async def get(self, url: str, res_type: str = 'text', **kwargs) -> str | dict | bytes:
        count = 0
        while count < self.timeout_times:
            try:
                if res_type == 'json':
                    async with self.session.get(url, **kwargs) as response:
                        return await response.json()
                elif res_type == 'byte':
                    async with self.session.get(url, **kwargs) as response:
                        return await response.read()
                else:
                    async with self.session.get(url, **kwargs) as response:
                        return await response.text()
            except Exception as e:
                count += 1
                await asyncio.sleep(0.5)
                logger.info(str(e) + '网络请求失败一次...')
        raise InternetException(url)


    async def post(self, url: str, data: dict, **kwargs) -> str | dict | bytes:
        count = 0
        while count < self.timeout_times:
            try:
                async with self.session.post(url, headers=self.headers, json=data, **kwargs) as response:
                    return await response.json()
            except Exception as e:
                count += 1
                await asyncio.sleep(0.5)
                logger.info(str(e) + '网络请求失败一次...')
        raise InternetException(url)

    async def close(self):
        if not self.session.closed:
            await self.session.close()


class VNDBRequest:
    kana_url = 'https://api.vndb.org/kana/'


    def __init__(self, config: AstrBotConfig, command_body: CommandBody):
        self.producer_vns: int = config['searchSetting']['producerVns'] if config['searchSetting']['producerVns'] != 0 else 0
        self.type = command_body.type
        self.value = command_body.value
        self.url = self.kana_url + self.type.value
        self.http = Http(config)



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
        payload = self._build_self_payload()
        res = await self.http.post(self.url, payload)
        if not res: raise ResponseException
        if not res["results"]: raise NoGameException

        if self.type == CommandType.VN:
            return [VNDBVnResponse.model_validate(i) for i in res["results"]]
        elif self.type == CommandType.CHARACTER:
            return [VNDBCharacterResponse.model_validate(i) for i in res["results"]]
        else: raise NotImplementedError

    async def request_by_producer(self) -> tuple[list[VNDBProducerResponse], list[list[VNDBVnResponse]]]:
        pro_payload = self._build_self_payload()
        unformat_res = await self.http.post(self.url, pro_payload)
        if not unformat_res: raise ResponseException

        pro_res = [VNDBProducerResponse.model_validate(i) for i in unformat_res["results"]]
        if not pro_res: raise NoGameException


        vn_url = self.kana_url + CommandType.VN.value
        vn_fields = const.vndb_command_fields['vn_of_producer']
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
        # payload = self._build_self_payload()
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


class TouchGalRequest:
    base_url = 'https://www.touchgal.top/'
    search_api = base_url + 'api/search/'


    def __init__(self, config: AstrBotConfig):
        self.config = config
        self.http = Http(self.config)
        self.nsfw = {'kun-patch-setting-store|state|data|kunNsfwEnable': 'all' if self.config['searchSetting']['enableNSFW'] else 'sfw'}


    async def request_vn_by_search(self, keyword: str) -> tuple[list[TouchGalResponse], int]:
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
        return (await self.http.get(self.base_url + 'api/home/random', 'json', cookies=self.nsfw))['uniqueId']

    async def request_html(self, unique_id: str) -> str:
        return await self.http.get(self.base_url + unique_id, cookies=self.nsfw)

    async def request_resources(self, touchgal_id: int) -> list[ResourceResponse]:
        resource_url = f'{self.base_url}api/patch/resource?patchId={touchgal_id}'
        res = await self.http.get(resource_url, 'json', cookies=self.nsfw)
        return [ResourceResponse.model_validate(i) for i in res]
