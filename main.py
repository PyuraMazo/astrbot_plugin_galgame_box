from typing import Any
from pathlib import Path

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api import AstrBotConfig, logger
from astrbot.api.message_components import Reply, Node, Plain, Image, Nodes
from astrbot.api.util import session_waiter, SessionController

from .core.api.type import CommandBody, CommandType
from .core.builder import Builder
from .core.http import TouchGalRequest
from .core.handler import Handler
from .core.api.exception import *
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

        self.config = config
        self.session_data: dict[str, int] = {}
        self.builder = Builder(self.config, self.resource_path)
        self.handler = Handler()
        self.cache = Cache(self.config)



    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        pass

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        await self.cache.clean_cache_async()
        await self.cache.close_http_session()


    @filter.command_group("gb", alias={'旮旯', 'gal', 'GAL'})
    async def gb(self, event: AstrMessageEvent):
        """galgame_info插件的主指令"""
        pass

    @gb.command('vn', alias={'作品', '游戏'})
    async def vn(self, event: AstrMessageEvent, keyword: str):
        """通过关键词查询作品"""
        try:
            cmd = CommandBody(
                type=CommandType.VN,
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
            yield event.chain_result([Reply(id=event.message_obj.message_id), Plain(str(e))])
            logger.error(str(e))


    @gb.command('cha', alias={'角色'})
    async def cha(self, event: AstrMessageEvent, keyword: str):
        """通过关键词查询角色"""
        try:
            cmd = CommandBody(
                type=CommandType.CHARACTER,
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
            yield event.chain_result([Reply(id=event.message_obj.message_id), Plain('发生错误！' + str(e))])
            logger.error(str(e))


    @gb.command('pro', alias={'厂商'})
    async def pro(self, event: AstrMessageEvent, keyword: str):
        """通过关键词查询厂商"""
        try:
            cmd = CommandBody(
                type=CommandType.PRODUCER,
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
            yield event.chain_result([Reply(id=event.message_obj.message_id), Plain('发生错误！' + str(e))])
            logger.error(str(e))


    @gb.command('vn_id', alias={'ID', 'id'})
    async def vn_id(self, event: AstrMessageEvent, keyword: str):
        """通过VNDB ID查询特定内容"""
        try:
            cmd = CommandBody(
                type=CommandType.ID,
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
            yield event.chain_result([Reply(id=event.message_obj.message_id), Plain('发生错误！' + str(e))])
            logger.error(str(e))


    @gb.command('random', alias={'随机'})
    async def random(self, event: AstrMessageEvent):
        """通过TouchGal随机获取一部作品"""
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
            yield event.chain_result([Reply(id=event.message_obj.message_id), Plain('发生错误！' + str(e))])
            logger.error(str(e))

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
                if len(keyword) > 1 and keyword[0] == 'v' and keyword[1:].isdigit() and total == 1:
                    if not res: raise InternetException
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

                    @session_waiter(timeout=30, record_history_chains=False)
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
                        raise SessionTimeoutException

                else:
                    raise InvalidArgsException

            resp = await request.request_resources(touchgal_id)
            msg_arr: list[tuple[str, str]] = await self.builder.build_options(cmd, resp)
            nodes = [Node(uin=event.get_self_id(), content=[Plain(msg[1])]) for msg in msg_arr]

            yield event.chain_result([Nodes(nodes)])
        except Exception as e:
            yield event.chain_result([Reply(id=event.message_obj.message_id), Plain('发生错误！' + str(e))])
            logger.error(str(e))