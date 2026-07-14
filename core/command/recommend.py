import asyncio

from astrbot.api import AstrBotConfig, html_renderer
from astrbot.api.event import AstrMessageEvent
from astrbot.core.utils.session_waiter import (
    SessionController,
    session_waiter,
)

from ..services import Services
from ..type.exceptions import EarlyReturn, SessionTimeoutException
from ..type.inner_models import CommandType, RecommendCache, template_list
from ..type.outer_models import TouchGalResponse
from ..utils import OnlySenderFilter
from . import Random
from .base_command import BaseCommand


class Recommend(BaseCommand):
    @classmethod
    async def initialize(cls, config: AstrBotConfig):
        await super().initialize(config)
        cls.random = Services.get(Random)

        cls.recommend_cache = config.get("recommendSetting", {}).get(
            "recommendCache", 5
        )

        cls.session_cache_dict: dict[str, RecommendCache] = {}
        cls.count_per_search = cls.recommend_cache * 3

        return cls()

    async def goooooooooo(self, event: AstrMessageEvent, value: str):
        session_id = event.get_group_id() + event.get_sender_id()
        resp, total = await self.touchgal.request_vn_by_search(
            CommandType.RECOMMEND,
            value,
            searchInAlias=False,
            searchInTag=True,
            limit=self.count_per_search,
            page=1,
        )

        task = RecommendCache(
            tasks_remaining_queue=resp,
            ready_queue=[],
            total=total,
            handling=0,
            ready_signal=asyncio.Event(),
            use_signal=asyncio.Event(),
            stop_signal=asyncio.Event(),
        )
        self.session_cache_dict[session_id] = task

        asyncio.create_task(self._make_machine(session_id, value))

        await asyncio.wait(
            [
                asyncio.ensure_future(task.ready_signal.wait()),
                asyncio.ensure_future(task.stop_signal.wait()),
            ],
            return_when=asyncio.FIRST_COMPLETED,
        )
        if task.stop_signal.is_set():
            msg = task.stop_info
            yield event.image_result(msg)
            self.session_cache_dict.pop(session_id, None)
            raise EarlyReturn(msg)

        url = task.ready_queue.pop(0)
        yield event.image_result(url)
        tips = f"-如果需要以同样要求继续获取作品，请输入文本【换一个】\n-如果不再需要，请输入文本【结束】以结束此次会话\n-后续同理\n-默认等待时间：{self.session_timeout}s"
        yield event.plain_result(tips)

        alter = "换一个"
        end = "结束"

        @session_waiter(timeout=self.session_timeout)
        async def select_waiter(
            controller: SessionController, sess_event: AstrMessageEvent
        ):
            # 协程切换最大等待时间30s
            controller.keep(60, True)
            if not task.stop_signal.is_set():
                message = sess_event.message_str.strip()
                if message == alter:
                    if not task.ready_queue:
                        if task.handling < task.total:
                            await asyncio.wait(
                                [
                                    asyncio.ensure_future(task.ready_signal.wait()),
                                    asyncio.ensure_future(task.stop_signal.wait()),
                                ],
                                return_when=asyncio.FIRST_COMPLETED,
                            )
                        else:
                            task.stop_info = "没有更多内容了，自动关闭会话。"
                            task.stop_signal.set()

                    if not task.stop_signal.is_set():
                        task.use_signal.clear()

                        _url = task.ready_queue.pop(0)
                        _image = sess_event.image_result(_url)
                        await sess_event.send(_image)

                        task.use_signal.set()
                        controller.keep(self.session_timeout, True)

                elif message == end:
                    task.stop_info = "成功关闭此次会话。"
                    task.stop_signal.set()

            if task.stop_signal.is_set():
                self.session_cache_dict.pop(session_id, None)
                await sess_event.send(sess_event.plain_result(task.stop_info))
                controller.stop()

        try:
            await select_waiter(event, session_filter=OnlySenderFilter())
        except TimeoutError:
            raise SessionTimeoutException(CommandType.RECOMMEND, value)
        finally:
            task.stop_signal.set()

    async def _make_machine(self, session_id: str, value: str):
        task = self.session_cache_dict[session_id]

        while not task.stop_signal.is_set():
            if task.handling == task.total:
                return

            if len(task.ready_queue) > self.recommend_cache:
                # 大于缓存数量，等待消耗信号或停止信号
                done, _ = await asyncio.wait(
                    [
                        asyncio.ensure_future(task.use_signal.wait()),
                        asyncio.ensure_future(task.stop_signal.wait()),
                    ],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if task.stop_signal.is_set():
                    break
                task.use_signal.clear()

            if not task.tasks_remaining_queue:
                resp, _ = await self.touchgal.request_vn_by_search(
                    CommandType.RECOMMEND,
                    value,
                    searchInAlias=False,
                    searchInTag=True,
                    limit=self.count_per_search,
                    page=task.handling // self.count_per_search + 1,
                )
                task.tasks_remaining_queue = resp

            # 重置准备信号
            task.ready_signal.clear()

            current = task.tasks_remaining_queue.pop(0)
            task.handling += 1
            try:
                url = await self._core_handler(current)
                task.ready_queue.append(url)

                task.ready_signal.set()
            except Exception as e:
                task.stop_info = str(e).split("：")[0]
                task.stop_signal.set()
                return
        else:
            self.session_cache_dict.pop(session_id, None)

    async def _core_handler(self, res: TouchGalResponse):
        data = await self.random.build_html(
            res.uniqueId, cmd_type=CommandType.RECOMMEND, resp=res
        )
        tmpl = self.templates[template_list[CommandType.RANDOM.value]]

        return await html_renderer.render_custom_template(
            tmpl, data, True, self.render_options
        )
