import asyncio
from typing import Optional, Callable
from pathlib import Path

from astrbot.api import AstrBotConfig
from astrbot.api import message_components as comp
from astrbot.api.event import AstrMessageEvent
from astrbot.api.util import SessionController, session_waiter

from ..api.const import html_list, id2command
from ..api.exception import InvalidArgsException, CodeException, NoResultException, SessionTimeoutException
from ..api.model import AnimeTraceResponse
from ..api.type import CommandBody, CommandType, AnimeTraceModel
from ..builder import Builder, get_builder
from ..cache import Cache, get_cache
from ..html_handler import HTMLHandler, get_handler
from ..internet.vndb_request import get_vndb_request, VNDBRequest
from ..internet.touchgal_request import get_touchgal_request, TouchGalRequest
from ..internet.animetrace_request import get_animetrace_request, AnimeTreceRequest
from ..utils.file import File

class TaskLine:
    def __init__(self):
        self.resources_dir = Path(__file__).parent / '..' / '..' / 'resources'
        self.template_dir = self.resources_dir / 'template'
        self.session_data_storage = {}

        self.vndb_request: Optional[VNDBRequest] = None
        self.touchgal_request: Optional[TouchGalRequest] = None
        self.animetrace_request: Optional[AnimeTreceRequest] = None
        self.builder: Optional[Builder] = None
        self.html_handler: Optional[HTMLHandler] = None
        self.cache: Optional[Cache] = None

        self.task_map: Optional[dict[CommandType, Callable]] = None
        self.find_results: Optional[int] = None

    async def initialize(self, config: AstrBotConfig):
        self.vndb_request = get_vndb_request()
        self.touchgal_request = get_touchgal_request()
        self.animetrace_request = get_animetrace_request()
        self.builder = get_builder()
        self.html_handler = get_handler()
        self.cache = get_cache()

        await self.vndb_request.initialize(config)
        await self.touchgal_request.initialize(config)
        await self.animetrace_request.initialize(config)
        await self.builder.initialize(config)
        await self.html_handler.initialize()
        await self.cache.initialize(config)

        self.task_map: dict[CommandType, Callable] = {
            CommandType.VN: self._vn_task,
            CommandType.CHARACTER: self._cha_task,
            CommandType.PRODUCER: self._pro_task,
            CommandType.ID: self._id_task,
            CommandType.RANDOM: self._random_task,
            CommandType.DOWNLOAD: self._download_task,
            CommandType.FIND: self._find_task,
        }
        self.find_results = config.get('searchSetting', {}).get('findResults', 3)


    async def terminate(self):
        await self.vndb_request.terminate()
        await self.touchgal_request.terminate()
        await self.animetrace_request.terminate()
        await self.builder.terminate()
        await self.html_handler.terminate()
        await self.cache.terminate()


    async def run(self, cmd_body: CommandBody):
        cache = await self.cache.get_cache(cmd_body)
        if cache is not None:
            yield comp.Image.fromBytes(cache)
            return

        task = self.task_map[cmd_body.type]
        async for result in task(cmd_body):
            yield result

    async def _vn_task(self, cmd_body: CommandBody):
        rendered_html = self.template_dir / html_list[cmd_body.type.value]
        res = await self.vndb_request.request_by_vn(cmd_body.value)
        data = self.builder.build_options(cmd_body, res)
        tmpl = File.read_text(rendered_html)

        res = await asyncio.gather(tmpl, data)
        yield res


    async def _cha_task(self, cmd_body: CommandBody):
        rendered_html = self.template_dir / html_list[cmd_body.type.value]
        res = await self.vndb_request.request_by_character(cmd_body.value)
        data = self.builder.build_options(cmd_body, res)
        tmpl = File.read_text(rendered_html)

        res = await asyncio.gather(tmpl, data)
        yield res

    async def _pro_task(self, cmd_body: CommandBody):
        rendered_html = self.template_dir / html_list[cmd_body.type.value]
        pro, vns = await self.vndb_request.request_by_producer(cmd_body.value)
        data = self.builder.build_options(cmd_body, pro, vns=vns)
        tmpl = File.read_text(rendered_html)

        res = await asyncio.gather(tmpl, data)
        yield res


    async def _id_task(self, cmd_body: CommandBody):
        if cmd_body.value[0] not in id2command.keys():
            raise InvalidArgsException(cmd_body)

        actual_type_value = id2command[cmd_body.value[0]]
        rendered_html = self.template_dir / html_list[actual_type_value]
        res = await self.vndb_request.request_by_id(cmd_body.type, cmd_body.value)

        data = self.builder.build_options(cmd_body, res[0], vns=res[1]) \
            if actual_type_value == CommandType.PRODUCER.value \
            else self.builder.build_options(cmd_body, res)

        tmpl = File.read_text(rendered_html)

        res = await asyncio.gather(tmpl, data)
        yield res


    async def _random_task(self, cmd_body: CommandBody):
        rendered_html = self.template_dir / html_list[cmd_body.type.value]
        unique_id = await self.touchgal_request.request_random()
        text = await self.touchgal_request.request_html(unique_id)
        details = await self.html_handler.handle_touchgal_details(text)
        resp = (await self.touchgal_request.request_vn_by_search(details.vndb_id))[0]
        data = self.builder.build_options(cmd_body, resp, details=details)
        tmpl = File.read_text(rendered_html)

        res = await asyncio.gather(tmpl, data)
        yield res

    async def _download_task(self, cmd_body: CommandBody):
        keyword = cmd_body.value
        touchgal_id: int
        if keyword.isdigit():
            touchgal_id = int(keyword)
        else:
            res, total = await self.touchgal_request.request_vn_by_search(keyword)
            if total == 0:
                raise NoResultException(cmd_body)
            elif len(keyword) > 1 and keyword.startswith('v') and keyword[1:].isdigit() and total == 1:
                touchgal_id = res[0].id
            else:
                cmd_body.type = CommandType.SELECT
                msgs = await self.builder.build_options(cmd_body, res)
                event = cmd_body.event
                content = []
                for idx, msg in enumerate(msgs, start=1):
                    node = comp.Node(uin=event.get_self_id(),
                                content=[
                                    comp.Plain(f'【{idx}】'),
                                    comp.Image.fromBase64(msg[0]),
                                    comp.Plain(msg[1])
                                ])
                    content.append(node)

                tips = '未识别到ID，改为关键词搜索\n从以下内容中选择一项\n30s内回复输入对应数字获取相应资源'
                yield event.plain_result(tips)
                yield event.chain_result([comp.Nodes(content)])
                # 注册进session_data_storage
                self.session_data_storage[event.get_group_id() + event.get_sender_id()] = ''

                @session_waiter(timeout=30)
                async def index_waiter(controller: SessionController, sess_event: AstrMessageEvent):
                    # 可以用过滤器代替
                    if self.session_data_storage.get(sess_event.get_group_id() + sess_event.get_sender_id(), None) is not None:
                        message = sess_event.message_str
                        accept = int(message) if message.isdigit() else None

                        if accept and 0 < accept <= total:
                            controller.stop()
                            self.session_data_storage[sess_event.get_sender_id()] = accept - 1
                            return
                        else:
                            invalid = '无效的消息，请重新输入'
                            result = sess_event.make_result()
                            result.chain = [comp.Plain(invalid)]
                            await sess_event.send(result)

                try:
                    await index_waiter(event)
                    index = self.session_data_storage.pop(event.get_group_id() + event.get_sender_id())
                    touchgal_id = res[index].id
                    cmd_body.type = CommandType.DOWNLOAD
                except TimeoutError:
                    raise SessionTimeoutException(cmd_body)
                finally:
                    self.session_data_storage.pop(event.get_group_id() + event.get_sender_id(), '')


        resp = await self.touchgal_request.request_download(touchgal_id)
        res = await self.builder.build_options(cmd_body, resp)
        yield res



    async def _find_task(self, cmd_body: CommandBody):
        event = cmd_body.event

        no_args = True
        if cmd_body.value and cmd_body.value.startswith('http'):
            no_args = False
        else:
            for msg in event.message_obj.message:
                if isinstance(msg, comp.Image):
                    cmd_body.value = msg.url
                    no_args = False
                    break

        if no_args:
            tips = '未检测到有效的指令参数\n改为从下一条消息中获取\n在30s内发送一张图片'
            yield event.plain_result(tips)
            # 注册进session_data_storage
            self.session_data_storage[event.get_group_id() + event.get_sender_id()] = ''

            @session_waiter(timeout=30)
            async def image_waiter(controller: SessionController, sess_event: AstrMessageEvent):
                if self.session_data_storage.get(sess_event.get_group_id() + sess_event.get_sender_id(), None) is not None:
                    message = sess_event.message_obj.message
                    _url = ''
                    for _msg in message:
                        if isinstance(_msg, comp.Image):
                            _url = _msg.url
                            break
                    if not _url:
                        invalid = '无效的图片，请重新发送'
                        result = event.make_result()
                        result.chain = [comp.Plain(invalid)]
                        await event.send(result)
                    else:
                        self.session_data_storage[sess_event.get_group_id() + sess_event.get_sender_id()] = _url
                        controller.stop()
            try:
                await image_waiter(event)
                cmd_body.value = self.session_data_storage.pop(event.get_group_id() + event.get_sender_id())
            except TimeoutError:
                raise SessionTimeoutException(cmd_body)
            finally:
                self.session_data_storage.pop(event.get_group_id() + event.get_sender_id(), '')

        model = AnimeTraceModel.Profession
        trace_resp: AnimeTraceResponse
        try:
            trace_resp = await self.animetrace_request.request_find(cmd_body.value, model)
        except CodeException:
            model = AnimeTraceModel.Common
            trace_resp = await self.animetrace_request.request_find(cmd_body.value, model)

        if not trace_resp.data:
            raise NoResultException(cmd_body)

        vndb_resp = []
        for i in trace_resp.data:
            index = 1
            block = []
            for j in i.character:
                block.append(self.vndb_request.request_by_find(j.character, j.work))
                if index < len(i.character) and index < self.find_results:
                    index += 1
                else:
                    break
            vndb_resp.append(await asyncio.gather(*block))

        rendered_html = self.template_dir / html_list[cmd_body.type.value]
        data = self.builder.build_options(
            cmd_body,
            trace_resp,
            vndb_resp=vndb_resp,
            image=cmd_body.value,
            count=len(trace_resp.data),
            model=model
        )
        tmpl = File.read_text(rendered_html)

        res = await asyncio.gather(tmpl, data)
        yield res



_task_line: Optional[TaskLine] = None
def get_task_line():
    global _task_line
    if _task_line is None:
        _task_line = TaskLine()
    return _task_line
