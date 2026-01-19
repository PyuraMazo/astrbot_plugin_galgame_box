from typing import Any
from os import path

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import AstrBotConfig
from astrbot.api.message_components import Reply, Node, Plain, Image, Nodes
from astrbot.core.utils.session_waiter import (
    session_waiter,
    SessionController,
)

from .core.api.type import CommandBody, CommandType, Dict
from .core.builder import Builder
from .core.http import VNDBRequest, TouchGalRequest
from .core.utils.file import File
from .core.handler import Handler
from .core.api.excption import *
from .core.cache import Cache




@register("galgame_box", "PyuraMazo", "结合了VNDB和TouchGal的API，更全面地展示关于Galgame的完整信息，还提供更多的相关服务。", "1.0.0")
class MyPlugin(Star):
    resource_path = path.join(path.dirname(path.abspath(__file__)), 'core', 'resources')
    template_path = path.join(resource_path, 'template')
    render_options = {
        'type': 'jpeg',
        'quality': 100
    }

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.builder = Builder(self.config)
        self.handler = Handler()
        self.session_data: dict = {}
        self.cache = Cache(self.config)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        pass


    @filter.command_group("gb", alias={'旮旯', 'gal', 'GAL'})
    async def gb(self, event: AstrMessageEvent):
        """galgame_info插件的主指令"""
        pass

    @gb.command('vn', alias={'作品'})
    async def vn(self, event: AstrMessageEvent, keyword: str):
        """通过关键词查询作品"""
        try:
            cmd = CommandBody(
                type=CommandType.VN,
                value=keyword,
                msg_id=event.unified_msg_origin
            )
            cache = self.cache.get_cache(cmd)
            print(cache)
            if cache:
                yield event.chain_result([Image.fromBytes(cache)])
                return

            request = VNDBRequest(self.config, cmd)
            rendered_html = path.join(self.template_path, Dict.html_list[cmd.type.value])
            res = await request.request_simply()
            data = await self.builder.build_options(cmd, res)
            buffer = File.read_text(rendered_html)

            url = await self.html_render(buffer, data.model_dump(), options=self.render_options)
            yield event.image_result(url)
            await self.cache.download_get_image(url, cmd, True)
        except Exception as e:
            yield event.chain_result([Reply(id=event.message_obj.message_id), Plain(str(e))])

    @gb.command('cha', alias={'角色'})
    async def cha(self, event: AstrMessageEvent, keyword: str):
        """通过关键词查询角色"""
        try:
            cmd = CommandBody(
                type=CommandType.CHARACTER,
                value=keyword,
                msg_id=event.unified_msg_origin
            )
            cache = self.cache.get_cache(cmd)
            if cache:
                yield event.chain_result([Image.fromBytes(cache)])
                return

            request = VNDBRequest(self.config, cmd)
            rendered_html = path.join(self.template_path, Dict.html_list[cmd.type.value])
            res = await request.request_simply()
            data = await self.builder.build_options(cmd, res)
            buffer = File.read_text(rendered_html)

            url = await self.html_render(buffer, data.model_dump(), options=self.render_options)
            yield event.image_result(url)
            await self.cache.download_get_image(url, cmd, True)
        except Exception as e:
            yield event.chain_result([Reply(id=event.message_obj.message_id), Plain(str(e))])


    @gb.command('pro', alias={'厂商'})
    async def pro(self, event: AstrMessageEvent, keyword: str):
        """通过关键词查询厂商"""
        try:
            cmd = CommandBody(
                type=CommandType.PRODUCER,
                value=keyword,
                msg_id=event.unified_msg_origin
            )
            cache = self.cache.get_cache(cmd)
            if cache:
                yield event.chain_result([Image.fromBytes(cache)])
                return

            request = VNDBRequest(self.config, cmd)
            rendered_html = path.join(self.template_path, Dict.html_list[cmd.type.value])
            pro, vns = await request.request_by_producer()
            data = await self.builder.build_options(cmd, pro, vns=vns)
            buffer = File.read_text(rendered_html)

            url = await self.html_render(buffer, data.model_dump(), options=self.render_options)
            yield event.image_result(url)
            await self.cache.download_get_image(url, cmd, True)
        except Exception as e:
            yield event.chain_result([Reply(id=event.message_obj.message_id), Plain(str(e))])


    @gb.command('id', alias={'ID'})
    async def id(self, event: AstrMessageEvent, keyword: str):
        """通过VNDB ID查询特定内容"""
        try:
            cmd = CommandBody(
                type=CommandType.ID,
                value=keyword,
                msg_id=event.unified_msg_origin
            )
            cache = self.cache.get_cache(cmd)
            if cache:
                yield event.chain_result([Image.fromBytes(cache)])
                return

            request = VNDBRequest(self.config, cmd)
            if cmd.value[0] not in Dict.id2command.keys():
                raise InvalidArgsException

            actual_type_value = Dict.id2command[cmd.value[0]]
            rendered_html = path.join(self.template_path, Dict.html_list[actual_type_value])
            res = await request.request_by_id()

            if actual_type_value == CommandType.PRODUCER.value:
                data = await self.builder.build_options(cmd, res[0], vns=res[1])
            else:
                data = await self.builder.build_options(cmd, res)

            buffer = File.read_text(rendered_html)
            url = await self.html_render(buffer, data.model_dump(), options=self.render_options)
            yield event.image_result(url)
            await self.cache.download_get_image(url, cmd, True)
        except Exception as e:
            yield event.chain_result([Reply(id=event.message_obj.message_id), Plain(str(e))])


    @gb.command('random', alias={'随机'})
    async def random(self, event: AstrMessageEvent):
        """通过TouchGal随机获取一部作品"""
        try:
            cmd = CommandBody(
                type=CommandType.RANDOM,
                value='',
                msg_id=event.unified_msg_origin
            )

            request = TouchGalRequest(self.config)
            rendered_html = path.join(self.template_path, Dict.html_list[cmd.type.value])
            unique_id = await request.request_random()
            text = await request.request_html(unique_id)
            details = self.handler.handle_touchgal_details(text)
            resp = (await request.request_vn_by_search(details.vndb_id))[0]
            data = await self.builder.build_options(cmd, resp, details=details)
            buffer = File.read_text(rendered_html)

            url = await self.html_render(buffer, data.model_dump(), options=self.render_options)
            yield event.image_result(url)
        except Exception as e:
            yield event.chain_result([Reply(id=event.message_obj.message_id), Plain(str(e))])
            raise e

    @gb.command('download', alias={'下载'})
    async def download(self, event: AstrMessageEvent, id: str):
        """优先通过VNDB ID、TouchGal ID，最后通过关键词搜索获取指定资源的下载链接"""
        try:
            cmd = CommandBody(
                type=CommandType.DOWNLOAD,
                value=id,
                msg_id=event.unified_msg_origin
            )

            request = TouchGalRequest(self.config)
            keyword = cmd.value
            touchgal_id: int
            if keyword.isdigit():
                touchgal_id = int(keyword)
            else:
                res, total = await request.request_vn_by_search(keyword)
                if keyword[0] == 'v' and keyword[1:].isdigit() and total == 1:
                    if not res: raise InternetException
                    touchgal_id = res[0].id
                elif total > 0:
                    cmd.type = CommandType.SELECT
                    msgs: list[tuple[Any, str]] = await self.builder.build_options(cmd, res)
                    content = []
                    for msg in msgs:
                        node = Node(uin=event.get_self_id(),
                                    content=[
                                        Plain(f'【{msgs.index(msg) + 1}】'),
                                        Image.fromBase64(msg[0]),
                                        Plain(msg[1])
                                    ])
                        content.append(node)

                    tips = '未识别到ID，改为关键词搜索\n从以下内容中选择一项\n30s内回复输入对应数字获取相应资源'
                    yield event.plain_result(tips)
                    yield event.chain_result(content)

                    @session_waiter(timeout=30, record_history_chains=False)
                    async def empty_mention_waiter(controller: SessionController, sess_event: AstrMessageEvent):
                        message = sess_event.message_str
                        accept = int(message) if message.isdigit() else None

                        if accept and 0 < accept <= total:
                            controller.stop()
                            self.session_data['index'] = accept - 1
                            return
                        else:
                            invalid = '无效的消息，请重新输入'
                            result = event.make_result()
                            result.chain = [Plain(invalid)]
                            await event.send(result)

                    try:
                        await empty_mention_waiter(event)
                        index = self.session_data.pop('index')
                        touchgal_id = res[index].id
                        cmd.type = CommandType.DOWNLOAD
                    except TimeoutError:
                        raise SessionTimeoutException

                else:
                    raise InvalidArgsException

            resp = await request.request_resources(touchgal_id)
            msg_arr: list[tuple[str, str]] = await self.builder.build_options(cmd, resp)
            nodes = [Node(uin=event.get_self_id(), content=[Plain(msg[1])]) for msg in msg_arr]

            yield event.chain_result([Nodes(nodes)])
        except Exception as e:
            yield event.chain_result([Reply(id=event.message_obj.message_id), Plain(str(e))])


    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        self.cache.clean_cache()

