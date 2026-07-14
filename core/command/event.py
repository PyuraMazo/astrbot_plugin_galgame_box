import asyncio
from datetime import datetime

from astrbot.api import AstrBotConfig, html_renderer
from astrbot.api.event import AstrMessageEvent

from ..type.inner_models import CommandType, ja_weeks, template_list
from ..type.outer_models import VNDBCharacterResponse, VNDBVnResponse
from .base_command import BaseCommand


class Event(BaseCommand):
    @classmethod
    async def initialize(cls, config: AstrBotConfig):
        await super().initialize(config)

        return cls()

    async def goooooooooo(self, event: AstrMessageEvent, value: str):
        now = datetime.now().strftime("%Y-%m-%d")
        date = now.split("-")

        if value:
            date[1], date[2] = self.split_date(value, CommandType.EVENT)

        vns, characters = await self.vndb.request_by_event(date)
        data = await self.build(date, vns, characters)
        tmpl = self.templates[template_list[CommandType.EVENT.value]]

        url = await html_renderer.render_custom_template(
            tmpl, data, True, self.render_options
        )
        yield event.image_result(url)

    async def build(
        self,
        date_list: list[str],
        vn_response: list[VNDBVnResponse],
        cha_response: list[VNDBCharacterResponse],
    ):

        co_vn_images = self.build_vndb_images(vn_response)
        co_cha_images = self.build_vndb_images(cha_response)
        vn_images, cha_images = await asyncio.gather(co_vn_images, co_cha_images)
        vns = [
            {
                "image": img,
                "subtitle": vn.alttitle or vn.title,
                "desc": self.build_vn(vn),
            }
            for vn, img in zip(vn_response, vn_images)
        ]
        chas = [
            {
                "image": img,
                "subtitle": cha.original or cha.name,
                "desc": self.build_character(cha),
            }
            for cha, img in zip(cha_response, cha_images)
        ]
        vns_block = {
            "column_info": ["今天是这些作品的发布纪念日"] if vns else [],
            "cards": vns,
        }
        chas_block = {
            "column_info": ["今天是这些角色的生日"] if chas else [],
            "cards": chas,
        }

        week = ja_weeks[
            datetime.weekday(datetime.strptime("-".join(date_list), "%Y-%m-%d"))
        ]
        return {
            "font": self.font,
            "bg": self.bg,
            "title": f"今天是{date_list[0]}年{date_list[1]}月{date_list[2]}日    {week}曜日",
            "blocks": [vns_block, chas_block],
        }
