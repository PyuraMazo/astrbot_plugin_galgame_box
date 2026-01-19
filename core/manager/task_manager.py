from pathlib import Path

from astrbot.api import AstrBotConfig


from ..api.type import CommandBody, CommandType, ConfigDict, UnrenderedData
from ..builder import Builder
from ..http import VNDBRequest, TouchGalRequest
from ..utils.file import File
from ..handler import Handler
from ..api.exception import *
from ..cache import Cache



class TaskLine:

    def __init__(self, config: AstrBotConfig, resource_path: Path, cmd: CommandBody):
        self.config = config
        self.resource_path = resource_path
        self.cmd = cmd
        self.template_path = self.resource_path / 'template'

        self.builder = Builder(self.config, self.resource_path)
        self.cache = Cache(self.config)
        self.handler = Handler()


    async def start(self) -> tuple[str, UnrenderedData]:
        if self.cmd.type == CommandType.VN or self.cmd.type == CommandType.CHARACTER:
            return await self._vn_cha_task()
        elif self.cmd.type == CommandType.PRODUCER:
            return await self._pro_task()
        elif self.cmd.type == CommandType.ID:
            return await self._id_task()
        elif self.cmd.type == CommandType.RANDOM:
            return await self._random_task()
        else:
            raise NotImplementedError



    async def _vn_cha_task(self) -> tuple[str, UnrenderedData]:
        request = VNDBRequest(self.config, self.cmd)
        rendered_html = self.template_path / ConfigDict.html_list[self.cmd.type.value]
        res = await request.request_simply()
        data = await self.builder.build_options(self.cmd, res)
        buffer = await File.read_text(rendered_html)

        return buffer, data


    async def _pro_task(self) -> tuple[str, UnrenderedData]:
        request = VNDBRequest(self.config, self.cmd)
        rendered_html = self.template_path / ConfigDict.html_list[self.cmd.type.value]
        pro, vns = await request.request_by_producer()
        data = await self.builder.build_options(self.cmd, pro, vns=vns)
        buffer = await File.read_text(rendered_html)

        return buffer, data


    async def _id_task(self) -> tuple[str, UnrenderedData]:
        request = VNDBRequest(self.config, self.cmd)
        if self.cmd.value[0] not in ConfigDict.id2command.keys():
            raise InvalidArgsException

        actual_type_value = ConfigDict.id2command[self.cmd.value[0]]
        rendered_html = self.template_path / ConfigDict.html_list[actual_type_value]
        res = await request.request_by_id()

        data = await self.builder.build_options(self.cmd, res[0], vns=res[1]) \
            if actual_type_value == CommandType.PRODUCER.value \
            else await self.builder.build_options(self.cmd, res)

        buffer = await File.read_text(rendered_html)

        return buffer, data


    async def _random_task(self) -> tuple[str, UnrenderedData]:
        request = TouchGalRequest(self.config)
        rendered_html = self.template_path / ConfigDict.html_list[self.cmd.type.value]
        unique_id = await request.request_random()
        text = await request.request_html(unique_id)
        details = await self.handler.handle_touchgal_details(text)
        resp = (await request.request_vn_by_search(details.vndb_id))[0]
        data = await self.builder.build_options(self.cmd, resp, details=details)
        buffer = await File.read_text(rendered_html)

        return buffer, data