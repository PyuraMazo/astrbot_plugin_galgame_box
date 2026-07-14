from astrbot.api import AstrBotConfig, html_renderer
from astrbot.api.event import AstrMessageEvent

from ..type.inner_models import CommandType, template_list
from ..type.outer_models import VNDBCharacterResponse
from .base_command import BaseCommand


class Character(BaseCommand):
    @classmethod
    async def initialize(cls, config: AstrBotConfig):
        await super().initialize(config)

        return cls()

    async def goooooooooo(self, event: AstrMessageEvent, value: str):
        res = await self.vndb.request_by_character(value)
        data = await self.build(res)
        tmpl = self.templates[template_list[CommandType.CHARACTER.value]]

        url = await html_renderer.render_custom_template(
            tmpl, data, True, self.render_options
        )
        yield event.image_result(url)

    async def build(self, res: list[VNDBCharacterResponse]):
        cards = [
            {
                "image": img,
                "desc": self.build_character(info),
                "subtitle": info.original or info.name,
            }
            for img, info in zip(await self.build_vndb_images(res), res)
        ]
        return {"font": self.font, "bg": self.bg, "cards": cards}
