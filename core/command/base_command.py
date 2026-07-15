import asyncio
from pathlib import Path
from typing import Literal

from astrbot.api import AstrBotConfig

from ..function import Cache
from ..network import AnimeTrece, Downloader, TouchGal, Vndb
from ..services import Services
from ..type.exceptions import ArgsOrNullException
from ..type.inner_models import CommandType, bs64, template_list
from ..type.outer_models import (
    ResourceResponse,
    TouchGalResponse,
    VNDBCharacterResponse,
    VNDBProducerResponse,
    VNDBVnResponse,
)
from ..utils import File, Splicer


class BaseCommand:
    resources_dir = Path(__file__).parent / ".." / ".." / "resources"
    template_dir = resources_dir / "template"

    templates = {}
    is_init = False

    render_options = {"type": "jpeg", "quality": 100}
    support_forward = ["aiocqhttp", "qq_official", "onebot"]

    # 解决静态类型检查器警告
    downloader: Downloader | None = None
    vndb: Vndb | None = None
    touchgal: TouchGal | None = None
    animetrace: AnimeTrece | None = None
    cache: Cache | None = None
    bg: str | None = None
    font: str | None = None
    err_image: str | None = None

    session_timeout: int | None = None
    forward_limit: int | None = None
    results_limit: bool | None = None
    character_options: list | None = None

    @classmethod
    async def initialize(cls, config: AstrBotConfig):
        if not BaseCommand.is_init:
            BaseCommand.downloader = Services.get(Downloader)
            BaseCommand.vndb = Services.get(Vndb)
            BaseCommand.touchgal = Services.get(TouchGal)
            BaseCommand.animetrace = Services.get(AnimeTrece)

            BaseCommand.cache = Services.get(Cache)

            basic = config.get("basicSetting", {})
            enable_font = basic.get("enableFont", True)
            BaseCommand.session_timeout = basic.get("sessionTimeout", 30)
            BaseCommand.forward_limit = basic.get("forwardLimit", 10)
            BaseCommand.results_limit = basic.get("resultsLimit", False)
            BaseCommand.character_options = config.get("characterSetting", {}).get(
                "characterOptions", []
            )

            BaseCommand.bg = await File.read_buffer2base64(
                BaseCommand.resources_dir / "image" / "pixiv139681518.jpg"
            )
            BaseCommand.font = (
                await File.read_buffer2base64(
                    BaseCommand.resources_dir / "font" / "hpsimplifiedhans-regular.ttf"
                )
                if enable_font
                else ""
            )
            BaseCommand.err_image = BaseCommand.cache.err_image

            for file in set(template_list.values()):
                BaseCommand.templates[file] = await File.read_text(
                    BaseCommand.template_dir / file
                )

            BaseCommand.is_init = True

    async def read_or_download_images(
        self, group: Literal["vndb", "touchgal"], url: str, prefix: bool = True
    ) -> bs64:
        cache_data = await self.cache.read_cache(group, url, prefix=prefix)
        if cache_data is None:
            buffer = await self.downloader.download_image(url)
            return (
                await self.cache.write_cache(group, url, buffer, prefix=prefix)
                if buffer
                else self.err_image
            )
        else:
            return cache_data

    async def build_vndb_images(
        self, response: list[VNDBVnResponse | VNDBCharacterResponse]
    ) -> list[bs64]:
        co_str = [
            self.read_or_download_images("vndb", i.image.url)
            if i.image
            else asyncio.sleep(0, result=self.err_image)
            for i in response
        ]
        return await asyncio.gather(*co_str)

    async def build_images(
        self,
        urls: list[str],
        cache_group: Literal["vndb", "touchgal"],
        prefix: bool = True,
    ) -> list[bs64]:
        co_str = [
            self.read_or_download_images(cache_group, i, prefix=prefix) for i in urls
        ]
        return await asyncio.gather(*co_str)

    def split_date(self, value: str, cmd_type: CommandType):
        s = []
        if "-" in value:
            s = value.split("-", 1)
        elif "/" in value:
            s = value.split("/", 1)

        if (s[0].strip().isdigit() and 0 < int(s[0]) < 13) and (
            s[1].strip().isdigit() and 0 < int(s[1]) < 32
        ):
            return s[0], s[1]

        raise ArgsOrNullException(cmd_type, value)

    def build_vn(self, response: VNDBVnResponse) -> list[str]:
        return (
            Splicer.from_vndb_vn()
            .vndb_id(response.id)
            .average(response.average)
            .rating(response.rating)
            .release(response.released)
            .length(response.length_minutes)
            .platform(response.platforms)
            .alias(response.aliases)
            .producer(response.developers)
            .titles(response.titles)
        ).do()

    def build_character(
        self,
        response: VNDBCharacterResponse,
        ignore_name=False,
        ignore_extra=False,
        ignore_vns=False,
    ) -> list[str]:
        base = (
            Splicer.from_vndb_character()
            .vndb_id(response.id)
            .alias(response.aliases)
            .birthday(response.birthday)
        )
        if not ignore_vns:
            base = base.vns(response.vns)
        if not ignore_name:
            base.name(response.original, response.name)

        option: list[str] = self.character_options
        if option and not ignore_extra:
            extra = [i.split("-")[0] for i in option]
            if "a" in extra:
                base.blood(response.blood_type)
            if "b" in extra:
                base.wh(response.weight, response.height)
            if "c" in extra:
                base.gender_o(response.sex)
            if "d" in extra:
                base.gender_i(response.sex)
            if "e" in extra:
                base.bwh(response.bust, response.waist, response.hips)
            if "f" in extra:
                base.cup(response.cup)

        return base.do()

    def build_producer(
        self, response: VNDBProducerResponse, ignore_name=False
    ) -> list[str]:
        base = (
            Splicer.from_vndb_producer()
            .vndb_id(response.id)
            .alias(response.aliases)
            .text_lang(response.lang)
            .co_type(response.type)
        )
        if not ignore_name:
            base.name(response.original, response.name)
        return base.do()

    def build_search(self, response: TouchGalResponse):
        return (
            Splicer.from_touchgal_info()
            .touchgal_id(response.id)
            .touchgal_score(response.averageRating)
            .touchgal_type(response.type)
            .touchgal_tags(response.tags)
            .touchgal_platforms(response.platform)
            .touchgal_lang(response.language)
        ).do()

    def build_download(self, response: ResourceResponse) -> list[str]:
        return (
            Splicer.from_touchgal_resource()
            .resource_title(response.name)
            .resource_category(response.section)
            .resource_note(response.note)
            .resource_links(response.links)
            .touchgal_platforms(response.platform)
            .touchgal_lang(response.language)
        ).do()
