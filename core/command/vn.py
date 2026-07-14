from astrbot.api import AstrBotConfig, html_renderer
from astrbot.api.event import AstrMessageEvent

from ..type.inner_models import CommandType, template_list
from ..type.outer_models import VNDBVnResponse
from .base_command import BaseCommand


class Vn(BaseCommand):
    @classmethod
    async def initialize(cls, config: AstrBotConfig):
        await super().initialize(config)

        return cls()

    async def goooooooooo(self, event: AstrMessageEvent, value: str):
        res = await self.vndb.request_by_vn(value)
        data = await self.build(res)
        tmpl = self.templates[template_list[CommandType.VN.value]]

        url = await html_renderer.render_custom_template(
            tmpl, data, True, self.render_options
        )
        yield event.image_result(url)

    async def build(self, res: list[VNDBVnResponse], desc: str = ""):
        cards = [
            {"image": img, "desc": self.build_vn(info)}
            for img, info in zip(await self.build_vndb_images(res), res)
        ]
        if desc:
            vndb = res[0]
            card = cards[0]
            return {
                "font": self.font,
                "bg": self.bg,
                "main_image": card["image"],
                "subtitle": vndb.alttitle or vndb.title,
                "info": card["desc"],
                "desc": desc,
            }
        else:
            return {"font": self.font, "bg": self.bg, "cards": cards}
