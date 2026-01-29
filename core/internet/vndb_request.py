from typing import Optional

from astrbot.api import AstrBotConfig

from .http import Http, get_http
from ..api.type import CommandType, CommandBody, AnimeTraceModel
from ..api.model import VNDBVnResponse, VNDBCharacterResponse, VNDBProducerResponse, TouchGalResponse, ResourceResponse, AnimeTraceResponse
from ..api.exception import ResponseException, NoResultException, InternetException, CodeException
from ..api.const import id2command, vndb_command_fields


class VNDBRequest:
    def __init__(self):
        self.kana_url = 'https://api.vndb.org/kana/'

        self.http: Optional[Http] = None
        self.producer_vns: Optional[int] = None


    async def initialize(self, config: AstrBotConfig):
        self.http = get_http()


        await self.http.initialize(config)
        self.producer_vns = config.get('searchSetting', {}).get('producerVns', 10) \
            if config.get('searchSetting', {}).get('producerVns', 10) != 0 \
            else 0

    async def terminate(self):
        await self.http.terminate()


    def _build_self_payload(self, cmd_type: CommandType, keyword: str) -> dict[str, object]:
        if cmd_type == CommandType.ID:
            fields = vndb_command_fields[id2command[keyword[0]]]
            return {
                "filters": ["id", "=", keyword],
                "fields": fields,
            }
        else:
            fields = vndb_command_fields[cmd_type.value]
            return {
                "filters": ["search", "=", keyword],
                "fields": fields,
            }


    async def request_by_vn(self, keyword: str, payload = None) \
            -> list[VNDBVnResponse]:
        url = self.kana_url + CommandType.VN.value
        payload = self._build_self_payload(CommandType.VN, keyword) if payload is None else payload
        res = await self.http.post(url, payload)
        if not res:
            raise ResponseException(url)
        if not res["results"]:
            raise NoResultException(f'{CommandType.VN}-{keyword}')

        return [VNDBVnResponse.model_validate(i) for i in res["results"]]


    async def request_by_character(self, keyword: str, payload = None) \
            -> list[VNDBCharacterResponse]:
        url = self.kana_url + CommandType.CHARACTER.value
        payload = self._build_self_payload(CommandType.CHARACTER, keyword) if payload is None else payload
        res = await self.http.post(url, payload)
        if not res:
            raise ResponseException(url)
        if not res["results"]:
            raise NoResultException(f'{CommandType.CHARACTER}-{keyword}')

        return [VNDBCharacterResponse.model_validate(i) for i in res["results"]]



    async def request_by_producer(self, keyword: str, payload = None) \
            -> tuple[list[VNDBProducerResponse], list[list[VNDBVnResponse]]]:
        url = self.kana_url + CommandType.PRODUCER.value
        pro_payload = self._build_self_payload(CommandType.PRODUCER, keyword) if payload is None else payload
        unformat_res = await self.http.post(url, pro_payload)
        if not unformat_res:
            raise ResponseException(url)

        pro_res = [VNDBProducerResponse.model_validate(i) for i in unformat_res["results"]]
        if not pro_res:
            raise NoResultException(f'{CommandType.PRODUCER}-{keyword}')

        vn_url = self.kana_url + CommandType.VN.value
        vn_fields = vndb_command_fields['vn_short']
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

    async def request_by_id(self, cmd_type: CommandType, keyword: str) \
            -> list[VNDBVnResponse] | list[VNDBCharacterResponse] | tuple[list[VNDBProducerResponse], list[list[VNDBVnResponse]]]:
        handle_type_value = id2command[keyword[0]]
        payload = self._build_self_payload(cmd_type, keyword)
        try:
            if handle_type_value == CommandType.VN.value:
                return await self.request_by_vn(keyword, payload)
            elif handle_type_value == CommandType.CHARACTER.value:
                return await self.request_by_character(keyword, payload)
            elif handle_type_value == CommandType.PRODUCER.value:
                return await self.request_by_producer(keyword, payload)
            else:
                raise NotImplementedError
        except NoResultException:
            raise NoResultException(f'{cmd_type}-{keyword}')

    async def request_by_find(self, character: str, vn: str) -> list[VNDBCharacterResponse]:
        url = self.kana_url + CommandType.CHARACTER.value
        fields = vndb_command_fields['character_short']
        payload = {
            "filters": ['and', ["search", "=", character], ['vn', '=', ['search', '=', vn]]],
            "fields": fields,
            "results": 1
        }
        res = await self.http.post(url, payload)
        return [VNDBCharacterResponse.model_validate(i) for i in res["results"]]



_vndb_request: Optional[VNDBRequest] = None
def get_vndb_request():
    global _vndb_request
    if _vndb_request is None:
        _vndb_request = VNDBRequest()
    return _vndb_request