from typing import Optional, Any

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api.message_components import Reply, Plain
from astrbot.api import AstrBotConfig, logger
from astrbot.api.platform import MessageType

from .core.api.const import id2command
from .core.api.exception import Tips, InvalidArgsException
from .core.api.type import CommandType, CommandBody
from .core.manager.task_line import TaskLine, get_task_line



class GalgameBoxPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.task_line: Optional[TaskLine] = None

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        self.task_line = get_task_line()

        await self.task_line.initialize(self.config)

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        await self.task_line.terminate()


    @filter.command_group("旮旯", alias={'gal', 'GAL'})
    async def gal_box(self, event: AstrMessageEvent):
        """Galgame百宝盒插件的主指令"""
        pass

    @gal_box.command('作品', alias={'游戏'})
    async def vn(self, event: AstrMessageEvent, keyword: str):
        """通过关键词查询作品"""
        async for res in self._common_command(event, CommandType.VN, keyword):
            yield res

    @gal_box.command('角色', alias={'人物'})
    async def character(self, event: AstrMessageEvent, keyword: str):
        """通过关键词查询作品"""
        async for res in self._common_command(event, CommandType.CHARACTER, keyword):
            yield res

    @gal_box.command('厂商', alias={'作者'})
    async def producer(self, event: AstrMessageEvent, keyword: str):
        """通过关键词查询厂商"""
        async for res in self._common_command(event, CommandType.PRODUCER, keyword):
            yield res

    @gal_box.command('ID', alias={'id'})
    async def vndb_id(self, event: AstrMessageEvent, keyword: str):
        """通过VNDB ID查询特定内容"""
        async for res in self._common_command(event, CommandType.ID, keyword):
            yield res

    @gal_box.command('随机')
    async def random(self, event: AstrMessageEvent):
        """通过TouchGal随机获取一部作品"""
        async for res in self._common_command(event, CommandType.RANDOM):
            yield res

    @gal_box.command('下载', alias={'资源'})
    async def download(self, event: AstrMessageEvent, id: str):
        """优先通过VNDB ID、TouchGal ID，最后通过关键词搜索获取指定资源的下载链接"""
        async for res in self._common_command(event, CommandType.DOWNLOAD, id):
            yield res

    @gal_box.command('出处', alias={'识别'})
    async def find(self, event: AstrMessageEvent, url: str = ''):
        """提供图片或者图片链接识别角色出处，可以先不填参数"""
        async for res in self._common_command(event, CommandType.FIND, url):
            yield res

    @gal_box.command('推荐', alias={'标签'})
    async def recommend(self, event: AstrMessageEvent, tags: str):
        """提供一个或多个标签，从TouchGal网站中获取推荐内容"""
        async for res in self._common_command(event, CommandType.RECOMMEND, tags):
            yield res

    @gal_box.command('绑定', alias={})
    async def bind(self, event: AstrMessageEvent):
        """通过Steam API和Steam ID绑定Steam账号，只能在私聊频道中生效"""
        async for res in self._common_command(event, CommandType.BIND):
            yield res

    @gal_box.command('拼图', alias={'steam'})
    async def schedule(self, event: AstrMessageEvent):
        """生成基于Steam的游玩记录的Galgame总览"""
        async for res in self._common_command(event, CommandType.SCHEDULE):
            yield res


    async def _common_command(self, event: AstrMessageEvent, cmd_type: CommandType, keyword: str = ''):
        try:
            if cmd_type == CommandType.BIND and not event.message_obj.type == MessageType.FRIEND_MESSAGE:
                yield event.plain_result('为保护你的隐私，请通过私聊频道进行绑定')
                return
            cmd = self._check_keyword_validity(event, cmd_type, keyword)
            async for res in self.task_line.run(cmd):
                yield res
        except Exception as e:
            yield next(self._handle_command_exception(event, e))


    def _handle_command_exception(self, event: AstrMessageEvent, e: Exception):
        logger.error(str(e), exc_info=True)
        if isinstance(e, Tips):
            yield event.chain_result([Reply(id=event.message_obj.message_id), Plain(str(e).split('：')[0])])
        else:
            yield event.chain_result([Reply(id=event.message_obj.message_id), Plain('发生非预期异常！')])

    def _check_keyword_validity(self, event: AstrMessageEvent, cmd_type: CommandType, keyword: str):
        valid = True
        cmd = CommandBody(
            type=cmd_type,
            value=keyword,
            event=event
        )
        if cmd_type == CommandType.ID:
            if keyword[0] not in id2command.keys():
                valid = False
        elif cmd_type == CommandType.FIND:
            cmd.value = keyword if keyword.startswith('http') else ''
        elif cmd_type == CommandType.RECOMMEND:
            if keyword == '':
                valid = False
            else:
                msg = event.message_str.strip()
                index = msg.find(keyword)
                cmd.value = msg[index:]

        if valid:
            return cmd
        else:
            raise InvalidArgsException(cmd)
