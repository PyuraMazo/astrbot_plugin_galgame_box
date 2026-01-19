import asyncio
from typing import Any
from pathlib import Path

from astrbot.core import AstrBotConfig

from .api.type import CommandBody, UnrenderedData, ConfigDict, RenderedItem, CommandType, RenderedProducer, TouchGalDetails, RenderedInfo
from .api.model import VNDBVnResponse, VNDBCharacterResponse, VNDBProducerResponse, ModelDict, TouchGalResponse, ResourceResponse
from .cache import Cache
from .utils.file import File


class Builder:
    def __init__(self, config: AstrBotConfig, resources_path: Path):
        self.config = config
        self.bg = resources_path / 'image' / 'pixiv139681518.jpg'
        self.err = resources_path / 'image' / 'error.jpg'
        self.font = resources_path / 'font' / 'hpsimplifiedhans-regular.ttf'
        
        self.cache = Cache(self.config)
        


    async def build_options(self, command_body: CommandBody,
                            response: list[VNDBVnResponse] | list[VNDBCharacterResponse] | list[VNDBProducerResponse] | list[TouchGalResponse] | list[ResourceResponse],
                            **kwargs)\
            -> UnrenderedData | list[tuple[str, str]]:
        bgi = await File.read_buffer2base64(str(self.bg))
        font = await File.read_buffer2base64(str(self.font))
        
        title = self._build_title(command_body, len(response))
        run_type = command_body.type
        if run_type == CommandType.ID:
            for cmd_type in CommandType:
                if cmd_type.value[0] == command_body.value[0]:
                    run_type = cmd_type
                    break

        if run_type == CommandType.VN:
            resp: list[VNDBVnResponse] = response
            co_items = [self._build_vn(res) for res in resp]
            items = await asyncio.gather(*co_items)
            return UnrenderedData(
                title=title,
                items=items,
                bg_image=bgi,
                font=font
            )
        elif run_type == CommandType.CHARACTER:
            resp: list[VNDBCharacterResponse] = response
            co_items = [self._build_character(res) for res in resp]
            items = await asyncio.gather(*co_items)
            return UnrenderedData(
                title=title,
                items=items,
                bg_image=bgi,
                font=font
            )
        elif run_type == CommandType.PRODUCER:
            resp: list[VNDBProducerResponse] = response
            vns: list[list[VNDBVnResponse]] = kwargs['vns']
            co_pros = [self._build_producer(pro, vn) for pro, vn in zip(resp, vns)]
            pros = await asyncio.gather(*co_pros)
            return UnrenderedData(
                title=title,
                items=pros,
                bg_image=bgi,
                font=font
            )
        elif run_type == CommandType.RANDOM:
            resp: list[TouchGalResponse] = response
            details: TouchGalDetails = kwargs['details']
            res = await self._build_details(resp[0], details)
            return UnrenderedData(
                title=title,
                items=[res],
                bg_image=bgi,
                font=font
            )
        elif run_type == CommandType.DOWNLOAD:
            resp: list[ResourceResponse] = response
            return [('', self._build_resources(i)) for i in resp]
        elif run_type == CommandType.SELECT:
            resp: list[TouchGalResponse] = response
            return [await self._build_details(i) for i in resp]
        else: raise NotImplementedError


    def _build_title(self, command_body: CommandBody, count: int) -> str:
        run_type = f'搜索指令「{command_body.type.value}」'
        value = f'搜索词「{command_body.value}」' if command_body.value else ''
        count = f'搜索结果「{count}条」' if command_body.type != CommandType.RANDOM else ''
        format_title = [i for i in [run_type, value, count] if i]
        return "<br>".join(format_title)


    async def _build_vn(self, response: VNDBVnResponse) -> RenderedItem:
        id = f'VNDB ID：{response.id}'
        img = await File.buffer2base64(await self.cache.download_get_image(response.image.url)) if response.image else self.err
        avg = f'平均分：{response.average}' if response.average else ''
        rating = f'贝叶斯评分：{response.rating}' if response.rating else ''
        release = f'发布日期：{response.released}' if response.released else ''
        length = f'游玩时间：{response.length_minutes}' if response.length_minutes else ''

        platform = f'支持平台：{"、".join(response.platforms)}' if response.platforms else ''
        alias = f'别称：{"、".join(response.aliases)}' if response.aliases else ''

        pro = [f'{p.original or p.name}（{p.id}）' for p in response.developers] if response.developers else []
        dev = f'制作者（VNDB ID）：{"、".join(pro)}' if pro else ''

        lang = []
        if response.titles:
            for title in response.titles:
                if title.lang in ConfigDict.lang.keys():
                    lang.append(f'{ConfigDict.lang[title.lang]}标题（{'官方' if title.official else '非官方'}）：{title.title}')
        titles = "<br>".join(lang)

        data_list = [i for i in [id, titles, alias, rating, avg, length, dev, release, platform] if i]
        return RenderedItem(
            image=img,
            text="<br>".join(data_list),
            sub_title='')

    async def _build_character(self, response: VNDBCharacterResponse) -> RenderedItem:
        id = f'VNDB ID：{response.id}'
        img = await File.buffer2base64(await self.cache.download_get_image(response.image.url)) if response.image else self.err
        name = response.original or response.name
        aliases = f'别名：{"、".join(response.aliases)}' if response.aliases else ''
        birthday = f'生日：{response.birthday[0]}月{response.birthday[1]}日' if response.birthday else ''

        vn_list = []
        for vn in response.vns:
            vn_list.append(f'出场作品（VNDB ID）：「{vn.alttitle or vn.title}」（{vn.id}）')
        vns = "、".join(vn_list)

        option: list[str] = self.config['searchSetting']['characterOptions']
        extra: list = []
        if option:
            extra =  [i.split('-')[0] for i in option]

        blood = f'血型：{response.blood_type}' if 'a' in extra and response.blood_type else ''
        wh = f'身高/体重（cm/kg）：{response.height or '??'}/{response.weight or '??'}' \
            if 'b' in extra and (response.weight or response.height) \
            else ''
        gender_outer = f'性别：{ModelDict.gender[response.sex[0]]}' if 'c' in extra else ''
        gender_inner =  f'真实性别：{ModelDict.gender[response.sex[1]]}' if 'd' in extra else ''
        bwh = f'三围：{response.bust or '??'}-{response.waist or '??'}-{response.hips or '??'}' \
            if 'e' in extra and (response.bust or response.waist or response.hips) \
            else ''
        cup = f'罩杯：{response.cup}' if 'f' in extra and response.cup else ''

        data_list = [i for i in[id, aliases, birthday, vns, blood,  wh, gender_outer, gender_inner, bwh, cup] if i]
        return RenderedItem(
            image=img,
            text="<br>".join(data_list),
            sub_title=name)

    async def _build_producer(self, response: VNDBProducerResponse, vn_response: list[VNDBVnResponse]) -> RenderedProducer:
        id = f'VNDB ID：{response.id}'
        name = f'名称：{response.original or response.name}'
        aliases = f'别称：{"、".join(response.aliases)}' if response.aliases else ''
        lang = f'文本语言：{ConfigDict.lang[response.lang]}' if response.lang in ConfigDict.lang.keys() else ''
        type = f'类型：{ConfigDict.develop_type[response.type]}'
        info_list = [i for i in [id, name, aliases, lang, type] if i]
        info = "<br>".join(info_list)

        vns: list[RenderedItem] = []
        for vn in vn_response:
            vn_id = f'VNDB ID：{vn.id}'
            vn_img = await File.buffer2base64(await self.cache.download_get_image(vn.image.url)) if vn.image else self.err
            vn_title = f'名称：{vn.alttitle or vn.title}'
            vn_released = f'发布日期：{vn.released}' if vn.released else ''
            vn_rating = f'贝叶斯评分：{vn.rating}' if vn.rating else ''
            vn_list = [i for i in [vn_id, vn_title, vn_released, vn_rating] if i]
            vns.append(RenderedItem(
                image=vn_img,
                text="<br>".join(vn_list),
                sub_title=''
            ))
        return RenderedProducer(
            column_info=info,
            vns=vns,
        )


    async def _build_details(self, response: TouchGalResponse, details: TouchGalDetails = None) -> RenderedInfo | tuple[Any, str]:
        touchgal_id = f'TouchGal ID：{response.id}'
        cover = response.banner
        title = response.name
        avg = f'站内评分：{response.averageRating}'
        source_type = f'站内资源：{"、".join(response.type)}'
        platform = f'资源平台：{"、".join(response.platform)}'
        tags = f'标签：{"、".join([i.tag["name"] for i in response.tag])}'

        lang = []
        for i in response.language:
            if i in ConfigDict.lang.keys():
                lang.append(ConfigDict.lang[i])
        language = f'资源语言：{'、'.join(lang)}'

        if not details:
            text = '\n'.join([i for i in [title, touchgal_id, avg, source_type, platform, language] if i])
            file_path = await File.buffer2base64(await File.avif2jpg_async(await self.cache.download_get_image(cover)), False) if response.banner else self.err
            return file_path, text

        vndb_id = f'VNDB ID：{details.vndb_id}'
        description = details.description.replace('、', '<br>')
        co_imgs = [File.buffer2base64(await self.cache.download_get_image(img), extend='avif') or self.err for img in details.images]
        imgs = await asyncio.gather(*co_imgs)
        data_list = [i for i in [vndb_id, touchgal_id, tags, avg, source_type, language, platform] if i]
        return RenderedInfo(
            text=f"<br>".join(data_list),
            sub_title=title,
            main_image=await File.buffer2base64(await self.cache.download_get_image(cover), extend='avif') if response.banner else self.err,
            images=imgs,
            description=description,
        )

    def _build_resources(self, response: ResourceResponse) -> str:
        title = f'标题：{response.name}' if response.name else ''
        kind = f'类型：{response.section}' if response.section else ''
        storage = f'资源平台：{response.storage}' if response.storage else ''
        platform = f'支持平台：{"、".join(response.platform)}' if response.platform else ''
        size = f'文件大小：{response.size}' if response.size else ''
        source_type = f'标签：{"、".join(response.type)}' if response.type else ''

        lang = []
        for i in response.language:
            if i in ConfigDict.lang.keys():
                lang.append(ConfigDict.lang[i])
        language = f'资源语言：{"、".join(lang)}' if lang else ''
        note = f'备注：{response.note}' if response.note else ''
        content = f'链接：{response.content}' if response.content else ''
        code = f'提取码：{response.code}' if response.code else ''
        password = f'解压码：{response.password}' if response.password else ''


        data = [i for i in [title, kind, storage, platform, size, source_type, language, content, code, password ,note] if i]
        return '\n'.join(data)