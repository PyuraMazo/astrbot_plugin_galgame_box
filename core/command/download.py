from astrbot.api import AstrBotConfig
from astrbot.api import message_components as comp
from astrbot.api.event import AstrMessageEvent
from astrbot.core.utils.session_waiter import (
    SessionController,
    session_waiter,
)

from ..type.exceptions import SessionTimeoutException
from ..type.inner_models import CommandType, bs64
from ..type.outer_models import ResourceResponse, TouchGalResponse
from ..utils import OnlySenderFilter
from .base_command import BaseCommand


class Download(BaseCommand):
    @classmethod
    async def initialize(cls, config: AstrBotConfig):
        await super().initialize(config)
        cls.session_dict: dict[str, int] = {}

        return cls()

    async def goooooooooo(self, event: AstrMessageEvent, value: str):
        if value.isdigit():
            touchgal_id = int(value)
        else:
            res, total = await self.touchgal.request_vn_by_search(
                CommandType.DOWNLOAD, value
            )
            if (
                len(value) > 1
                and value.startswith("v")
                and value[1:].isdigit()
                and total == 1
            ):
                touchgal_id = res[0].id
            else:
                images, texts = await self._build_search_select(res)

                tips = f"-未识别到ID，改为关键词搜索\n-从以下内容中选择一项\n-请在{self.session_timeout}s内回复输入对应编号"
                yield event.plain_result(tips)

                if event.get_platform_name() in self.support_forward:
                    n = []
                    for idx, (img, info) in enumerate(zip(images, texts), start=1):
                        node = comp.Node(
                            uin=event.get_self_id(),
                            content=[
                                comp.Plain(f"【{idx}】"),
                                comp.Image.fromBase64(img),
                                comp.Plain(info),
                            ],
                        )
                        n.append(node)
                    yield event.chain_result([comp.Nodes(n)])
                else:
                    t = []
                    for idx, (img, info) in enumerate(zip(images, texts), start=1):
                        t.append(comp.Plain(f"【{idx}】"))
                        t.append(comp.Image.fromBase64(img))
                        t.append(comp.Plain(info))
                    yield event.chain_result(t)

                @session_waiter(timeout=self.session_timeout)
                async def index_waiter(
                    controller: SessionController, sess_event: AstrMessageEvent
                ):
                    message = sess_event.message_str.strip()
                    accept = int(message) if message.isdigit() else None

                    if accept is not None and 0 < accept <= total:
                        self.session_dict[
                            event.get_group_id() + event.get_sender_id()
                        ] = accept - 1
                        controller.stop()
                        return
                    else:
                        invalid = "无效的选择，请重新输入。"
                        await sess_event.send(sess_event.plain_result(invalid))

                try:
                    await index_waiter(event, session_filter=OnlySenderFilter())
                    index = self.session_dict.pop(
                        event.get_group_id() + event.get_sender_id()
                    )
                    touchgal_id = res[index].id
                except TimeoutError:
                    raise SessionTimeoutException(CommandType.DOWNLOAD, value)

        resp = await self.touchgal.request_download(touchgal_id)
        resources = self._build_resources(resp)
        if event.get_platform_name() in self.support_forward:
            nodes = []
            for idx, resource in enumerate(resources, start=1):
                nodes.append(
                    comp.Node(uin=event.get_self_id(), content=[comp.Plain(resource)])
                )
                if idx % self.forward_limit == 0:
                    yield event.chain_result([comp.Nodes(nodes)])
                    nodes = []
                if idx == self.forward_limit and self.results_limit:
                    break
            if nodes:
                yield event.chain_result([comp.Nodes(nodes)])
        else:
            cut_sign = "\n----------\n"
            if self.results_limit:
                sub = resources[: self.results_limit]
                yield cut_sign.join(sub)
            else:
                plain = []
                for idx, text in enumerate(resources):
                    if idx == self.forward_limit:
                        yield event.plain_result(cut_sign.join(plain))
                    plain.append(text)
                if plain:
                    yield event.plain_result(cut_sign.join(plain))

    def _build_resources(self, res: list[ResourceResponse]):
        return ["\n".join(self.build_download(i)) for i in res]

    async def _build_search_select(
        self, res: list[TouchGalResponse]
    ) -> tuple[list[bs64], list[str]]:
        urls = []
        texts = []
        for r in res:
            urls.append(r.banner)
            texts.append("\n".join(self.build_search(r)))
        images = await self.build_images(urls, "touchgal", prefix=False)
        return images, texts
