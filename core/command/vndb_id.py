from astrbot.api import AstrBotConfig, html_renderer
from astrbot.api.event import AstrMessageEvent

from ..type.exceptions import ArgsOrNullException, NoResultException
from ..type.inner_models import CommandType, id2command, template_list
from ..type.vndb_models import (
    VNDBCharacterResponse,
    VNDBProducerResponse,
    VNDBVnResponse,
)
from . import Character, Producer, Vn
from .base_command import BaseCommand


class VndbId(BaseCommand):
    @classmethod
    async def initialize(cls, config: AstrBotConfig):
        from ..services import Services

        await super().initialize(config)
        cls.vn = Services.get(Vn)
        cls.character = Services.get(Character)
        cls.producer = Services.get(Producer)

        cls.nsfw_enable = config.get("safetySetting", {}).get("enableNSFW", False)

        return cls()

    async def goooooooooo(self, event: AstrMessageEvent, value: str):
        if value[0] not in id2command:
            raise ArgsOrNullException(CommandType.ID, value)

        real_type = id2command[value[0]]
        res = await self.vndb.request_by_id(real_type, value)
        desc = ""
        previews = []
        if real_type == CommandType.VN:
            try:
                vn: VNDBVnResponse = res[0]
                bangumi_res = (
                    await self.bangumi.request_by_vndb_id(
                        CommandType.ID, vn.alttitle or vn.title, value
                    )
                )[0]

                if bangumi_res.summary:
                    desc = bangumi_res.summary.replace("\r\n", "<br>")
                elif vn.description:
                    desc = vn.description.replace("\n", "<br>")

                if vn.screenshots:
                    count = 0
                    for ss in vn.screenshots:
                        if ss.violence > 0.2 or ss.sexual > 0.2:
                            if self.nsfw_enable:
                                count += 1
                                previews.append(ss.url)
                        else:
                            count += 1
                            previews.append(ss.url)
                        if count > 3:
                            break

            except NoResultException:
                pass

        data = await self.build(real_type, res, desc, previews)
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
        desc: str,
        previews: list[str],
    ):
        if t == CommandType.VN:
            return await self.vn.build(res, desc=desc, previews=previews)
        elif t == CommandType.CHARACTER:
            return await self.character.build(res)
        else:
            return await self.producer.build(*res)
