import asyncio
from typing import Optional, Callable
from pathlib import Path
from datetime import datetime

from astrbot.api import AstrBotConfig, html_renderer
from astrbot.api import message_components as comp
from astrbot.api.event import AstrMessageEvent
from astrbot.core.utils.session_waiter import (
    session_waiter,
    SessionFilter,
    SessionController
)

from ..api.const import html_list, id2command
from ..api.exception import InvalidArgsException, CodeException, NoResultException, SessionTimeoutException, \
    HasBoundException, ArgsOrNullException
from ..api.model import AnimeTraceResponse, TouchGalResponse
from ..api.type import CommandBody, CommandType, AnimeTraceModel, SelectInfo, SteamData, SteamVnsInfo
from ..builder import Builder, get_builder
from ..cache import Cache, get_cache
from ..html_handler import HTMLHandler, get_html_handler
from ..internet.downloader import get_downloader, Downloader
from ..internet.vndb_request import get_vndb_request, VNDBRequest
from ..internet.touchgal_request import get_touchgal_request, TouchGalRequest
from ..internet.animetrace_request import get_animetrace_request, AnimeTreceRequest
from ..internet.steam_request import get_steam_request, SteamRequest
from ..data_handler import get_data_handler, DataHandler
from ..utils.file import File



class OnlySenderFilter(SessionFilter):
    def filter(self, event: AstrMessageEvent) -> str:
        return event.get_sender_id()


class TaskLine:
    def __init__(self):
        self.resources_dir = Path(__file__).parent / '..' / '..' / 'resources'
        self.template_dir = self.resources_dir / 'template'
        self.session_data_storage = {}
        self.render_options = {
            'type': 'jpeg',
            'quality': 100
        }

        self.vndb_request: Optional[VNDBRequest] = None
        self.touchgal_request: Optional[TouchGalRequest] = None
        self.animetrace_request: Optional[AnimeTreceRequest] = None
        self.steam_request: Optional[SteamRequest] = None
        self.builder: Optional[Builder] = None
        self.html_handler: Optional[HTMLHandler] = None
        self.cache: Optional[Cache] = None
        self.downloader: Optional[Downloader] = None
        self.data_handler: Optional[DataHandler] = None


        self.task_map: Optional[dict[CommandType, Callable]] = None
        self.find_results: Optional[int] = None
        self.session_timeout: Optional[int] = None
        self.recommend_cache: Optional[int] = None
        self.update_interval: Optional[float] = None

    async def initialize(self, config: AstrBotConfig):
        self.vndb_request = get_vndb_request()
        self.touchgal_request = get_touchgal_request()
        self.animetrace_request = get_animetrace_request()
        self.steam_request = get_steam_request()
        self.builder = get_builder()
        self.html_handler = get_html_handler()
        self.cache = get_cache()
        self.downloader = get_downloader()
        self.data_handler = get_data_handler()

        await self.vndb_request.initialize(config)
        await self.touchgal_request.initialize(config)
        await self.animetrace_request.initialize(config)
        await self.steam_request.initialize(config)
        await self.builder.initialize(config)
        await self.html_handler.initialize()
        await self.cache.initialize(config)
        await self.downloader.initialize(config)
        await self.data_handler.initialize(config)

        self.task_map: dict[CommandType, Callable] = {
            CommandType.VN: self._vn_task,
            CommandType.CHARACTER: self._cha_task,
            CommandType.PRODUCER: self._pro_task,
            CommandType.ID: self._id_task,
            CommandType.RANDOM: self._random_task,
            CommandType.DOWNLOAD: self._download_task,
            CommandType.FIND: self._find_task,
            CommandType.RECOMMEND: self._recommend_task,
            CommandType.BIND: self._bind_task,
            CommandType.PUZZLE: self._puzzle_task
        }
        search_setting = config.get('searchSetting', {})
        self.find_results = search_setting.get('findResults', 3)
        self.session_timeout = search_setting.get('sessionTimeout', 30)
        self.recommend_cache = search_setting.get('recommendCache', 3)
        self.update_interval = search_setting.get('updateInterval', 24)


    async def terminate(self):
        await self.vndb_request.terminate()
        await self.touchgal_request.terminate()
        await self.animetrace_request.terminate()
        await self.steam_request.terminate()
        await self.builder.terminate()
        await self.html_handler.terminate()
        await self.cache.terminate()
        await self.downloader.terminate()
        await self.data_handler.terminate()



    async def run(self, cmd_body: CommandBody):
        cache = await self.cache.get_cache(cmd_body)
        if cache is not None:
            yield cmd_body.event.chain_result([comp.Image.fromBytes(cache)])
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
        url = await html_renderer.render_custom_template(res[0], res[1].model_dump(), True, self.render_options)
        await self.cache.store_image(cmd_body, await self.downloader.download_once(url))
        yield cmd_body.event.image_result(url)


    async def _cha_task(self, cmd_body: CommandBody):
        rendered_html = self.template_dir / html_list[cmd_body.type.value]
        res = await self.vndb_request.request_by_character(cmd_body.value)
        data = self.builder.build_options(cmd_body, res)
        tmpl = File.read_text(rendered_html)

        res = await asyncio.gather(tmpl, data)
        url = await html_renderer.render_custom_template(res[0], res[1].model_dump(), True, self.render_options)
        await self.cache.store_image(cmd_body, await self.downloader.download_once(url))
        yield cmd_body.event.image_result(url)

    async def _pro_task(self, cmd_body: CommandBody):
        rendered_html = self.template_dir / html_list[cmd_body.type.value]
        pro, vns = await self.vndb_request.request_by_producer(cmd_body.value)
        data = self.builder.build_options(cmd_body, pro, vns=vns)
        tmpl = File.read_text(rendered_html)

        res = await asyncio.gather(tmpl, data)
        url = await html_renderer.render_custom_template(res[0], res[1].model_dump(), True, self.render_options)
        await self.cache.store_image(cmd_body, await self.downloader.download_once(url))
        yield cmd_body.event.image_result(url)


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
        url = await html_renderer.render_custom_template(res[0], res[1].model_dump(), True, self.render_options)
        await self.cache.store_image(cmd_body, await self.downloader.download_once(url))
        yield cmd_body.event.image_result(url)


    async def _random_task(self, cmd_body: CommandBody):
        rendered_html = self.template_dir / html_list[cmd_body.type.value]
        unique_id = await self.touchgal_request.request_random()
        text = await self.touchgal_request.request_html(unique_id)
        details = await self.html_handler.handle_touchgal_details(text)

        resp = (await self.touchgal_request.request_vn_by_search(details.vndb_id or details.title))[0]

        data = self.builder.build_options(cmd_body, resp, details=[details])
        tmpl = File.read_text(rendered_html)

        res = await asyncio.gather(tmpl, data)
        url = await html_renderer.render_custom_template(res[0], res[1].model_dump(), True, self.render_options)
        yield cmd_body.event.image_result(url)

    async def _download_task(self, cmd_body: CommandBody):
        event = cmd_body.event
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
                content = []
                for idx, msg in enumerate(msgs, start=1):
                    node = comp.Node(uin=event.get_self_id(),
                                content=[
                                    comp.Plain(f'【{idx}】'),
                                    comp.Image.fromBase64(msg[0]),
                                    comp.Plain(msg[1])
                                ])
                    content.append(node)

                tips = f'-未识别到ID，改为关键词搜索\n-从以下内容中选择一项\n-请在{self.session_timeout}s内回复输入对应编号'
                yield event.plain_result(tips)
                yield event.chain_result([comp.Nodes(content)])

                @session_waiter(timeout=self.session_timeout)
                async def index_waiter(controller: SessionController, sess_event: AstrMessageEvent):
                    message = sess_event.message_str
                    accept = int(message) if message.isdigit() else None

                    if accept and 0 < accept <= total:
                        self.session_data_storage[event.get_group_id() + event.get_sender_id()] = accept - 1
                        controller.stop()
                        return
                    else:
                        invalid = '无效的选择，请重新输入'
                        await sess_event.send(sess_event.plain_result(invalid))

                try:
                    await index_waiter(event, session_filter=OnlySenderFilter())
                    index = self.session_data_storage.pop(event.get_group_id() + event.get_sender_id())
                    touchgal_id = res[index].id
                    cmd_body.type = CommandType.DOWNLOAD
                except TimeoutError:
                    raise SessionTimeoutException(cmd_body)


        resp = await self.touchgal_request.request_download(touchgal_id)
        msg_arr: list[tuple[str, str]] = await self.builder.build_options(cmd_body, resp)
        nodes = [comp.Node(uin=event.get_self_id(), content=[comp.Plain(msg[1])]) for msg in msg_arr]
        yield event.chain_result([comp.Nodes(nodes)])


    async def _find_task(self, cmd_body: CommandBody):
        event = cmd_body.event
        for i in event.message_obj.message:
            if isinstance(i, comp.Reply):
                cmd_body.value = self._get_chain_image(i.chain)
                break

        if not cmd_body.value:
            tips = f'-未检测到有效的指令参数\n-改为从下一条消息中获取\n-请在{self.session_timeout}s内发送一张图片'
            yield event.plain_result(tips)

            @session_waiter(timeout=self.session_timeout)
            async def image_waiter(controller: SessionController, sess_event: AstrMessageEvent):
                message = sess_event.message_obj.message
                _url = self._get_chain_image(message)

                if not _url:
                    invalid = '未解析到图片，请重新发送'
                    await sess_event.send(sess_event.plain_result(invalid))
                else:
                    self.session_data_storage[sess_event.get_group_id() + sess_event.get_sender_id()] = _url
                    controller.stop()

            try:
                await image_waiter(event, session_filter=OnlySenderFilter())
                cmd_body.value = self.session_data_storage.pop(event.get_group_id() + event.get_sender_id())
            except TimeoutError:
                raise SessionTimeoutException(cmd_body)


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
        url = await html_renderer.render_custom_template(res[0], res[1].model_dump(), True, self.render_options)
        yield cmd_body.event.image_result(url)


    async def _recommend_task(self, cmd_body: CommandBody, **kwargs):
        event = cmd_body.event
        id = event.get_group_id() + event.get_sender_id()
        resp, total = await self.touchgal_request.request_vn_by_search(
            cmd_body.value,
            searchInAlias=False,
            searchInTag=True,
            limit=self.recommend_cache,
            page=kwargs.get('page', 1)
        )
        if total == 0:
            raise NoResultException(cmd_body)

        if not kwargs.get('only_data', False):
            # 此分支只由最外层进入一次
            tmpl, data = await self._recommend_subtask(cmd_body, resp)
            cache_body = SelectInfo(
                cmd_body=cmd_body,
                cache=data,
                current=1,
                total=total,
                tmpl=tmpl
            )
            url = await html_renderer.render_custom_template(
                cache_body.tmpl,
                cache_body.cache.pop(0).model_dump(),
                True,
                self.render_options
            )
            yield event.image_result(url)
            self.session_data_storage[id] = cache_body

            tips = '-如果需要以同样要求继续获取作品，请输入文本【换一个】\n-如果不再需要，请输入文本【结束】以结束此次会话\n-后续同理\n-默认等待时间：2分钟'
            yield event.plain_result(tips)

            @session_waiter(timeout=120)
            async def select_waiter(controller: SessionController, sess_event: AstrMessageEvent):
                controller.keep(120, True)
                alter = '换一个'
                end = '结束'
                _id = sess_event.get_group_id() + sess_event.get_sender_id()
                message = sess_event.message_str
                if message == alter:
                    body: SelectInfo = self.session_data_storage[_id]

                    if not (body.cache or body.ready):
                        raise NoResultException(cmd_body)

                    _url = ''
                    if not body.ready:
                        body.current += 1
                        _url = await html_renderer.render_custom_template(
                            body.tmpl,
                            body.cache.pop(0).model_dump(),
                            True,
                            self.render_options
                        )
                    else:
                        _url = body.ready
                        body.ready = ''

                    _image = sess_event.image_result(_url)
                    await sess_event.send(_image)
                    controller.keep(120, True)

                    # 提前准备
                    if body.cache:
                        body.current += 1
                        body.ready = await html_renderer.render_custom_template(
                            body.tmpl,
                            body.cache.pop(0).model_dump(),
                            True,
                            self.render_options
                        )
                        if not body.cache:
                            if body.current < body.total:
                                new_resp = (await anext(self._recommend_task(
                                    cmd_body,
                                    only_data=True,
                                    page=int(body.current / self.recommend_cache + 1)
                                )))
                                body.cache = (await self._recommend_subtask(cmd_body, new_resp))[1]


                elif message == end:
                    await sess_event.send(sess_event.plain_result('成功关闭此次会话'))
                    self.session_data_storage.pop(_id)
                    controller.stop()
                else:
                    pass

            try:
                await select_waiter(event, session_filter=OnlySenderFilter())
            except TimeoutError:
                raise SessionTimeoutException(cmd_body)
        else:
            yield resp

    async def _bind_task(self, cmd_body: CommandBody):
        event = cmd_body.event
        channel_id = event.get_sender_id()
        if self.data_handler.check_data(channel_id):
            raise HasBoundException(channel_id)
        else:
            tips0 = '-Steam ID（不是好友ID）获取方法：\nhttps://help.steampowered.com/zh-cn/faqs/view/2816-BE67-5B69-0FEC\n-API获取方法：\nhttps://steamcommunity.com/dev/apikey'
            tips1 = '-请输入你的Steam ID\n-等待时间5分钟'
            yield event.plain_result(tips0)
            yield event.plain_result(tips1)
            self.session_data_storage[event.get_group_id() + event.get_sender_id()] = SteamData(
                platform_id=event.get_sender_id(),
                record=False
            )

            @session_waiter(timeout=300)
            async def bind_waiter(controller: SessionController, sess_event: AstrMessageEvent):
                _id = sess_event.get_group_id() + sess_event.get_sender_id()
                tips2 = '-请输入你的Steam Key\n-等待时间5分钟'
                tips4 = '输入的信息有误\n-会话已关闭'


                data: SteamData = self.session_data_storage[_id]
                if not data.steam_id:
                    data.steam_id = sess_event.message_str
                    await sess_event.send(sess_event.plain_result(tips2))
                    controller.keep(300, True)
                elif not data.key:
                    data.key = sess_event.message_str
                    try:
                        resp = await self.steam_request.request_profile(data)
                        await self.data_handler.store(data)
                        tips3 = f'-绑定成功\n-绑定用户名：{resp.personaname}'
                        await sess_event.send(sess_event.plain_result(tips3))
                    except ArgsOrNullException:
                        await sess_event.send(sess_event.plain_result(tips4))

                    controller.stop()
                    self.session_data_storage.pop(_id)
                else:
                    raise NotImplementedError

            try:
                await bind_waiter(event, session_filter=OnlySenderFilter())
            except TimeoutError:
                raise SessionTimeoutException(cmd_body)


    async def _puzzle_task(self, cmd_body: CommandBody):
        now = datetime.now().timestamp()

        event = cmd_body.event
        saved = await self.data_handler.read(event.get_sender_id())

        profile = await self.steam_request.request_profile(saved)
        steam_owner = await self.steam_request.request_owner(saved)
        # 在更新时间内
        if saved.record and now - saved.write_time <= self.update_interval * 3600:
            filename = f'{cmd_body.type.value}-{saved.platform_id}'
            cache = await self.cache.get_cache(filename)
            if cache is not None:
                yield event.chain_result([comp.Image.fromBytes(cache)])
                return

        # 近两周
        if saved.record and now - saved.write_time <= 2 * 7 * 24 * 3600:
            own_before = set(saved.vns.keys() | set(saved.others_id))
            extra_img_dict: dict[int, str] = {}
            extra_vns_id_set: set[int] = set()
            # 库存数量有变化，添加
            if steam_owner.game_count != len(own_before):
                id_set = {game.appid for game in steam_owner.games}
                extra_id_list = list((id_set - (set(saved.others) | set(saved.vns.keys()))))
                vndb_vns_list = await self.vndb_request.request_by_release(extra_id_list, steam_owner.game_count)
                vn_id_list = []

                for i in vndb_vns_list:
                    extra_img_dict[i.appid] = i.vns[0].image.url
                    for j in i.extlinks:
                        if j.label == 'Steam':
                            vn_id_list.append(int(j.id))
                            break
                saved.others_id = list(set(saved.others_id) | (set(extra_id_list) - set(vn_id_list)))
                extra_vns_id_set = set(vn_id_list)

            # 更新
            recent_list = await self.steam_request.request_recently(saved)
            recent_dict = {game.id: game for game in recent_list if game.appid in saved.vns or game.appid in extra_vns_id_set}
            for k, l in recent_dict:
                saved.vns[k] = SteamVnsInfo(
                    name=l.name,
                    play_time=l.playtime_forever,
                    vndb_img=saved.vns.get(k, {}).get('vndb_img', '') or extra_img_dict[k]
                )

                if k in extra_vns_id_set:
                    extra_vns_id_set.remove(k)


            for m in extra_vns_id_set:
                saved.vns[m] = SteamVnsInfo(
                    name=recent_dict[m].name,
                    play_time=0,
                    vndb_img=extra_img_dict[m]
                )
            saved.write_time = now

        # 初始化和更新超过两周
        else:
            id_list = [game.appid for game in steam_owner.games]
            vndb_vns_list = await self.vndb_request.request_by_release(id_list, steam_owner.game_count)
            vndb_vns_dict = {int(j.id): i.vns[0].image.url for i in vndb_vns_list for j in i.extlinks if
                             j.label == 'Steam'}
            steam_vn_list = [k for k in steam_owner.games if k.appid in vndb_vns_dict]

            saved.record = True
            saved.write_time = now
            saved.others_id = list(set(id_list) - set(vndb_vns_dict.keys()))
            saved.vns = {}
            for o in steam_vn_list:
                saved.vns[o.appid] = SteamVnsInfo(
                    name=o.name,
                    play_time=o.playtime_forever,
                    vndb_img=vndb_vns_dict[o.appid]
                )

        await self.data_handler.store(saved, True)
        rendered_html = self.template_dir / html_list[cmd_body.type.value + '2']
        data = self.builder.build_options(cmd_body, [profile], vns=saved.vns, update=datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M'))
        tmpl = File.read_text(rendered_html)

        res = await asyncio.gather(tmpl, data)
        url = await html_renderer.render_custom_template(res[0], res[1].model_dump(), True, self.render_options)
        await self.cache.store_image(f'{cmd_body.type.value}-{saved.platform_id}', await self.downloader.download_once(url))
        yield cmd_body.event.image_result(url)



    async def _recommend_subtask(self, cmd_body: CommandBody, responses: list[TouchGalResponse]):
        rendered_html = self.template_dir / html_list[cmd_body.type.value]
        tmpl = File.read_text(rendered_html)
        data_co = []
        for _resp in responses:
            text = await self.touchgal_request.request_html(_resp.unique_id)
            details = await self.html_handler.handle_touchgal_details(text)

            data_co.append(self.builder.build_options(cmd_body, [_resp], details=[details]))

        return await asyncio.gather(tmpl, asyncio.gather(*data_co))


    def _get_chain_image(self, chain: list[comp.BaseMessageComponent] , default_return = ''):
        for msg in chain:
            if isinstance(msg, comp.Image):
                return msg.url
        return default_return



_task_line: Optional[TaskLine] = None
def get_task_line():
    global _task_line
    if _task_line is None:
        _task_line = TaskLine()
    return _task_line
