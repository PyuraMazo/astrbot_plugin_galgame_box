from astrbot.api import AstrBotConfig, html_renderer
from astrbot.api.event import AstrMessageEvent

from ..type.bangumi_models import BangumiSubjectResponse
from ..type.exceptions import NoResultException
from ..type.inner_models import CommandType, TouchGalDetails, template_list
from ..type.touchgal_models import TouchGalWorkResponse
from ..type.vndb_models import VNDBVnResponse
from ..utils import HTMLHandler
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

        data = await self.build_(target, bangumi_info[0])
        tmpl = self.templates[template_list[CommandType.RANDOM.value]]

        url = await html_renderer.render_custom_template(
            tmpl, data, True, self.render_options
        )
        yield event.image_result(url)

    async def build_html(
        self,
        unique_id: str,
        cmd_type: CommandType = CommandType.RANDOM,
        resp: TouchGalWorkResponse = None,
    ):
        text = await self.touchgal.request_html(unique_id)
        details = await HTMLHandler.handle_touchgal_details(text)

        if resp is None:
            res, _ = await self.touchgal.request_vn_by_search(
                cmd_type, details.title or details.third_info[1]
            )
            resp = res[0]
        return await self.build(resp, details)

    async def build(self, res: TouchGalWorkResponse, html_details: TouchGalDetails):
        info = self.build_search(res, ignore_name=True)

        third = html_details.third_info or ""
        third_id = f"{third[0]}：{third[1]}" if third else ""
        desc = html_details.description.replace("、", "<br>")
        previews = await self.build_images(html_details.previews, "touchgal")
        main_image = (
            (await self.build_images([res.banner], "touchgal"))[0]
            if res.banner
            else self.err_image
        )
        info.insert(0, third_id)
        return {
            "font": self.font,
            "bg": self.bg,
            "subtitle": res.name,
            "main_image": main_image,
            "info": info,
            "desc": desc,
            "previews": previews,
        }

    async def build_(self, vndb_vn: VNDBVnResponse, bangumi_vn: BangumiSubjectResponse):
        main_image = (await self.build_images([vndb_vn.image.url], "vndb"))[0]

        info = self.build_vn(vndb_vn)
        info.insert(0, "--- VNDB ---")
        third_info = self.build_bangumi_info(bangumi_vn)
        if third_info:
            third_info.insert(0, "--- Bangumi ---")
        info += third_info

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
