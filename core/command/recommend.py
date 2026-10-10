import asyncio

from astrbot.api import AstrBotConfig, html_renderer
from astrbot.api.event import AstrMessageEvent
from astrbot.core.utils.session_waiter import (
    SessionController,
    session_waiter,
)

from ..type.bangumi_models import BangumiSubjectResponse
from ..type.exceptions import EarlyReturn, SessionTimeoutException, Tips
from ..type.inner_models import CommandType, RecommendCache, template_list
from ..type.vndb_models import VNDBVnResponse
from ..utils import OnlySenderFilter
from .base_command import BaseCommand


class Recommend(BaseCommand):
    @classmethod
    async def initialize(cls, config: AstrBotConfig):
        await super().initialize(config)

        cls.recommend_cache = config.get("recommendSetting", {}).get(
            "recommendCache", 5
        )
        cls.nsfw_enable = config.get("safetySetting", {}).get("enableNSFW", False)

        cls.session_cache_dict: dict[str, RecommendCache] = {}
        cls.count_per_search = cls.recommend_cache * 2

        return cls()

    async def goooooooooo(self, event: AstrMessageEvent, tags: list[str]):
        session_id = event.get_group_id() + event.get_sender_id()

        vns, total = await self._request_once(tags, 0)
        task = RecommendCache(
            tasks_remaining_queue=vns,
            ready_queue=[],
            total=total,
            handling=0,
            ready_signal=asyncio.Event(),
            use_signal=asyncio.Event(),
            stop_signal=asyncio.Event(),
        )
        self.session_cache_dict[session_id] = task

        asyncio.create_task(self._make_machine(session_id, tags))

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
            raise SessionTimeoutException(CommandType.RECOMMEND, str(tags))
        finally:
            task.stop_signal.set()

    async def build(
        self, bangumi_vn: BangumiSubjectResponse, vndb_vn: VNDBVnResponse | None
    ):
        previews = []
        if vndb_vn:
            main_image = await self.read_or_download_image("vndb", vndb_vn.image.url)
            info = self.build_vn(vndb_vn)
            bangumi_info = self.build_bangumi_info(bangumi_vn, True)
            info += bangumi_info
            subtitle = vndb_vn.alttitle or vndb_vn.title

            if vndb_vn.screenshots:
                count = 0
                for ss in vndb_vn.screenshots:
                    if ss.violence > 0.2 or ss.sexual > 0.2:
                        if self.nsfw_enable:
                            count += 1
                            previews.append(ss.url)
                    else:
                        count += 1
                        previews.append(ss.url)
                    if count > 3:
                        break
        else:
            main_image = (
                await self.read_or_download_image(
                    "bangumi", bangumi_vn.image, use_proxy=True
                )
                if bangumi_vn.image
                else self.err_image
            )
            info = self.build_bangumi_info(bangumi_vn)
            subtitle = bangumi_vn.name

        desc = bangumi_vn.summary.replace("\r\n", "<br>") if bangumi_vn.summary else ""

        return {
            "font": self.font,
            "bg": self.bg,
            "subtitle": subtitle,
            "main_image": main_image,
            "info": info,
            "desc": desc,
            "previews": previews,
        }

    async def _make_machine(self, session_id: str, tags: list[str]):
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
                vns, _ = self._request_once(
                    tags, task.handling // self.count_per_search + 1
                )
                task.tasks_remaining_queue = vns

            # 重置准备信号
            task.ready_signal.clear()

            bangumi_vn, vndb_vn = task.tasks_remaining_queue.pop(0)
            task.handling += 1
            try:
                url = await self._core_handler(bangumi_vn, vndb_vn)
                task.ready_queue.append(url)

                task.ready_signal.set()
            except Exception as e:
                task.stop_info = str(e).split("：")[0]
                task.stop_signal.set()
                return
        else:
            self.session_cache_dict.pop(session_id, None)

    async def _core_handler(
        self, bangumi_vn: BangumiSubjectResponse, vndb_vn: VNDBVnResponse
    ):
        data = await self.build(bangumi_vn, vndb_vn)
        tmpl = self.templates[template_list[CommandType.RANDOM.value]]

        return await html_renderer.render_custom_template(
            tmpl, data, True, self.render_options
        )

    async def _request_once(
        self, tags: list[str], offset: int
    ) -> tuple[list[tuple[BangumiSubjectResponse, VNDBVnResponse | None]], int]:
        bangumi_vns, total = await self.bangumi.request_by_tags(
            CommandType.RECOMMEND, tags, limit=self.count_per_search, offset=offset
        )
        vndb_vns: list[VNDBVnResponse | None] = []
        for idx, vn in enumerate(bangumi_vns):
            for info in vn.infobox:
                if (
                    info is not None
                    and info.key == "链接"
                    and isinstance(info.value, list)
                ):
                    for kv in info.value:
                        vn_id = kv.get("v", "./.").split("/")[-1]
                        if vn_id and kv.get("k", "").upper() == "VNDB":
                            try:
                                vndb_vn: list[
                                    VNDBVnResponse
                                ] = await self.vndb.request_by_id(CommandType.VN, vn_id)
                                vndb_vns.append(vndb_vn[0])
                            except Tips:
                                vndb_vns.append(None)
                            finally:
                                break
                    else:
                        vndb_vns.append(None)
                    break
            else:
                vndb_vns.append(None)

        vns: list[tuple[BangumiSubjectResponse, VNDBVnResponse | None]] = [
            (b, v) for b, v in zip(bangumi_vns, vndb_vns)
        ]
        return vns, total
