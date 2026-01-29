import asyncio
from typing import Any, Callable, Dict, Optional
from pathlib import Path
from PIL import Image as PILImage
from io import BytesIO

from astrbot.api import AstrBotConfig


from .internet.downloader import get_downloader, Downloader
from .api.type import CommandType, CommandBody, UnrenderedData, TouchGalDetails, AnimeTraceModel, RenderedItem, \
    ColumnStyle, RenderedBlock, RenderedRandom
from .api.model import VNDBVnResponse, VNDBCharacterResponse, VNDBProducerResponse, TouchGalResponse, ResourceResponse, \
    AnimeTraceResponse, AnimeTraceData
from .api.const import id2command, lang, develop_type, gender
from .utils.file import File
from .utils.image import Image

class Builder:
    def __init__(self):
        self.resources_dir = Path(__file__).parent/ '..' / 'resources'
        self.bg_path = self.resources_dir / 'image' / 'pixiv139681518.jpg'
        self.err_path = self.resources_dir / 'image' / 'error.jpg'
        self.font_path = self.resources_dir / 'font' / 'hpsimplifiedhans-regular.ttf'
        self._handlers: Dict[CommandType, Callable] = {
            CommandType.VN: self._handle_vn,
            CommandType.CHARACTER: self._handle_character,
            CommandType.PRODUCER: self._handle_producer,
            CommandType.RANDOM: self._handle_random,
            CommandType.DOWNLOAD: self._handle_download,
            CommandType.SELECT: self._handle_select,
            CommandType.FIND: self._handle_find,
            CommandType.RECOMMEND: self._handle_random
        }

        self.downloader: Optional[Downloader] = None
        self.bg: Optional[str] = None
        self.err: Optional[str] = None
        self.font: Optional[str] = None
        self.character_options: Optional[list[str]] = None

    async def initialize(self, config: AstrBotConfig):
        self.downloader = get_downloader()
        self.character_options = config.get('searchSetting', {}).get('characterOptions', [])

        await self.downloader.initialize(config)
        self.bg = await File.read_buffer2base64(str(self.bg_path))
        self.err = await File.read_buffer2base64(str(self.err_path))
        self.font = await File.read_buffer2base64(str(self.font_path))

    async def terminate(self):
        await self.downloader.terminate()

    async def build_options(self,
                            command_body: CommandBody,
                            response,
                            **kwargs) -> UnrenderedData | list[tuple[str, str]]:
        await self._init_resources()
        # count = kwargs['count'] if 'count' in kwargs else len(response)
        count = kwargs.get('count', 0) or len(response)
        title = self._build_title(command_body, count)

        handler_type = self._determine_handler_type(command_body)

        handler = self._handlers[handler_type]

        result = await handler(response, title=title, **kwargs)
        return result

    def _determine_handler_type(self, command_body: CommandBody) -> CommandType:
        run_type = command_body.type
        if run_type == CommandType.ID:
            for cmd_type in CommandType:
                if id2command.get(command_body.value[0], '') == cmd_type.value:
                    return cmd_type
        return run_type

    async def _init_resources(self):
        if not self.bg: self.bg = await File.read_buffer2base64(str(self.bg_path))
        if not self.font: self.font = await File.read_buffer2base64(str(self.font_path))
        if not self.err: self.err = await File.read_buffer2base64(str(self.err_path))

    async def _handle_vn(self, response, **kwargs):
        resp: list[VNDBVnResponse] = response
        co_items = [self._build_vn(res) for res in resp]
        items = await asyncio.gather(*co_items)
        return UnrenderedData(
            title='<br>'.join(kwargs.get('title', '标题出错')),
            items=items,
            bg_image=self.bg,
            font=self.font
        )

    async def _handle_character(self, response, **kwargs):
        resp: list[VNDBCharacterResponse] = response
        co_items = [self._build_character(res) for res in resp]
        items = await asyncio.gather(*co_items)
        return UnrenderedData(
            title='<br>'.join(kwargs.get('title', '标题出错')),
            items=items,
            bg_image=self.bg,
            font=self.font
        )

    async def _handle_producer(self, response, **kwargs):
        resp: list[VNDBProducerResponse] = response
        vns: list[list[VNDBVnResponse]] = kwargs['vns']
        co_pros = [self._build_producer(pro, vn) for pro, vn in zip(resp, vns)]
        pros = await asyncio.gather(*co_pros)
        return UnrenderedData(
            title='<br>'.join(kwargs.get('title', '标题出错')),
            items=pros,
            bg_image=self.bg,
            font=self.font
        )

    async def _handle_random(self, response, **kwargs):
        resp: list[TouchGalResponse] = response
        details: list[TouchGalDetails] = kwargs['details']

        # res = await self._build_select(resp[0], details) if resp else {}
        co = [self._build_select(i, j) for i, j in zip(resp, details)]
        return UnrenderedData(
            title='<br>'.join(kwargs.get('title', '标题出错')),
            items=await asyncio.gather(*co),
            bg_image=self.bg,
            font=self.font
        )

    async def _handle_download(self, response, **kwargs):
        resp: list[ResourceResponse] = response
        return [('', self._build_download(i)) for i in resp]

    async def _handle_select(self, response, **kwargs):
        resp: list[TouchGalResponse] = response
        co = [self._build_select(i) for i in resp]
        return await asyncio.gather(*co)

    async def _handle_find(self, response, **kwargs):
        trace_resp: AnimeTraceResponse = response
        vndb_resp = kwargs['vndb_resp']

        _buffer = await self.downloader.do(kwargs['image'])
        # 转换为合法jpg
        buffer = await Image.image2jpg_async(_buffer)
        blocks = [self._build_find(data, chas, buffer) for data, chas in zip(trace_resp.data, vndb_resp)]
        title = kwargs.get('title', [])
        title.append(f'检测模型「{"GAL专用" if kwargs["model"] == AnimeTraceModel.Profession else "GAL+动画"}」')
        title.append(f'是否AI图「{"是" if response.ai else "否"}」')
        return UnrenderedData(
            title='<br>'.join(title) if len(title) > 1 else '标题出错',
            items=await asyncio.gather(*blocks),
            bg_image=self.bg,
            font=self.font,
            main_image=await File.buffer2base64(buffer) if buffer else self.err
        )

    def _build_title(self, command_body: CommandBody, count: int) -> list[str]:
        run_type = f'搜索指令「{command_body.type.value}」'
        value = f'搜索词「{command_body.value if not command_body.value.startswith("http") else "网络链接"}」' if command_body.value else ''
        count = f'搜索结果「{count}条」' if command_body.type != CommandType.RANDOM else ''
        return [i for i in [run_type, value, count] if i]


    async def _build_vn(self, response: VNDBVnResponse) -> RenderedItem:
        id = f'VNDB ID：{response.id}'
        img = await File.buffer2base64(await self.downloader.do(response.image.url)) if response.image else self.err
        avg = f'平均分：{response.average}' if response.average else ''
        rating = f'贝叶斯评分：{response.rating}' if response.rating else ''
        release = f'发布日期：{response.released}' if response.released else ''
        length = f'游玩时间：{round(response.length_minutes / 60, 1)}小时' if response.length_minutes else ''

        platform = f'支持平台：{"、".join(response.platforms)}' if response.platforms else ''
        alias = f'别称：{"、".join(response.aliases)}' if response.aliases else ''

        pro = [f'{p.original or p.name}（{p.id}）' for p in response.developers] if response.developers else []
        dev = f'制作者（VNDB ID）：{"、".join(pro)}' if pro else ''

        lang_list = []
        if response.titles:
            for title in response.titles:
                if title.lang in lang.keys():
                    lang_list.append(f'{lang[title.lang]}标题（{"官方" if title.official else "非官方"}）：{title.title}')
        titles = "<br>".join(lang_list)

        data_list = [i for i in [id, titles, alias, rating, avg, length, dev, release, platform] if i]
        return RenderedItem(
            image=img,
            text="<br>".join(data_list),
            sub_title='')

    async def _build_character(self, response: VNDBCharacterResponse, ignore_extra = False) -> RenderedItem:
        id = f'VNDB ID：{response.id}'
        img = await File.buffer2base64(await self.downloader.do(response.image.url)) if response.image else self.err
        name = response.original or response.name
        aliases = f'别名：{"、".join(response.aliases)}' if response.aliases else ''
        birthday = f'生日：{response.birthday[0]}月{response.birthday[1]}日' if response.birthday else ''

        vn_list = []
        for vn in response.vns:
            vn_list.append(f'出场作品（VNDB ID）：「{vn.alttitle or vn.title}」（{vn.id}）')
        vns = "、".join(vn_list)

        option: list[str] = self.character_options
        extra: list = []
        if option and not ignore_extra:
            extra =  [i.split('-')[0] for i in option]

        blood = f'血型：{response.blood_type}' if 'a' in extra and response.blood_type else ''
        wh = f'身高/体重（cm/kg）：{response.height or "??"}/{response.weight or "??"}' \
            if 'b' in extra and (response.weight or response.height) \
            else ''
        gender_outer = f'性别：{gender[response.sex[0]]}' if 'c' in extra else ''
        gender_inner =  f'真实性别：{gender[response.sex[1]]}' if 'd' in extra else ''
        bwh = f'三围：{response.bust or "??"}-{response.waist or "??"}-{response.hips or "??"}' \
            if 'e' in extra and (response.bust or response.waist or response.hips) \
            else ''
        cup = f'罩杯：{response.cup}' if 'f' in extra and response.cup else ''

        data_list = [i for i in[id, aliases, birthday, vns, blood,  wh, gender_outer, gender_inner, bwh, cup] if i]
        return RenderedItem(
            image=img,
            text="<br>".join(data_list),
            sub_title=name)

    async def _build_producer(self, response: VNDBProducerResponse, vn_response: list[VNDBVnResponse]) -> RenderedBlock:
        id = f'VNDB ID：{response.id}'
        name = f'名称：{response.original or response.name}'
        aliases = f'别称：{"、".join(response.aliases)}' if response.aliases else ''
        language = f'文本语言：{lang[response.lang]}' if response.lang in lang.keys() else ''
        type = f'类型：{develop_type[response.type]}'
        info_list = [i for i in [id, name, aliases, language, type] if i]
        info = "<br>".join(info_list)

        vns: list[RenderedItem] = []
        for vn in vn_response:
            vn_id = f'VNDB ID：{vn.id}'
            vn_img = await File.buffer2base64(await self.downloader.do(vn.image.url)) if vn.image else self.err
            vn_title = f'名称：{vn.alttitle or vn.title}'
            vn_released = f'发布日期：{vn.released}' if vn.released else ''
            vn_rating = f'贝叶斯评分：{vn.rating}' if vn.rating else ''
            vn_list = [i for i in [vn_id, vn_title, vn_released, vn_rating] if i]
            vns.append(RenderedItem(
                image=vn_img,
                text="<br>".join(vn_list),
                sub_title=''
            ))
        return RenderedBlock(
            column_info=info,
            vns=vns,
        )

    async def _build_select(self, response: TouchGalResponse, details: TouchGalDetails = None) -> RenderedRandom | tuple[Any, str]:
        touchgal_id = f'TouchGal ID：{response.id}'
        cover = response.banner
        title = response.name
        avg = f'站内评分：{response.averageRating}'
        source_type = f'站内资源：{"、".join(response.type)}'
        platform = f'资源平台：{"、".join(response.platform)}'
        tags = f'标签：{"、".join([i.tag["name"] for i in response.tag])}'

        lang_list = []
        for i in response.language:
            if i in lang.keys():
                lang_list.append(lang[i])
        language = f'资源语言：{"、".join(lang_list)}'

        if not details:
            text = '\n'.join([i for i in [title, touchgal_id, avg, source_type, platform, language] if i])
            file_path = await File.buffer2base64(await Image.image2jpg_async(await self.downloader.do(cover)), False) if response.banner else self.err
            return file_path, text

        vndb_id = f'VNDB ID：{details.vndb_id}'
        description = details.description.replace('、', '<br>')
        co_imgs = [File.buffer2base64(await self.downloader.do(img), suffix='avif') or self.err for img in details.images]
        imgs = await asyncio.gather(*co_imgs)
        data_list = [i for i in [vndb_id, touchgal_id, tags, avg, source_type, language, platform] if i]
        return RenderedRandom(
            text="<br>".join(data_list),
            sub_title=title,
            main_image=await File.buffer2base64(await self.downloader.do(cover), suffix='avif') if response.banner else self.err,
            images=imgs,
            description=description
        )

    def _build_download(self, response: ResourceResponse) -> str:
        title = f'标题：{response.name}' if response.name else ''
        kind = f'类型：{response.section}' if response.section else ''
        storage = f'资源平台：{response.storage}' if response.storage else ''
        platform = f'支持平台：{"、".join(response.platform)}' if response.platform else ''
        size = f'文件大小：{response.size}' if response.size else ''
        source_type = f'标签：{"、".join(response.type)}' if response.type else ''

        lang_list = []
        for i in response.language:
            if i in lang.keys():
                lang_list.append(lang[i])
        language = f'资源语言：{"、".join(lang_list)}' if lang else ''
        note = f'备注：{response.note}' if response.note else ''
        content = f'链接：{response.content}' if response.content else ''
        code = f'提取码：{response.code}' if response.code else ''
        password = f'解压码：{response.password}' if response.password else ''


        data = [i for i in [title, kind, storage, platform, size, source_type, language, content, code, password ,note] if i]
        return '\n'.join(data)

    async def _build_find(self, response: AnimeTraceData, character_response, buffer: bytes) -> RenderedBlock:
        image = PILImage.open(BytesIO(buffer))
        width, height = image.size
        left = int(width * response.box[0])
        top = int(height * response.box[1])
        right = int(width * response.box[2])
        bottom = int(height * response.box[3])
        area = await asyncio.to_thread(image.crop, (left, top, right, bottom))

        output = BytesIO()
        area.save(output, format='JPEG')

        cha_list = []
        for cha, err_if in zip(character_response, response.character):
            if cha:
                cha_list.append(await self._build_character(cha[0], True))
            else:
                cha_list.append(RenderedItem(
                    sub_title=err_if.character,
                    image=self.err,
                    text=f'出场作品：{err_if.work}<br>VNDB暂无记录，角色可能并非来自Gal'
                ))
        buf = output.getvalue()
        column = ColumnStyle(
            image=await File.buffer2base64(buf) if buf else self.err,
            title=f'检测区域如左图<br>可信度：{"不" if response.not_confident else ""}可信'
        )
        return RenderedBlock(
            column_info=column,
            vns=cha_list,
        )

_builder: Optional[Builder] = None
def get_builder():
    global _builder
    if _builder is None:
        _builder = Builder()
    return _builder