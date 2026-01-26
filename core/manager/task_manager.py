import asyncio
from pathlib import Path
from typing import Callable

from astrbot.api import AstrBotConfig
from ..api.model import AnimeTraceResponse

from ..api.type import CommandBody, CommandType, UnrenderedData, AnimeTraceModel
from ..builder import Builder
from ..request import VNDBRequest, TouchGalRequest, AnimeTreceRequest
from ..utils.file import File
from ..handler import Handler
from ..api.exception import InvalidArgsException, NoResultException, CodeException
from ..cache import Cache
from ..api import const


class TaskLine:

    def __init__(self, config: AstrBotConfig, resource_path: Path, cmd: CommandBody):
        self.config = config
        self.resource_path = resource_path
        self.cmd = cmd
        self.template_path = self.resource_path / 'template'

        self.builder = Builder(self.config, self.resource_path)
        self.cache = Cache(self.config)
        self.handler = Handler()

        self.task_map: dict[CommandType, Callable] = {
            CommandType.VN: self._vn_cha_task,
            CommandType.CHARACTER: self._vn_cha_task,
            CommandType.PRODUCER: self._vn_cha_task,
            CommandType.ID: self._id_task,
            CommandType.RANDOM: self._random_task,
            CommandType.FIND: self._find_task,
        }


    async def start(self) -> tuple[str, UnrenderedData]:
        return await self.task_map[self.cmd.type]()


    async def _vn_cha_task(self) -> tuple[str, UnrenderedData]:
        request = VNDBRequest(self.config, self.cmd)
        rendered_html = self.template_path / const.html_list[self.cmd.type.value]
        res = await request.request_simply()
        data = await self.builder.build_options(self.cmd, res)
        buffer = await File.read_text(rendered_html)

        return buffer, data


    async def _pro_task(self) -> tuple[str, UnrenderedData]:
        request = VNDBRequest(self.config, self.cmd)
        rendered_html = self.template_path / const.html_list[self.cmd.type.value]
        pro, vns = await request.request_by_producer()
        data = await self.builder.build_options(self.cmd, pro, vns=vns)
        buffer = await File.read_text(rendered_html)

        return buffer, data


    async def _id_task(self) -> tuple[str, UnrenderedData]:
        request = VNDBRequest(self.config, self.cmd)
        if self.cmd.value[0] not in const.id2command.keys():
            raise InvalidArgsException(f'{self.cmd.type}-{self.cmd.value}')

        actual_type_value = const.id2command[self.cmd.value[0]]
        rendered_html = self.template_path / const.html_list[actual_type_value]
        res = await request.request_by_id()

        data = await self.builder.build_options(self.cmd, res[0], vns=res[1]) \
            if actual_type_value == CommandType.PRODUCER.value \
            else await self.builder.build_options(self.cmd, res)

        buffer = await File.read_text(rendered_html)

        return buffer, data


    async def _random_task(self) -> tuple[str, UnrenderedData]:
        request = TouchGalRequest(self.config)
        rendered_html = self.template_path / const.html_list[self.cmd.type.value]
        unique_id = await request.request_random()
        text = await request.request_html(unique_id)
        details = await self.handler.handle_touchgal_details(text)
        resp = (await request.request_vn_by_search(details.vndb_id))[0]
        data = await self.builder.build_options(self.cmd, resp, details=details)
        buffer = await File.read_text(rendered_html)

        return buffer, data

    async def _find_task(self) -> tuple[str, UnrenderedData]:
        trace_request = AnimeTreceRequest(self.config)
        vndb_request = VNDBRequest(self.config, self.cmd)

        model = AnimeTraceModel.Profession
        trace_resp: AnimeTraceResponse
        try:
            trace_resp = await trace_request.request(self.cmd.value, model)
        except CodeException:
            model = AnimeTraceModel.Common
            trace_resp = await trace_request.request(self.cmd.value, model)

        if not trace_resp.data:
            raise NoResultException(f'{self.cmd.type}-{self.cmd.value}')

        max_count = self.config.get('searchSetting', {}).get('findResults', 3)
        vndb_resp = []
        for i in trace_resp.data:
            index = 1
            block = []
            for j in i.character:
                block.append(vndb_request.request_by_find(j.character, j.work))
                if index < len(i.character) and index < max_count:
                    index += 1
                else:
                    break

            vndb_resp.append(await asyncio.gather(*block))

        rendered_html = self.template_path / const.html_list[self.cmd.type.value]
        data = await self.builder.build_options(self.cmd,
                                                trace_resp,
                                                vndb_resp=vndb_resp,
                                                image=self.cmd.value,
                                                count=len(trace_resp.data),
                                                model=model)
        buffer = await File.read_text(rendered_html)

        return buffer, data