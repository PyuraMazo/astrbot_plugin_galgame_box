from apscheduler.triggers.cron import CronTrigger

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Plain, Reply
from astrbot.api.star import Context, Star
from astrbot.core.message.message_event_result import MessageChain
from astrbot.core.platform.message_session import MessageSession
from astrbot.core.star.filter.command import GreedyStr

from .core.command import *
from .core.function.cache import Cache
from .core.network import Downloader, Http
from .core.services import Services
from .core.type.exceptions import EarlyReturn, Tips


class GalgameBoxPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.ctx = context
        self.push_list: list[str] = []

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        await Services.initialize(self.config)

        self._get_push_list()
        await self._register_push_task()

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        await self._cancel_gal_event()
        await Services.get(Downloader).terminate()
        await Services.get(Http).terminate()
        await Services.get(Cache).terminate()

    @filter.command_group("旮旯", alias={"gal", "GAL"})
    async def gal_box(self, event: AstrMessageEvent):
        """Galgame百宝盒插件的主指令"""
        pass

    @gal_box.command("作品", alias={"游戏", "vn"})
    async def vn(self, event: AstrMessageEvent, keyword: str):
        """通过关键词查询作品"""
        try:
            yield await anext(Services.get(Vn).goooooooooo(event, keyword))
        except Exception as e:
            yield await anext(self._handle_command_exception(event, e))

    @gal_box.command("角色", alias={"人物", "character"})
    async def character(self, event: AstrMessageEvent, keyword: str):
        """通过关键词查询角色"""
        try:
            yield await anext(Services.get(Character).goooooooooo(event, keyword))
        except Exception as e:
            yield await anext(self._handle_command_exception(event, e))

    @gal_box.command("厂商", alias={"作者", "producer"})
    async def producer(self, event: AstrMessageEvent, keyword: str):
        """通过关键词查询厂商"""
        try:
            yield await anext(Services.get(Producer).goooooooooo(event, keyword))
        except Exception as e:
            yield await anext(self._handle_command_exception(event, e))

    @gal_box.command("ID", alias={"id"})
    async def vndb_id(self, event: AstrMessageEvent, keyword: str):
        """通过VNDB ID查询特定内容"""
        try:
            yield await anext(Services.get(VndbId).goooooooooo(event, keyword))
        except Exception as e:
            yield await anext(self._handle_command_exception(event, e))

    @gal_box.command("简讯", alias={"event"})
    async def gal_event(self, event: AstrMessageEvent, date: str = ""):
        """了解今日旮旯讯息，包括今天发售游戏与生日角色"""
        try:
            yield await anext(Services.get(Event).goooooooooo(event, date))
        except Exception as e:
            yield await anext(self._handle_command_exception(event, e))

    @gal_box.command("随机", alias={"random"})
    async def random(self, event: AstrMessageEvent):
        """通过TouchGal随机获取一部作品"""
        try:
            yield await anext(Services.get(Random).goooooooooo(event))
        except Exception as e:
            yield await anext(self._handle_command_exception(event, e))

    @gal_box.command("推荐", alias={"标签", "recommend"})
    async def recommend(self, event: AstrMessageEvent, tags: GreedyStr):
        """提供一个或多个标签，从TouchGal网站中获取推荐内容"""
        try:
            async for res in Services.get(Recommend).goooooooooo(event, tags):
                yield res
        except Exception as e:
            yield await anext(self._handle_command_exception(event, e))

    @gal_box.command("下载", alias={"资源", "download"})
    async def download(self, event: AstrMessageEvent, the_id: str):
        """优先通过VNDB ID、TouchGal ID，最后通过关键词搜索获取指定资源的下载链接"""
        try:
            async for res in Services.get(Download).goooooooooo(event, the_id):
                yield res
        except Exception as e:
            yield await anext(self._handle_command_exception(event, e))

    @gal_box.command("出处", alias={"识别", "find"})
    async def find(self, event: AstrMessageEvent, url: str = ""):
        """提供图片或者图片链接识别角色出处，可以先不填参数"""
        try:
            async for res in Services.get(Find).goooooooooo(event, url):
                yield res
        except Exception as e:
            yield await anext(self._handle_command_exception(event, e))

    async def _push_today(self):
        try:
            async for res in Services.get(EventTimed).goooooooooo():
                for group in self.push_list:
                    await self.ctx.send_message(group, MessageChain().url_image(res))
        except Exception as e:
            await anext(self._handle_command_exception(None, e))  # 无需等待

    async def _register_push_task(self):
        if not self.push_list:
            logger.warning("推送白名单为空，定时任务不会执行！")
            return

        schedule_time = self.config.get("scheduleSetting", {}).get("pushTime", "07:00")
        if ":" in schedule_time:
            hour, minute = map(int, schedule_time.split(":", 1))
        elif "：" in schedule_time:
            hour, minute = map(int, schedule_time.split("：", 1))
        else:
            logger.error("时间格式错误，定时任务不会执行！")
            return

        if 0 <= hour <= 23 and 0 <= minute <= 59:
            schedule_id = "event_timed"
            scheduler = self.ctx.cron_manager.scheduler

            scheduler.add_job(
                self._push_today,
                trigger=CronTrigger(hour=hour, minute=minute),
                id=schedule_id,
                replace_existing=True,
                misfire_grace_time=120,
            )
            logger.info(f"设置定时任务成功，将向{len(self.push_list)}个群聊推送内容！")

        else:
            logger.error("时间格式错误，定时任务不会执行！")
            return

    async def _cancel_gal_event(self):
        schedule_id = "event_timed"
        scheduler = self.ctx.cron_manager.scheduler
        if scheduler.get_job(schedule_id):
            scheduler.remove_job(schedule_id)

    def _get_push_list(self):
        ids = self.config.get("scheduleSetting", {}).get("pushList", [])

        def func(source: str):
            platform, group = source.split("-", 1)
            return MessageSession.from_str(f"{platform}:GroupMessage:{group}")

        self.push_list = list(map(func, ids))

    async def _handle_command_exception(
        self, event: AstrMessageEvent | None, e: Exception
    ):
        logger.error(str(e), exc_info=True)
        msg = "发生非预期异常！"
        if isinstance(e, Tips):
            if isinstance(e, EarlyReturn):
                return
            msg = str(e).split("：")[0]
        elif isinstance(e, RuntimeError) and "endpoints failed" in str(e):
            msg = "图片渲染失败！"

        if event is not None:
            yield event.chain_result(
                [Reply(id=event.message_obj.message_id), Plain(msg)]
            )
        else:
            for group in self.push_list:
                await self.ctx.send_message(group, MessageChain().message(msg))
