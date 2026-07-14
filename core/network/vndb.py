import asyncio
import math

from astrbot.api import AstrBotConfig

from ..type.exceptions import InternetException, NoResultException, ResponseException
from ..type.inner_models import CommandType, vndb_command_fields
from ..type.outer_models import (
    VNDBCharacterResponse,
    VNDBProducerResponse,
    VNDBReleaseResponse,
    VNDBVnResponse,
)
from .http import Http


class Vndb:
    kana_url = "https://api.vndb.org/kana/"

    @classmethod
    async def initialize(cls, config: AstrBotConfig):
        from ..services import Services

        cls.http = Services.get(Http)

        cls.producer_vns = (
            config.get("producerSetting", {}).get("producerVns", 9)
            if config.get("producerSetting", {}).get("producerVns", 9) != 0
            else 0
        )
        cls.event_rating = config.get("eventSetting", {}).get("eventRating", 75)
        cls.schedule_content = (
            config.get("scheduleSetting", {}).get("scheduleContent", "c")
        )[0]

        return cls()

    async def request_by_vn(self, keyword: str, payload=None) -> list[VNDBVnResponse]:
        url = self.kana_url + "vn"
        payload = payload or {
            "filters": ["search", "=", keyword],
            "fields": vndb_command_fields["vn"],
        }
        res = await self.http.post(url, payload)
        if not res:
            raise ResponseException(url)
        if not res["results"]:
            raise NoResultException(CommandType.VN, keyword)

        return [VNDBVnResponse.model_validate(i) for i in res["results"]]

    async def request_by_character(
        self, keyword: str, payload=None
    ) -> list[VNDBCharacterResponse]:
        url = self.kana_url + "character"
        payload = payload or {
            "filters": ["search", "=", keyword],
            "fields": vndb_command_fields["character"],
        }
        res = await self.http.post(url, payload)
        if not res:
            raise ResponseException(url)
        if not res["results"]:
            raise NoResultException(CommandType.CHARACTER, keyword)

        return [VNDBCharacterResponse.model_validate(i) for i in res["results"]]

    async def request_by_producer(
        self, keyword: str, payload=None
    ) -> tuple[list[VNDBProducerResponse], list[list[VNDBVnResponse]]]:
        url = self.kana_url + "producer"
        pro_payload = payload or {
            "filters": ["search", "=", keyword],
            "fields": vndb_command_fields["producer"],
        }
        unformat_res = await self.http.post(url, pro_payload)

        if not unformat_res:
            raise ResponseException(url)
        pro_res = [
            VNDBProducerResponse.model_validate(i) for i in unformat_res["results"]
        ]

        if not pro_res:
            raise NoResultException(CommandType.PRODUCER, keyword)
        vn_url = self.kana_url + "vn"
        vn_fields = vndb_command_fields["vn_short"]
        vns: list[list[VNDBVnResponse]] = []
        for item in pro_res:
            vn_payload = {
                "filters": ["developer", "=", ["id", "=", item.id]],
                "fields": vn_fields,
                "sort": "rating",
                "reverse": True,
                "results": self.producer_vns,
            }

            vns_res = (await self.http.post(vn_url, vn_payload))["results"]
            vns.append([VNDBVnResponse.model_validate(i) for i in vns_res])

        return pro_res, vns

    async def request_by_id(
        self, real_type: CommandType, keyword: str
    ) -> (
        list[VNDBVnResponse]
        | list[VNDBCharacterResponse]
        | tuple[list[VNDBProducerResponse], list[list[VNDBVnResponse]]]
    ):
        payload = {
            "filters": ["id", "=", keyword],
            "fields": vndb_command_fields[real_type.value],
        }
        try:
            if real_type == CommandType.VN:
                return await self.request_by_vn(keyword, payload)
            elif real_type == CommandType.CHARACTER:
                return await self.request_by_character(keyword, payload)
            elif real_type == CommandType.PRODUCER:
                return await self.request_by_producer(keyword, payload)
            else:
                raise NotImplementedError
        except NoResultException:
            raise NoResultException(CommandType.ID, keyword)

    async def request_by_event(
        self, date: list[str]
    ) -> tuple[list[VNDBVnResponse], list[VNDBCharacterResponse]]:
        vn_url = self.kana_url + "vn"
        cha_url = self.kana_url + "character"
        released = [
            ["released", "=", f"{year}-{date[1]}-{date[2]}"]
            for year in range(1990, int(date[0]))
        ]
        vn_payload = {
            "filters": ["and", ["or", *released], ["rating", ">=", self.event_rating]],
            "fields": vndb_command_fields["vn_short"],
        }
        cha_payload = {
            "filters": [
                "and",
                ["birthday", "=", [int(date[1]), int(date[2])]],
                ["vn", "=", ["rating", ">=", self.event_rating]],
            ],
            "fields": vndb_command_fields["character_event"],
        }
        res = await asyncio.gather(
            self.http.post(vn_url, vn_payload), self.http.post(cha_url, cha_payload)
        )
        _vn = [VNDBVnResponse.model_validate(i) for i in res[0]["results"]]
        _cha = [VNDBCharacterResponse.model_validate(j) for j in res[1]["results"]]
        return _vn, _cha

    async def request_by_event_vn(
        self, date: list[str]
    ) -> tuple[VNDBVnResponse, list[VNDBCharacterResponse]]:
        vn_url = self.kana_url + "vn"
        cha_url = self.kana_url + "character"
        released = [
            ["released", "=", f"{year}-{date[1]}-{date[2]}"]
            for year in range(1990, int(date[0]))
        ]
        vn_payload = {
            "filters": ["or", *released]
            if self.schedule_content != "c"
            else ["and", ["or", *released], ["votecount", ">", 50]],
            "fields": vndb_command_fields["vn"],
            "results": 1,
            "sort": "votecount" if self.schedule_content == "b" else "rating",
            "reverse": True,
        }
        res = await self.http.post(vn_url, vn_payload)
        if not res:
            raise NoResultException(CommandType.EVENT_TIMED, "/".join(date))

        try:
            the_vn = VNDBVnResponse.model_validate(res["results"][0])

            cha_payload = {
                "filters": [
                    "and",
                    ["vn", "=", ["id", "=", the_vn.id]],
                    ["or", ["role", "=", "main"], ["role", "=", "primary"]],
                ],
                "fields": vndb_command_fields["character_event"],
            }
            cha_res = await self.http.post(cha_url, cha_payload)
            the_cha = [
                VNDBCharacterResponse.model_validate(j) for j in cha_res["results"]
            ]
            return the_vn, the_cha
        except InternetException:
            raise NoResultException(CommandType.EVENT_TIMED, "/".join(date))

    async def request_by_event_cha(
        self, date: list[str]
    ) -> tuple[VNDBCharacterResponse, list[VNDBVnResponse]]:
        cha_url = self.kana_url + "character"
        vn_url = self.kana_url + "vn"
        cha_payload = {
            "filters": [
                "and",
                ["birthday", "=", [int(date[1]), int(date[2])]],
                ["vn", "=", ["rating", ">=", self.event_rating]],
                ["role", "=", "main"],
            ],
            "fields": vndb_command_fields["character"],
        }
        res = await self.http.post(cha_url, cha_payload)
        if not res:
            raise NoResultException(CommandType.EVENT_TIMED, "/".join(date))

        try:
            cha = [VNDBCharacterResponse.model_validate(j) for j in res["results"]]

            vn_cha_map = {n.id: m.id for m in cha for n in m.vns}
            filters = [["id", "=", i] for i in vn_cha_map]
            search_best_vn_payload = {
                "filters": ["or", *filters]
                if self.schedule_content != "c"
                else ["and", ["or", *filters], ["votecount", ">", 50]],
                "fields": "id",
                "results": 1,
                "sort": "votecount" if self.schedule_content == "b" else "rating",
                "reverse": True,
            }

            best: dict[str, list[dict]] = await self.http.post(
                vn_url, search_best_vn_payload
            )

            the_cha_id = vn_cha_map[best["results"][0]["id"]]
            for i in cha:
                if i.id == the_cha_id:
                    best_vn_ids = [
                        ["id", "=", k] for k, v in vn_cha_map.items() if v == the_cha_id
                    ]

                    vn_payload = {
                        "filters": ["or", *best_vn_ids],
                        "fields": vndb_command_fields["vn_short"],
                    }
                    vns = await self.http.post(vn_url, vn_payload)
                    vn = [VNDBVnResponse.model_validate(i) for i in vns["results"]]
                    return i, vn
        except InternetException:
            raise NoResultException(CommandType.EVENT_TIMED, "/".join(date))
        else:
            raise Exception("从已知cha列表中检索失败")

    async def request_by_find(
        self, character: str, vn: str
    ) -> list[VNDBCharacterResponse]:
        url = self.kana_url + "character"
        fields = vndb_command_fields["character_short"]
        payload = {
            "filters": [
                "and",
                ["search", "=", character],
                ["vn", "=", ["search", "=", vn]],
            ],
            "fields": fields,
            "results": 1,
        }
        res = await self.http.post(url, payload)
        return [VNDBCharacterResponse.model_validate(i) for i in res["results"]]

    async def request_by_release(
        self, id_list: list[int], length: int
    ) -> list[VNDBReleaseResponse]:
        query = "release"
        url = self.kana_url + query
        fields = vndb_command_fields[query]

        count = math.ceil(length / 100)
        res = []
        for page in range(count):
            start = page * 100
            end = (page + 1) * 100 if (page + 1) * 100 <= length else length
            games = [["extlink", "=", ["steam", i]] for i in id_list[start:end]]
            payload = {"filters": ["or", *games], "fields": fields, "results": 100}

            res.extend((await self.http.post(url, payload))["results"])
        return [VNDBReleaseResponse.model_validate(i) for i in res]
