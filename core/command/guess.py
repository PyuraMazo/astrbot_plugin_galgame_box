import asyncio
from datetime import datetime

from astrbot.api import AstrBotConfig, html_renderer
from astrbot.api.event import AstrMessageEvent
from astrbot.core.utils.session_waiter import SessionController, session_waiter

from ..type.bangumi_models import BangumiSubjectResponse
from ..type.exceptions import (
    InvalidArgsException,
    NoResultException,
)
from ..type.inner_models import CommandType, GuessRecord, guess_degree, template_list
from ..type.vndb_models import VNDBVnResponse
from ..utils import OnlySenderFilter
from . import Random
from .base_command import BaseCommand


class Guess(BaseCommand):
    @classmethod
    async def initialize(cls, config: AstrBotConfig):
        from ..services import Services

        await super().initialize(config)
        cls.random = Services.get(Random)

        guess_setting = config.get("guessSetting")
        cls.guess_timeout = guess_setting.get("answerLimit", 5)
        cls.guess_round = guess_setting.get("queryRound", 8)
        cls.wake_sign = guess_setting.get("answerWake", "：")
        cls.is_shared = guess_setting.get("sharedGuess", True)
        return cls()

    async def goooooooooo(self, event: AstrMessageEvent, degree: int):
        if degree is not None and not (1 <= degree <= 4):
            raise InvalidArgsException(CommandType.GUESS, str(degree))

        target: VNDBVnResponse | None = None
        bangumi_info: list[BangumiSubjectResponse] = []

        while not bangumi_info:
            try:
                target = await self.vndb.request_random(
                    least_rating=guess_degree[degree]
                )
                bangumi_info = await self.bangumi.request_by_vndb_id(
                    CommandType.GUESS, target.alttitle or target.title, target.id
                )
            except NoResultException:
                pass

        data = await self.random.build(target, bangumi_info[0])
        tmpl = self.templates[template_list[CommandType.GUESS.value]]
        async_url = asyncio.create_task(
            html_renderer.render_custom_template(tmpl, data, True, self.render_options)
        )

        @session_waiter(timeout=self.guess_timeout * 60)
        async def guess_waiter(
            controller: SessionController, sess_event: AstrMessageEvent
        ):
            message = sess_event.message_str.strip()
            if message.startswith(self.wake_sign):
                message = sess_event.message_str.lstrip(self.wake_sign)
                try:
                    if message == "放弃":
                        await sess_event.send(sess_event.plain_result("答案揭晓..."))
                        await sess_event.send(sess_event.image_result(await async_url))
                        controller.stop()
                        return

                    res = await self.vndb.request_by_vn(message)
                    ids = [vn.id for vn in res]
                    if target.id in ids:
                        await sess_event.send(sess_event.plain_result("回答正确！"))
                        await sess_event.send(sess_event.image_result(await async_url))
                        controller.stop()
                    else:
                        record = self._build_record(res[0])
                        records.append(record)
                        resp = self._build_plus_info(answer_info, record)
                        resp.insert(0, f"【第{len(records)}/{self.guess_round}轮尝试】")
                        await sess_event.send(sess_event.plain_result("\n".join(resp)))
                        if len(records) == 8:
                            await sess_event.send(
                                sess_event.plain_result("次数耗尽！答案揭晓...")
                            )
                            await sess_event.send(
                                sess_event.image_result(await async_url)
                            )
                            controller.stop()
                        else:
                            controller.keep()
                except NoResultException:
                    await sess_event.send(sess_event.plain_result("未搜索到有效结果。"))

        try:
            try:
                answer_info = self._build_record(target)
                records: list[GuessRecord] = []
                yield event.plain_result(
                    f"开始你的首轮查询，总限时{self.guess_timeout}分钟。\n请以「{self.wake_sign}」开头输入一个作品名以查询。\n可以使用「{self.wake_sign}放弃」指令放弃。"
                )
                await guess_waiter(
                    event,
                    session_filter=OnlySenderFilter() if not self.is_shared else None,
                )
            except TimeoutError:
                yield event.plain_result("时间到！答案自动揭晓...")
                yield event.image_result(await async_url)
        except RuntimeError as e:
            if "endpoints failed" in str(e):
                yield event.plain_result(
                    f"图片渲染失败...\n答案是（{target.id}）「{target.title}」。"
                )
            else:
                raise

    def _build_record(self, vn: VNDBVnResponse) -> GuessRecord:
        record = GuessRecord(title=vn.title)
        if vn.released:
            record.date = datetime.fromisoformat(vn.released)
        if vn.rating:
            record.rating = vn.rating
        if vn.length_minutes:
            record.length = round(vn.length_minutes / 60, 1)
        if vn.developers:
            record.developers = {i.name or i.original for i in vn.developers}
        if vn.tags:
            record.tags = {i.name for i in vn.tags[:3] if i}
        if vn.platforms:
            record.platforms = set(vn.platforms)
        return record

    def _build_plus_info(
        self, target: GuessRecord, unchecked_record: GuessRecord
    ) -> list[str]:
        res = [f"游戏标题: {unchecked_record.title}"]
        if target.date:
            res.append(self._compare("发售日期: ", target.date, unchecked_record.date))
        if target.rating:
            res.append(
                self._compare("游戏评分: ", target.rating, unchecked_record.rating)
            )
        if target.length:
            res.append(
                self._compare(
                    "文本长度: ",
                    target.length,
                    unchecked_record.length,
                    lambda length: f"{length}h",
                )
            )
        if target.developers:
            res.append(
                self._compare(
                    "制作厂商: ", target.developers, unchecked_record.developers
                )
            )
        if target.tags:
            res.append(self._compare("游戏标签: ", target.tags, unchecked_record.tags))
        if target.platforms:
            res.append(
                self._compare(
                    "支持平台: ", target.platforms, unchecked_record.platforms
                )
            )
        return res

    def _compare(
        self,
        tip_str: str,
        target: float | set | datetime,
        current: float | set | datetime | None,
        str_factory=None,
    ) -> str:
        if isinstance(target, float):
            if current is not None:
                if current < target:
                    sign = "↑"
                elif current > target:
                    sign = "↓"
                else:
                    sign = "√"
                return (
                    f"{tip_str}{current}({sign})"
                    if str_factory is None
                    else f"{tip_str}{str_factory(current)}({sign})"
                )
            else:
                return f"{tip_str}未知"
        elif isinstance(target, set):
            if current is not None:
                leaving = len(current - target)
                source = len(current)
                if leaving == 0:
                    sign = "√"
                elif leaving < source:
                    sign = "≈"
                else:
                    sign = "×"
                return f"{tip_str}{'、'.join(current)}({sign})"
            else:
                return f"{tip_str}未知"
        elif isinstance(target, datetime):
            if current is not None:
                return self._compare(
                    tip_str,
                    target.timestamp(),
                    current.timestamp(),
                    lambda stamp: datetime.fromtimestamp(stamp).strftime("%Y-%m-%d"),
                )
            else:
                return f"{tip_str}未知"
        else:
            raise NotImplementedError
