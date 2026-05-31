from apscheduler.triggers.cron import CronTrigger

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Plain, Reply
from astrbot.api.platform import MessageType
from astrbot.api.star import Context, Star
from astrbot.core.message.message_event_result import MessageChain
from astrbot.core.platform.message_session import MessageSession
from astrbot.core.star.filter.command import GreedyStr

from .core.api.exception import Tips
from .core.api.type import CommandType
from .core.manager.task_line import TaskLine, get_task_line


class GalgameBoxPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.ctx = context
        self.task_line: TaskLine | None = None
        self.event_list: list[str] = []

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        self.task_line = get_task_line()

        self._init_ids()
        await self.task_line.initialize(self.config)
        await self._register_gal_event()

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        await self._cancel_gal_event()
        await self.task_line.terminate()

    @filter.command_group("旮旯", alias={"gal", "GAL"})
    async def gal_box(self, event: AstrMessageEvent):
        """Galgame百宝盒插件的主指令"""
        pass

    @gal_box.command("作品", alias={"游戏", "vn"})
    async def vn(self, event: AstrMessageEvent, keyword: str):
        """通过关键词查询作品"""
        async for res in self._common_command(event, CommandType.VN, keyword):
            yield res

    @gal_box.command("角色", alias={"人物", "character"})
    async def character(self, event: AstrMessageEvent, keyword: str):
        """通过关键词查询角色"""
        async for res in self._common_command(event, CommandType.CHARACTER, keyword):
            yield res

    @gal_box.command("厂商", alias={"作者", "producer"})
    async def producer(self, event: AstrMessageEvent, keyword: str):
        """通过关键词查询厂商"""
        async for res in self._common_command(event, CommandType.PRODUCER, keyword):
            yield res

    @gal_box.command("ID", alias={"id"})
    async def vndb_id(self, event: AstrMessageEvent, keyword: str):
        """通过VNDB ID查询特定内容"""
        async for res in self._common_command(event, CommandType.ID, keyword):
            yield res

    @gal_box.command("简讯", alias={"event"})
    async def gal_event(self, event: AstrMessageEvent):
        """了解今日旮旯讯息，包括今天发售游戏与生日角色"""
        async for res in self._common_command(event, CommandType.EVENT):
            yield res

    @gal_box.command("随机", alias={"random"})
    async def random(self, event: AstrMessageEvent):
        """通过TouchGal随机获取一部作品"""
        async for res in self._common_command(event, CommandType.RANDOM):
            yield res

    @gal_box.command("下载", alias={"资源", "download"})
    async def download(self, event: AstrMessageEvent, id: str):
        """优先通过VNDB ID、TouchGal ID，最后通过关键词搜索获取指定资源的下载链接"""
        async for res in self._common_command(event, CommandType.DOWNLOAD, id):
            yield res

    @gal_box.command("推荐", alias={"标签", "recommend"})
    async def recommend(self, event: AstrMessageEvent, tags: GreedyStr):
        """提供一个或多个标签，从TouchGal网站中获取推荐内容"""
        async for res in self._common_command(event, CommandType.RECOMMEND, tags):
            yield res

    @gal_box.command("出处", alias={"识别", "find"})
    async def find(self, event: AstrMessageEvent, url: str = ""):
        """提供图片或者图片链接识别角色出处，可以先不填参数"""
        async for res in self._common_command(event, CommandType.FIND, url):
            yield res

    @gal_box.command("绑定", alias={"bind"})
    async def bind(self, event: AstrMessageEvent):
        """通过Steam API和Steam ID绑定Steam账号，只能在私聊频道中生效"""
        async for res in self._common_command(event, CommandType.BIND):
            yield res

    @gal_box.command("拼图", alias={"puzzle"})
    async def puzzle(self, event: AstrMessageEvent):
        """生成基于Steam的游玩记录的Galgame总览"""
        async for res in self._common_command(event, CommandType.PUZZLE):
            yield res

    async def _gal_event(self):
        # white_list = self.config.get("searchSetting", {}).get("collectAutomatically", False)
        async for res in self._common_command(None, CommandType.GAL_EVENT):
            for group in self.event_list:
                await self.ctx.send_message(group, MessageChain().url_image(res))

    async def _register_gal_event(self):
        if not self.event_list:
            logger.warning("推送白名单为空，定时任务不会执行！")
            return

        schedule_time = self.config.get("scheduleSetting", {}).get("galEvent", "07:00")
        if ":" in schedule_time:
            hour, minute = map(int, schedule_time.split(":", 1))
        elif "：" in schedule_time:
            hour, minute = map(int, schedule_time.split("：", 1))
        else:
            logger.error("时间格式错误，定时任务不会执行！")
            return
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            schedule_id = "gal_event"
            scheduler = self.ctx.cron_manager.scheduler

            scheduler.add_job(
                self._gal_event,
                trigger=CronTrigger(hour=hour, minute=minute),
                id=schedule_id,
                replace_existing=True,
                misfire_grace_time=120,
            )
        else:
            logger.error("时间格式错误，定时任务不会执行！")
            return

    async def _cancel_gal_event(self):
        schedule_id = "gal_event"
        scheduler = self.ctx.cron_manager.scheduler
        if scheduler.get_job(schedule_id):
            scheduler.remove_job(schedule_id)

    def _init_ids(self):
        ids = self.config.get("searchSetting", {}).get("eventList", [])

        def func(_: str):
            platform, group = _.split("-", 1)
            return MessageSession.from_str(f"{platform}:GroupMessage:{group}")

        self.event_list = list(map(func, ids))

    async def _common_command(
        self, event: AstrMessageEvent | None, cmd_type: CommandType, keyword: str = ""
    ):
        try:
            if (
                cmd_type == CommandType.BIND
                and not event.message_obj.type == MessageType.FRIEND_MESSAGE
            ):
                yield event.plain_result("为保护你的隐私，请通过私聊频道进行绑定")
                return
            async for res in self.task_line.run(event, cmd_type, keyword):
                yield res
        except Exception as e:
            yield await anext(self._handle_command_exception(event, e))

    async def _handle_command_exception(
        self, event: AstrMessageEvent | None, e: Exception
    ):
        logger.error(str(e), exc_info=True)
        msg = "发生非预期异常！"
        if isinstance(e, Tips):
            msg = str(e).split("：")[0]

        if event is not None:
            yield event.chain_result(
                [Reply(id=event.message_obj.message_id), Plain(msg)]
            )
        else:
            for group in self.event_list:
                await self.ctx.send_message(group, MessageChain().message(msg))
