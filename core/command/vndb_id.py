from astrbot.api import AstrBotConfig, html_renderer
from astrbot.api.event import AstrMessageEvent

from ..services import Services
from ..type.exceptions import ArgsOrNullException, NoResultException
from ..type.inner_models import CommandType, id2command, template_list
from ..type.outer_models import (
    VNDBCharacterResponse,
    VNDBProducerResponse,
    VNDBVnResponse,
)
from ..utils import HTMLHandler
from . import Character, Producer, Vn
from .base_command import BaseCommand


class VndbId(BaseCommand):
    @classmethod
    async def initialize(cls, config: AstrBotConfig):
        await super().initialize(config)
        cls.vn = Services.get(Vn)
        cls.character = Services.get(Character)
        cls.producer = Services.get(Producer)

        return cls()

    async def goooooooooo(self, event: AstrMessageEvent, value: str):
        if value[0] not in id2command:
            raise ArgsOrNullException(CommandType.ID, value)

        real_type = id2command[value[0]]
        res = await self.vndb.request_by_id(real_type, value)
        desc = ""
        if real_type == CommandType.VN:
            try:
                search_info, _ = await self.touchgal.request_vn_by_search(
                    CommandType.ID, value
                )
                html_text = await self.touchgal.request_html(search_info[0].uniqueId)
                desc = (
                    await HTMLHandler.handle_touchgal_details(html_text)
                ).description
            except NoResultException:
                pass

        data = await self.build(real_type, res, desc)
        tmpl = self.templates[
            template_list[real_type.value if not desc else CommandType.RANDOM.value]
        ]

        url = await html_renderer.render_custom_template(
            tmpl, data, True, self.render_options
        )
        yield event.image_result(url)

    async def build(
        self,
        t: CommandType,
        res: list[VNDBVnResponse]
        | list[VNDBCharacterResponse]
        | tuple[list[VNDBProducerResponse], list[list[VNDBVnResponse]]],
        desc="",
    ):
        if t == CommandType.VN:
            return await self.vn.build(res, desc)
        elif t == CommandType.CHARACTER:
            return await self.character.build(res)
        else:
            return await self.producer.build(*res)
