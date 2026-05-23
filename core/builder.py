import asyncio
import math
from collections.abc import Callable
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image as PILImage

from astrbot.api import AstrBotConfig

from .api.const import id2command
from .api.model import (
    AnimeTraceData,
    AnimeTraceResponse,
    ResourceResponse,
    SteamProfileResponse,
    TouchGalResponse,
    VNDBCharacterResponse,
    VNDBProducerResponse,
    VNDBVnResponse,
)
from .api.type import (
    AnimeTraceModel,
    ColumnStyle,
    CommandBody,
    CommandType,
    RenderedBlock,
    RenderedItem,
    RenderedPuzzle,
    RenderedRandom,
    SteamVnsInfo,
    TouchGalDetails,
    UnrenderedData,
)
from .internet.downloader import Downloader, get_downloader
from .utils.file import File
from .utils.image import Image
from .utils.splicer import Splicer


class Builder:
    def __init__(self):
        self.resources_dir = Path(__file__).parent / ".." / "resources"
        self.bg_path = self.resources_dir / "image" / "pixiv139681518.jpg"
        self.err_path = self.resources_dir / "image" / "error.jpg"
        self.font_path = self.resources_dir / "font" / "hpsimplifiedhans-regular.ttf"
        self._handlers: dict[CommandType, Callable] = {
            CommandType.VN: self._handle_vn,
            CommandType.CHARACTER: self._handle_character,
            CommandType.PRODUCER: self._handle_producer,
            CommandType.EVENT: self._handle_event,
            CommandType.RANDOM: self._handle_random,
            CommandType.DOWNLOAD: self._handle_download,
            CommandType.SELECT: self._handle_select,
            CommandType.FIND: self._handle_find,
            CommandType.RECOMMEND: self._handle_random,
            CommandType.PUZZLE: self._handle_puzzle,
            CommandType.GAL_EVENT: self._handle_gal_event,
        }

        self.downloader: Downloader | None = None
        self.bg: str | None = None
        self.err: str | None = None
        self.font: str | None = None
        self.character_options: list[str] | None = None
        self.finish_consuming: int | None = None

    async def initialize(self, config: AstrBotConfig):
        self.downloader = get_downloader()
        search_setting = config.get("searchSetting", {})
        self.character_options = search_setting.get("characterOptions", [])
        self.finish_consuming = search_setting.get("finishConsuming", 20)
        enable_font = config.get("returnSetting", {}).get("enableFont", True)

        await self.downloader.initialize(config)
        self.bg = await File.read_buffer2base64(str(self.bg_path))
        self.err = await File.read_buffer2base64(str(self.err_path))
        self.font = (
            await File.read_buffer2base64(str(self.font_path)) if enable_font else ""
        )

    async def terminate(self):
        await self.downloader.terminate()

    async def build_options(
        self, command_body: CommandBody, response, **kwargs
    ) -> UnrenderedData | list[tuple[str, str]]:
        await self._init_resources()
        count = kwargs.get("count", 0) or len(response)
        title = self._build_title(command_body, count)

        handler_type = self._determine_handler_type(command_body)
        handler = self._handlers[handler_type]

        result = await handler(response, title=title, **kwargs)
        return result

    def _determine_handler_type(self, command_body: CommandBody) -> CommandType:
        run_type = command_body.type
        if run_type == CommandType.ID:
            for cmd_type in CommandType:
                if id2command.get(command_body.value[0], "") == cmd_type.value:
                    return cmd_type
        return run_type

    async def _init_resources(self):
        if self.bg is None:
            self.bg = await File.read_buffer2base64(str(self.bg_path))
        if self.font is None:
            self.font = await File.read_buffer2base64(str(self.font_path))
        if self.err is None:
            self.err = await File.read_buffer2base64(str(self.err_path))

    async def _handle_vn(self, response, **kwargs):
        resp: list[VNDBVnResponse] = response
        items = [
            RenderedItem(
                image=img, text="<br>".join(self._build_vn(info)), sub_title=""
            )
            for img, info in zip(await self._build_images(resp), resp)
        ]
        print(self.font)
        return UnrenderedData(
            title="<br>".join(kwargs.get("title", "标题出错")),
            items=items,
            bg_image=self.bg,
            font=self.font,
        )

    async def _handle_character(self, response, **kwargs):
        resp: list[VNDBCharacterResponse] = response
        items = [
            RenderedItem(
                image=img,
                text="<br>".join(self._build_character(info, ignore_name=True)),
                sub_title=info.original or info.name,
            )
            for img, info in zip(await self._build_images(resp), resp)
        ]
        return UnrenderedData(
            title="<br>".join(kwargs.get("title", "标题出错")),
            items=items,
            bg_image=self.bg,
            font=self.font,
        )

    async def _handle_producer(self, response, **kwargs):
        resp: list[VNDBProducerResponse] = response
        vns: list[list[VNDBVnResponse]] = kwargs["vns"]

        works: list[RenderedBlock] = []
        for producer, per_vns in zip(resp, vns):
            items: list[RenderedItem] = []
            for vn, vn_image in zip(per_vns, await self._build_images(per_vns)):
                items.append(
                    RenderedItem(
                        image=vn_image,
                        text="<br>".join(self._build_vn(vn)),
                        sub_title=vn.alttitle or vn.title,
                    )
                )
            works.append(
                RenderedBlock(
                    column_info="<br>".join(
                        self._build_producer(producer, ignore_name=True)
                    ),
                    vns=items,
                )
            )

        return UnrenderedData(
            title="<br>".join(kwargs.get("title", "标题出错")),
            items=works,
            bg_image=self.bg,
            font=self.font,
        )

    async def _handle_event(self, response, **kwargs):
        vn: list[VNDBVnResponse] = response
        cha: list[VNDBCharacterResponse] = kwargs["cha"]
        res = await self._build_event(vn, cha)
        return UnrenderedData(
            title="<br>".join(kwargs.get("title", "标题出错")),
            items=res,
            bg_image=self.bg,
            font=self.font,
        )

    async def _handle_gal_event(self, response, **kwargs):
        for_vn: bool = kwargs.get("for_vn", False)
        res: UnrenderedData
        if for_vn:
            resp: tuple[VNDBVnResponse, list[VNDBCharacterResponse]] = response
            res = await self._build_event_vn(resp[0], resp[1])
        else:
            resp: tuple[VNDBCharacterResponse, list[VNDBVnResponse]] = response
            res = await self._build_event_cha(resp[0], resp[1])
        return res

    async def _handle_random(self, response, **kwargs):
        resp: list[TouchGalResponse] = response
        details: list[TouchGalDetails] = kwargs["details"]

        # res = await self._build_select(resp[0], details) if resp else {}
        co = [self._build_select(i, j) for i, j in zip(resp, details)]
        return UnrenderedData(
            title="<br>".join(kwargs.get("title", "标题出错")),
            items=await asyncio.gather(*co),
            bg_image=self.bg,
            font=self.font,
        )

    async def _handle_download(self, response, **kwargs):
        resp: list[ResourceResponse] = response
        return [("", "\n".join(self._build_download(i))) for i in resp]

    async def _handle_select(self, response, **kwargs):
        resp: list[TouchGalResponse] = response
        co = [self._build_select(i) for i in resp]
        return await asyncio.gather(*co)

    async def _handle_find(self, response, **kwargs):
        trace_resp: AnimeTraceResponse = response
        vndb_resp = kwargs["vndb_resp"]

        _buffer = await self.downloader.download_once(kwargs["image"])
        # 转换为合法jpg
        buffer = await Image.image2jpg_async(_buffer)
        blocks = [
            self._build_find(data, chas, buffer)
            for data, chas in zip(trace_resp.data, vndb_resp)
        ]
        title = kwargs.get("title", [])
        title.append(
            f"检测模型「{'GAL专用' if kwargs['model'] == AnimeTraceModel.Profession else 'GAL+动画'}」"
        )
        title.append(f"是否AI图「{'是' if response.ai else '否'}」")
        return UnrenderedData(
            title="<br>".join(title) if len(title) > 1 else "标题出错",
            items=await asyncio.gather(*blocks),
            bg_image=self.bg,
            font=self.font,
            main_image=await File.buffer2base64(buffer) if buffer else self.err,
        )

    async def _handle_puzzle(self, response, **kwargs):
        vns: dict[int, SteamVnsInfo] = kwargs["vns"]
        sorted_list = sorted(vns.values(), key=lambda j: j.play_time, reverse=True)
        co = [self._build_puzzle(info) for info in sorted_list]
        _items: list[RenderedPuzzle] = await asyncio.gather(*co)
        buffer = await self.downloader.download_more([url.img for url in _items])
        bs = [File.buffer2base64(buf) for buf in buffer]
        for item, img in zip(_items, await asyncio.gather(*bs)):
            item.img = img

        profile: SteamProfileResponse = response[0]
        nick = f"用户「{profile.personaname}」"
        update = f"更新时间「{kwargs['update']}」"
        _all = 0
        for i in vns:
            _all += vns[i].play_time
        all_play = f"Galgame总游玩时间「{round(_all / 60, 1)}」小时"
        title = kwargs.get("title", [])
        title.append(update)
        title.append(nick)
        title.append(all_play)
        return UnrenderedData(
            title="<br>".join(title), items=_items, bg_image=self.bg, font=self.font
        )

    def _build_title(self, command_body: CommandBody, count: int) -> list[str]:
        run_type = f"指令「{command_body.type.value}」"
        value = (
            (
                f"参数「{command_body.value if not command_body.value.startswith('http') else '网络链接'}」"
                if command_body.value and command_body.type != CommandType.PUZZLE
                else ""
            )
            if isinstance(command_body.value, str)
            else "-".join(command_body.value)
        )
        count = (
            f"结果「{count}」条"
            if command_body.type
            not in [
                CommandType.RANDOM,
                CommandType.RECOMMEND,
                CommandType.PUZZLE,
                CommandType.EVENT,
            ]
            else ""
        )
        return [i for i in [run_type, value, count] if i]

    async def _build_images(
        self, response: list[VNDBVnResponse | VNDBCharacterResponse]
    ) -> list[str]:
        co_str = [
            File.buffer2base64(await self.downloader.download_once(i.image.url))
            if i.image
            else asyncio.sleep(0, result=self.err)
            for i in response
        ]
        return await asyncio.gather(*co_str)

    def _build_vn(self, response: VNDBVnResponse) -> list[str]:
        return (
            Splicer.from_vndb_vn()
            .vndb_id(response.id)
            .average(response.average)
            .rating(response.rating)
            .release(response.released)
            .length(response.length_minutes)
            .platform(response.platforms)
            .alias(response.aliases)
            .producer(response.developers)
            .titles(response.titles)
        ).do()

    def _build_character(
        self, response: VNDBCharacterResponse, ignore_name=False, ignore_extra=False
    ) -> list[str]:
        base = (
            Splicer.from_vndb_character()
            .vndb_id(response.id)
            .alias(response.aliases)
            .birthday(response.birthday)
            .vns(response.vns)
        )
        if not ignore_name:
            base.name(response.original, response.name)

        option: list[str] = self.character_options
        if option and not ignore_extra:
            extra = [i.split("-")[0] for i in option]
            if "a" in extra:
                base.blood(response.blood_type)
            if "b" in extra:
                base.wh(response.weight, response.height)
            if "c" in extra:
                base.gender_o(response.sex)
            if "d" in extra:
                base.gender_i(response.sex)
            if "e" in extra:
                base.bwh(response.bust, response.waist, response.hips)
            if "f" in extra:
                base.cup(response.cup)

        return base.do()

    def _build_producer(
        self, response: VNDBProducerResponse, ignore_name=False
    ) -> list[str]:
        base = (
            Splicer.from_vndb_producer()
            .vndb_id(response.id)
            .alias(response.aliases)
            .text_lang(response.lang)
            .co_type(response.type)
        )
        if not ignore_name:
            base.name(response.original, response.name)
        return base.do()

    async def _build_event(
        self,
        vn_response: list[VNDBVnResponse],
        cha_response: list[VNDBCharacterResponse],
    ) -> list[RenderedBlock]:

        co_vn_images = self._build_images(vn_response)
        co_cha_images = self._build_images(cha_response)
        vn_images, cha_images = await asyncio.gather(co_vn_images, co_cha_images)

        vns = [
            RenderedItem(
                image=img,
                text="<br>".join(self._build_vn(vn)),
                sub_title=vn.alttitle or vn.title,
            )
            for vn, img in zip(vn_response, vn_images)
        ]
        chas = [
            RenderedItem(
                image=img,
                text="<br>".join(self._build_character(cha)),
                sub_title=cha.original or cha.name,
            )
            for cha, img in zip(cha_response, cha_images)
        ]

        return [
            RenderedBlock(
                column_info="今天是这些作品的发布纪念日",
                vns=vns,
            ),
            RenderedBlock(
                column_info="今天是这些角色的生日",
                vns=chas,
            ),
        ]

    async def _build_event_vn(
        self, vn: VNDBVnResponse, chas: list[VNDBCharacterResponse]
    ) -> UnrenderedData:

        items: list[RenderedItem] = [
            RenderedItem(
                sub_title=cha.original or cha.name,
                image=img,
                text="<br>".join(self._build_character(cha)),
            )
            for cha, img in zip(chas, await self._build_images(chas))
        ]

        character = RenderedBlock(column_info="主要角色", vns=items)
        main_image = await File.buffer2base64(
            await self.downloader.download_once(vn.image.url) if vn.image else self.err
        )

        return UnrenderedData(
            title=vn.alttitle or vn.title,
            items=[character],
            bg_image=self.bg,
            font=self.font,
            main_image=main_image,
            main_desc="<br>".join(self._build_vn(vn)),
            extra_info="作品信息",
        )

    async def _build_event_cha(
        self, cha: VNDBCharacterResponse, vns: list[VNDBVnResponse]
    ):
        items: list[RenderedItem] = [
            RenderedItem(
                sub_title=vn.alttitle or vn.title,
                image=img,
                text="<br>".join(self._build_vn(vn)),
            )
            for vn, img in zip(vns, await self._build_images(vns))
        ]

        vn_ = RenderedBlock(column_info="登场作品", vns=items)
        main_image = await File.buffer2base64(
            await self.downloader.download_once(cha.image.url)
            if cha.image
            else self.err
        )

        return UnrenderedData(
            title=cha.original or cha.name,
            items=[vn_],
            bg_image=self.bg,
            font=self.font,
            main_image=main_image,
            main_desc="<br>".join(self._build_character(cha)),
            extra_info="角色信息",
        )

    async def _build_select(
        self, response: TouchGalResponse, details: TouchGalDetails = None
    ) -> RenderedRandom | tuple[Any, str]:
        cover = response.banner
        desc = (
            Splicer.from_touchgal_desc()
            .touchgal_id(response.id)
            .touchgal_score(response.averageRating)
            .touchgal_type(response.type)
            .touchgal_tags(response.tag)
            .touchgal_platforms(response.platform)
            .touchgal_lang(response.language)
        ).do()

        if not details:
            text = "\n".join(desc)
            file_path = self.err
            if response.banner:
                try:
                    file_path = await File.buffer2base64(
                        await Image.image2jpg_async(
                            await self.downloader.download_once(cover)
                        ),
                        False,
                    )
                except Exception:
                    file_path = self.err
            return file_path, text

        third = details.third_info or ""
        third_id = f"{third[0]}：{third[1]}" if third else ""
        description = details.description.replace("、", "<br>")
        img_buf = await self.downloader.download_more(details.images)
        co_imgs = [
            File.buffer2base64(img, suffix="avif") or self.err for img in img_buf
        ]
        imgs = await asyncio.gather(*co_imgs)
        desc.insert(0, third_id)
        return RenderedRandom(
            text="<br>".join(desc),
            sub_title=response.name,
            main_image=await File.buffer2base64(
                await self.downloader.download_once(cover), suffix="avif"
            )
            if response.banner
            else self.err,
            images=imgs,
            description=description,
        )

    def _build_download(self, response: ResourceResponse) -> list[str]:
        return (
            Splicer.from_touchgal_resource()
            .resource_title(response.name)
            .resource_category(response.section)
            .resource_note(response.note)
            .resource_links(response.links)
            .touchgal_platforms(response.platform)
            .touchgal_lang(response.language)
        ).do()

    async def _build_find(
        self, response: AnimeTraceData, character_response, buffer: bytes
    ) -> RenderedBlock:
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
        for cha, err_if in zip(character_response, response.character):
            if cha:
                character: VNDBCharacterResponse = cha[0]
                text = "<br>".join(
                    self._build_character(
                        character, ignore_name=True, ignore_extra=True
                    )
                )
                img = (
                    await File.buffer2base64(
                        await self.downloader.download_once(character.image.url)
                    )
                    if character.image
                    else self.err
                )
                cha_list.append(
                    RenderedItem(
                        image=img,
                        text=text,
                        sub_title=character.original or character.name,
                    )
                )
            else:
                cha_list.append(
                    RenderedItem(
                        sub_title=err_if.character,
                        image=self.err,
                        text=f"出场作品：{err_if.work}<br>VNDB暂无记录，角色可能并非来自Gal",
                    )
                )
        buf = output.getvalue()
        column = ColumnStyle(
            image=await File.buffer2base64(buf) if buf else self.err,
            title=f"检测区域如左图<br>可信度：{'不' if response.not_confident else ''}可信",
        )
        return RenderedBlock(
            column_info=column,
            vns=cha_list,
        )

    async def _build_puzzle(self, info: SteamVnsInfo):
        rate = (
            info.play_time / self.finish_consuming / 60
            if info.play_time < self.finish_consuming * 60
            else 1
        )
        return RenderedPuzzle(
            span=math.ceil(4 * rate), game=info.name, img=info.vndb_img
        )


_builder: Builder | None = None


def get_builder():
    global _builder
    if _builder is None:
        _builder = Builder()
    return _builder
