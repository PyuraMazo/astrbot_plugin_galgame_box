from astrbot.api import AstrBotConfig, html_renderer
from astrbot.api.event import AstrMessageEvent

from ..type.inner_models import CommandType, template_list
from ..type.outer_models import VNDBProducerResponse, VNDBVnResponse
from .base_command import BaseCommand


class Producer(BaseCommand):
    @classmethod
    async def initialize(cls, config: AstrBotConfig):
        await super().initialize(config)

        return cls()

    async def goooooooooo(self, event: AstrMessageEvent, value: str):
        pro, vns = await self.vndb.request_by_producer(value)
        data = await self.build(pro, vns)
        tmpl = self.templates[template_list[CommandType.PRODUCER.value]]

        url = await html_renderer.render_custom_template(
            tmpl, data, True, self.render_options
        )
        yield event.image_result(url)

    async def build(
        self, res: list[VNDBProducerResponse], res2: list[list[VNDBVnResponse]]
    ):
        blocks = []
        for producer, per_vns in zip(res, res2):
            cards = [
                {
                    "image": vn_image,
                    "desc": self.build_vn(vn),
                    "subtitle": vn.alttitle or vn.title,
                }
                for vn, vn_image in zip(per_vns, await self.build_vndb_images(per_vns))
            ]

            blocks.append(
                {"column_info": self.build_producer(producer), "cards": cards}
            )
        return {"font": self.font, "bg": self.bg, "blocks": blocks}
