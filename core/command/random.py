from astrbot.api import AstrBotConfig, html_renderer
from astrbot.api.event import AstrMessageEvent

from ..type.inner_models import CommandType, TouchGalDetails, template_list
from ..type.outer_models import TouchGalResponse
from ..utils import HTMLHandler
from .base_command import BaseCommand


class Random(BaseCommand):
    @classmethod
    async def initialize(cls, config: AstrBotConfig):
        await super().initialize(config)

        return cls()

    async def goooooooooo(self, event: AstrMessageEvent):
        unique_id = await self.touchgal.request_random()

        data = await self.build_html(unique_id)
        tmpl = self.templates[template_list[CommandType.RANDOM.value]]

        url = await html_renderer.render_custom_template(
            tmpl, data, True, self.render_options
        )
        yield event.image_result(url)

    async def build_html(
        self,
        unique_id: str,
        cmd_type: CommandType = CommandType.RANDOM,
        resp: TouchGalResponse = None,
    ):
        text = await self.touchgal.request_html(unique_id)
        details = await HTMLHandler.handle_touchgal_details(text)

        if resp is None:
            res, _ = await self.touchgal.request_vn_by_search(
                cmd_type, details.title or details.third_info[1]
            )
            resp = res[0]
        return await self.build(resp, details)

    async def build(self, res: TouchGalResponse, html_details: TouchGalDetails):
        info = self.build_search(res)

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
