from typing import Any
from pathlib import Path

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api import AstrBotConfig, logger
from astrbot.api.message_components import Reply, Node, Plain, Image, Nodes
from astrbot.api.util import session_waiter, SessionController

from .core.api.type import CommandBody, CommandType
from .core.builder import Builder
from .core.http import get_http
from .core.request import TouchGalRequest
from .core.handler import Handler
from .core.api.exception import Tips, SessionTimeoutException, InvalidArgsException, NoResultException
from .core.cache import Cache
from .core.manager.task_manager import TaskLine




class GalgameBoxPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.resource_path = Path(__file__).parent / "resources"
        self.render_options = {
            'type': 'jpeg',
            'quality': 100
        }
        self.session_data: dict = {}
        self.config = config

        self.builder = None
        self.handler = None
        self.cache = None

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        await get_http(self.config, True)
        self.builder = Builder(self.config, self.resource_path)
        self.handler = Handler()
        self.cache = Cache(self.config)


    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        await self.cache.clean_cache_async()
        await self.cache.close_http_session()


    @filter.command_group("旮旯", alias={'gal', 'GAL'})
    async def gb(self, event: AstrMessageEvent):
        """Galgame百宝盒插件的主指令"""
        pass


    @gb.command('作品', alias={'游戏'})
    async def vn(self, event: AstrMessageEvent, keyword: str):
        """通过关键词查询作品"""
        async for result in self._galgame_command(event, CommandType.VN, keyword):
            yield result


    @gb.command('角色', alias={'人物'})
    async def cha(self, event: AstrMessageEvent, keyword: str):
        """通过关键词查询角色"""
        async for result in self._galgame_command(event, CommandType.CHARACTER, keyword):
            yield result


    @gb.command('厂商', alias={'作者'})
    async def pro(self, event: AstrMessageEvent, keyword: str):
        """通过关键词查询厂商"""
        async for result in self._galgame_command(event, CommandType.PRODUCER, keyword):
            yield result


    @gb.command('id', alias={'ID'})
    async def vn_id(self, event: AstrMessageEvent, keyword: str):
        """通过VNDB ID查询特定内容"""
        async for result in self._galgame_command(event, CommandType.ID, keyword):
            yield result
             

    @gb.command('随机')
    async def random(self, event: AstrMessageEvent):
        """通过TouchGal随机获取一部作品"""
        async for result in self._random_command(event):
            yield result
            

    @gb.command('下载', alias={'资源'})
    async def download(self, event: AstrMessageEvent, id: str):
        """优先通过VNDB ID、TouchGal ID，最后通过关键词搜索获取指定资源的下载链接"""
        async for result in self._download_command(event, id):
            yield result


    @gb.command('出处', alias={'识别'})
    async def find(self, event: AstrMessageEvent, url: str = ''):
        """提供图片或者图片链接识别角色出处，可以先不填参数"""
        async for result in self._find_command(event, url):
            yield result



    def _handle_command_exception(self, event: AstrMessageEvent, e: Exception):
        # 开发用
        # raise e
        logger.error(str(e), exc_info=True)
        if isinstance(e, Tips):
            yield event.chain_result([Reply(id=event.message_obj.message_id), Plain(str(e).split('：')[0])])
        else:
            yield event.chain_result([Reply(id=event.message_obj.message_id), Plain('发生非预期异常！')])



    async def _galgame_command(self, event: AstrMessageEvent, cmd_type: CommandType, keyword: str):
        try:
            cmd = CommandBody(
                type=cmd_type,
                value=keyword,
                msg_id=event.unified_msg_origin
            )
            cache = await self.cache.get_cache_async(cmd)
            if cache:
                yield event.chain_result([Image.fromBytes(cache)])
                return
            buf, extra = await TaskLine(self.config, self.resource_path, cmd).start()
            url = await self.html_render(buf, extra.model_dump(), options=self.render_options)
            yield event.image_result(url)
            await self.cache.download_get_image(url, cmd, True)
        except Exception as e:
            yield next(self._handle_command_exception(event, e))


    async def _random_command(self, event: AstrMessageEvent):
        try:
            cmd = CommandBody(
                type=CommandType.RANDOM,
                value='',
                msg_id=event.unified_msg_origin
            )

            buf, extra = await TaskLine(self.config, self.resource_path, cmd).start()

            url = await self.html_render(buf, extra.model_dump(), options=self.render_options)
            yield event.image_result(url)
        except Exception as e:
            yield next(self._handle_command_exception(event, e))


    async def _download_command(self, event: AstrMessageEvent, id: str):
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
                if len(keyword) > 1 and keyword[0] == 'v' and keyword[1:].isdigit() and total == 1:
                    if not res:
                        raise NoResultException(f'{cmd.type}-{cmd.value}')
                    touchgal_id = res[0].id
                elif total > 0:
                    cmd.type = CommandType.SELECT
                    msgs: list[tuple[Any, str]] = await self.builder.build_options(cmd, res)
                    content = []
                    for idx, msg in enumerate(msgs, start=1):
                        node = Node(uin=event.get_self_id(),
                                    content=[
                                        Plain(f'【{idx}】'),
                                        Image.fromBase64(msg[0]),
                                        Plain(msg[1])
                                    ])
                        content.append(node)

                    tips = '未识别到ID，改为关键词搜索\n从以下内容中选择一项\n30s内回复输入对应数字获取相应资源'
                    yield event.plain_result(tips)
                    yield event.chain_result([Nodes(content)])

                    @session_waiter(timeout=30)
                    async def empty_mention_waiter(controller: SessionController, sess_event: AstrMessageEvent):

                        message = sess_event.message_str
                        accept = int(message) if message.isdigit() else None

                        if accept and 0 < accept <= total:
                            controller.stop()
                            self.session_data[sess_event.get_session_id()] = accept - 1
                            return
                        else:
                            invalid = '无效的消息，请重新输入'
                            result = event.make_result()
                            result.chain = [Plain(invalid)]
                            await event.send(result)

                    try:
                        await empty_mention_waiter(event)
                        index = self.session_data.pop(event.get_session_id())
                        touchgal_id = res[index].id
                        cmd.type = CommandType.DOWNLOAD
                    except TimeoutError:
                        raise SessionTimeoutException(f'{cmd.type}-{cmd.value}')

                else:
                    raise InvalidArgsException(f'{cmd.type}-{cmd.value}')

            resp = await request.request_resources(touchgal_id)
            msg_arr: list[tuple[str, str]] = await self.builder.build_options(cmd, resp)
            nodes = [Node(uin=event.get_self_id(), content=[Plain(msg[1])]) for msg in msg_arr]

            yield event.chain_result([Nodes(nodes)])
        except Exception as e:
            yield next(self._handle_command_exception(event, e))

    async def _find_command(self, event: AstrMessageEvent, url: str):
        try:
            cmd = CommandBody(
                type=CommandType.FIND,
                value='',
                msg_id=event.unified_msg_origin
            )
            if url.startswith('http'):
                cmd.value = url
            else:
                for msg in event.message_obj.message:
                    if isinstance(msg, Image):
                        cmd.value = msg.url
                        break
            if not cmd.value:
                tips = '未检测到指令参数\n改为从下一条消息中获取\n在30s内发送一张图片'
                yield event.plain_result(tips)
                @session_waiter(timeout=30)
                async def empty_mention_waiter(controller: SessionController, sess_event: AstrMessageEvent):

                    message = sess_event.message_obj.message
                    _url = ''
                    for _msg in message:
                        if isinstance(_msg, Image):
                            _url = _msg.url
                            controller.stop()
                            break
                    if not _url:
                        invalid = '无效的消息，请重新输入'
                        result = event.make_result()
                        result.chain = [Plain(invalid)]
                        await event.send(result)
                    else:
                        self.session_data[sess_event.get_session_id()] = _url
                try:
                    await empty_mention_waiter(event)
                    cmd.value = self.session_data.pop(event.get_session_id())
                except TimeoutError:
                    raise SessionTimeoutException(f'{cmd.type}-{cmd.value}')

            buf, extra = await TaskLine(self.config, self.resource_path, cmd).start()
            url = await self.html_render(buf, extra.model_dump(), options=self.render_options)
            yield event.image_result(url)

        except Exception as e:
            yield next(self._handle_command_exception(event, e))


