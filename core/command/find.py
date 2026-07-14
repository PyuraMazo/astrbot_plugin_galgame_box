import asyncio
from io import BytesIO

from openpyxl.drawing.image import PILImage

from astrbot.api import AstrBotConfig, html_renderer
from astrbot.api import message_components as comp
from astrbot.api.event import AstrMessageEvent
from astrbot.core.utils.session_waiter import (
    SessionController,
    session_waiter,
)

from ..type.exceptions import NoResultException, SessionTimeoutException
from ..type.inner_models import CommandType, bs64, template_list
from ..type.outer_models import (
    AnimeTraceData,
    AnimeTraceResponse,
    VNDBCharacterResponse,
)
from ..utils import File, Image, OnlySenderFilter
from .base_command import BaseCommand


class Find(BaseCommand):
    @classmethod
    async def initialize(cls, config: AstrBotConfig):
        await super().initialize(config)
        cls.find_results = config.get("findSetting", {}).get("findResults", 3)

        cls.session_dict: dict[str, bs64] = {}

        return cls()

    async def goooooooooo(self, event: AstrMessageEvent, url: str):
        if not url:
            # 从引用中获取
            for i in event.message_obj.message:
                if isinstance(i, comp.Reply):
                    url = await self._get_chain_image(i.chain)
                    break

        if not url:
            tips = f"-未检测到有效的指令参数\n-改为从下一条消息中获取\n-请在{self.session_timeout}s内发送一张图片"
            yield event.plain_result(tips)

            @session_waiter(timeout=self.session_timeout)
            async def image_waiter(
                controller: SessionController, sess_event: AstrMessageEvent
            ):
                message = sess_event.message_obj.message
                bs = await self._get_chain_image(message)

                if not bs:
                    invalid = "未解析到图片，请重新发送"
                    await sess_event.send(sess_event.plain_result(invalid))
                else:
                    self.session_dict[
                        sess_event.get_group_id() + sess_event.get_sender_id()
                    ] = bs
                    controller.stop()

            try:
                await image_waiter(event, session_filter=OnlySenderFilter())
                url = self.session_dict.pop(
                    event.get_group_id() + event.get_sender_id()
                )
            except TimeoutError:
                raise SessionTimeoutException(CommandType.FIND, "")

        trace_resp = await self.animetrace.request_find(url)

        if not trace_resp.data:
            raise NoResultException(CommandType.FIND, "")

        vndb_resp: list[list[VNDBCharacterResponse]] = []
        for i in trace_resp.data:
            chas_per_match = [
                self.vndb.request_by_find(j.character, j.work)
                for idx, j in enumerate(i.character)
                if idx < self.find_results
            ]
            vndb_resp.append(await asyncio.gather(*chas_per_match))

        data = await self.build(url, trace_resp, vndb_resp)
        tmpl = self.templates[template_list[CommandType.FIND.value]]

        res_url = await html_renderer.render_custom_template(
            tmpl, data, True, self.render_options
        )
        yield event.image_result(res_url)

    async def build(
        self,
        url: str,
        trace_resp: AnimeTraceResponse,
        vndb_resp: list[list[VNDBCharacterResponse]],
    ):
        if url.startswith("http"):
            buffer = await self.downloader.download_image(url)
            v_buffer = await Image.image2jpg_async(buffer)
        else:
            v_buffer = File.base64_to_buffer(url)
        blocks = [
            self._build_find(data, chas, v_buffer)
            for data, chas in zip(trace_resp.data, vndb_resp)
        ]
        title = [
            f"识别模型「{self.animetrace.current_model}」",
            f"匹配数「{len(blocks)}」个",
            f"AI图「{'是' if trace_resp.ai else '否'}」",
        ]
        return {
            "font": self.font,
            "bg": self.bg,
            "blocks": await asyncio.gather(*blocks),
            "title": {
                "image": await File.buffer2base64(v_buffer)
                if v_buffer
                else self.err_image,
                "text": title,
            },
        }

    async def _build_find(
        self,
        response: AnimeTraceData,
        character_response: list[VNDBCharacterResponse],
        buffer: bytes,
    ):
        image = PILImage.open(BytesIO(buffer))
        width, height = image.size
        left = int(width * response.box[0])
        top = int(height * response.box[1])
        right = int(width * response.box[2])
        bottom = int(height * response.box[3])
        area = await asyncio.to_thread(image.crop, (left, top, right, bottom))

        output = BytesIO()
        area.save(output, format="JPEG")

        cha_list = []
        for list_or_empty, err_if in zip(character_response, response.character):
            if list_or_empty:
                character: VNDBCharacterResponse = list_or_empty[0]
                text = self.build_character(
                    character, ignore_name=True, ignore_extra=True
                )
                img = (
                    (await self.build_images([character.image.url], "vndb"))[0]
                    if character.image
                    else self.err_image
                )
                cha_list.append(
                    {
                        "image": img,
                        "subtitle": character.original or character.name,
                        "desc": text,
                    }
                )
            else:
                cha_list.append(
                    {
                        "image": self.err_image,
                        "subtitle": err_if.character,
                        "desc": [
                            f"出场作品：{err_if.work}",
                            "VNDB暂无记录，角色可能并非来自Gal",
                        ],
                    }
                )
        buf = output.getvalue()
        column = {
            "image": await File.buffer2base64(buf) if buf else self.err_image,
            "text": [
                "检测区域如左图",
                f"可信度：{'不' if response.not_confident else ''}可信",
            ],
        }
        return {
            "column_info": column,
            "cards": cha_list,
        }

    async def _get_chain_image(self, chain: list[comp.BaseMessageComponent]) -> bs64:
        for part in chain:
            if isinstance(part, comp.Image):
                return await part.convert_to_base64()
        return ""
