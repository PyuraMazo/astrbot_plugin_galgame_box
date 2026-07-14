import asyncio
from datetime import datetime

from astrbot.api import AstrBotConfig, html_renderer

from ..services import Services
from ..type.exceptions import NoResultException
from ..type.inner_models import CommandType, template_list
from ..type.outer_models import TouchGalResponse, VNDBCharacterResponse, VNDBVnResponse
from ..utils import HTMLHandler
from . import Random
from .base_command import BaseCommand


class EventTimed(BaseCommand):
    @classmethod
    async def initialize(cls, config: AstrBotConfig):
        await super().initialize(config)
        cls.random = Services.get(Random)

        return cls()

    async def goooooooooo(self):
        now = datetime.now().strftime("%Y-%m-%d")
        date = now.split("-")

        vn = await self.vndb.request_by_event_vn(date)
        cha = await self.vndb.request_by_event_cha(date)

        vn_data, cha_data = await asyncio.gather(
            self.build(vn, for_vn=True), self.build(cha)
        )
        tmpl = self.templates[template_list[CommandType.EVENT_TIMED.value]]

        vn_url = await html_renderer.render_custom_template(
            tmpl, vn_data, True, self.render_options
        )
        cha_url = await html_renderer.render_custom_template(
            tmpl, cha_data, True, self.render_options
        )
        yield vn_url
        yield cha_url

    async def build(
        self,
        response: tuple[VNDBVnResponse, list[VNDBCharacterResponse]]
        | tuple[VNDBCharacterResponse, list[VNDBVnResponse]],
        for_vn: bool = False,
    ):
        if for_vn:
            response: tuple[VNDBVnResponse, list[VNDBCharacterResponse]]
            vn, cha_list = response
            try:
                searched_vn, _ = await self.touchgal.request_vn_by_search(
                    CommandType.EVENT_TIMED, vn.id
                )
                first_vn = searched_vn[0]
            except NoResultException:
                first_vn = None

            return await self._build_event_vn(vn, cha_list, first_vn)
        else:
            response: tuple[VNDBCharacterResponse, list[VNDBVnResponse]]
            cha, vn_list = response
            return await self._build_event_cha(cha, vn_list)

    async def _build_event_vn(
        self,
        vn: VNDBVnResponse,
        chas: list[VNDBCharacterResponse],
        touchgal_vn: TouchGalResponse | None,
    ):
        if touchgal_vn:
            text = await self.touchgal.request_html(touchgal_vn.uniqueId)
            desc = (await HTMLHandler.handle_touchgal_details(text)).description
        else:
            desc = "TouchGal暂无该作品简介。"

        characters = [
            {
                "image": img,
                "subtitle": cha.original or cha.name,
                "desc": self.build_character(cha),
            }
            for cha, img in zip(chas, await self.build_vndb_images(chas))
        ]

        main_image = (
            (await self.build_images([vn.image.url], "vndb"))[0]
            if vn.image
            else self.err_image
        )

        return {
            "font": self.font,
            "bg": self.bg,
            "subtitle": vn.alttitle or vn.title,
            "main_image": main_image,
            "info": self.build_vn(vn),
            "desc": desc,
            "cards_title": "登场角色",
            "cards": characters,
        }

    async def _build_event_cha(
        self, cha: VNDBCharacterResponse, vns: list[VNDBVnResponse]
    ):
        vns = [
            {
                "image": img,
                "subtitle": vn.alttitle or vn.title,
                "desc": self.build_vn(vn),
            }
            for vn, img in zip(vns, await self.build_vndb_images(vns))
        ]

        main_image = (
            (await self.build_images([cha.image.url], "vndb"))[0]
            if cha.image
            else self.err_image
        )

        return {
            "font": self.font,
            "bg": self.bg,
            "subtitle": cha.original or cha.name,
            "main_image": main_image,
            "info": self.build_character(cha, ignore_vns=True),
            "cards_title": "登场作品",
            "cards": vns,
        }
