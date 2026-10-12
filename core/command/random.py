from astrbot.api import AstrBotConfig, html_renderer
from astrbot.api.event import AstrMessageEvent

from ..type.bangumi_models import BangumiSubjectResponse
from ..type.exceptions import NoResultException
from ..type.inner_models import CommandType, template_list
from ..type.vndb_models import VNDBVnResponse
from .base_command import BaseCommand


class Random(BaseCommand):
    @classmethod
    async def initialize(cls, config: AstrBotConfig):
        await super().initialize(config)

        cls.nsfw_enable = config.get("safetySetting", {}).get("enableNSFW", False)

        return cls()

    async def goooooooooo(self, event: AstrMessageEvent):
        target = None
        bangumi_info: list[BangumiSubjectResponse] = []

        while not bangumi_info:
            try:
                target = await self.vndb.request_random()
                bangumi_info = await self.bangumi.request_by_vndb_id(
                    CommandType.RANDOM, target.alttitle or target.title, target.id
                )
            except NoResultException:
                pass

        data = await self.build(target, bangumi_info[0])
        tmpl = self.templates[template_list[CommandType.RANDOM.value]]

        url = await html_renderer.render_custom_template(
            tmpl, data, True, self.render_options
        )
        yield event.image_result(url)

    async def build(self, vndb_vn: VNDBVnResponse, bangumi_vn: BangumiSubjectResponse):
        main_image = await self.read_or_download_image("vndb", vndb_vn.image.url)

        info = self.build_vn(vndb_vn)
        bangumi_info = self.build_bangumi_info(bangumi_vn, True)
        info += bangumi_info

        desc = bangumi_vn.summary.replace("\r\n", "<br>") if bangumi_vn.summary else ""

        previews = []
        if vndb_vn.screenshots:
            count = 0
            for ss in vndb_vn.screenshots:
                if ss.violence > 0.2 or ss.sexual > 0.2:
                    if self.nsfw_enable:
                        count += 1
                        previews.append(ss.url)
                else:
                    count += 1
                    previews.append(ss.url)
                if count > 3:
                    break
        return {
            "font": self.font,
            "bg": self.bg,
            "subtitle": vndb_vn.alttitle or vndb_vn.title,
            "main_image": main_image,
            "info": info,
            "desc": desc,
            "previews": previews,
        }
