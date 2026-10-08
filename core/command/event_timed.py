from datetime import datetime

from astrbot.api import AstrBotConfig, html_renderer

from ..type.bangumi_models import BangumiSubjectResponse
from ..type.exceptions import NoResultException
from ..type.inner_models import CommandType, template_list
from ..type.vndb_models import VNDBCharacterResponse, VNDBVnResponse
from .base_command import BaseCommand
from .random import Random


class EventTimed(BaseCommand):
    @classmethod
    async def initialize(cls, config: AstrBotConfig):
        from ..services import Services

        await super().initialize(config)
        cls.random = Services.get(Random)

        return cls()

    async def goooooooooo(self):
        now = datetime.now().strftime("%Y-%m-%d")
        date = now.split("-")
        tmpl = self.templates[template_list[CommandType.EVENT_TIMED.value]]

        try:
            vn = await self.vndb.request_by_event_vn(date)
            vn_data = await self.build(vn, for_vn=True)
            vn_url = await html_renderer.render_custom_template(
                tmpl, vn_data, True, self.render_options
            )
            res1 = vn_url
        except Exception as e:
            res1 = e

        try:
            cha = await self.vndb.request_by_event_cha(date)
            cha_data = await self.build(cha)
            cha_url = await html_renderer.render_custom_template(
                tmpl, cha_data, True, self.render_options
            )
            res2 = cha_url
        except Exception as e:
            res2 = e
        yield res1, res2

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
                searched_vn, _ = await self.bangumi.request_by_vndb_id(
                    CommandType.EVENT_TIMED, vn.alttitle or vn.title, vn.id
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
        bangumi_vn: BangumiSubjectResponse | None,
    ):
        if bangumi_vn and bangumi_vn.summary:
            desc = bangumi_vn.summary.replace("\r\n", "<br>")
        elif vn.description:
            desc = vn.description.replace("\n", "<br>")
        else:
            desc = "暂无该作品简介  =。="

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
