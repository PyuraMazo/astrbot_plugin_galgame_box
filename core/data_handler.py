import asyncio
import base64
import json
import os
import shutil
from typing import Optional


from astrbot.api import AstrBotConfig
from astrbot.api.star import StarTools
from .api.exception import HasBoundException, NoBoundException

from .api.type import SteamData
from .utils.file import File

class DataHandler:
    def __init__(self):
        data_path = StarTools.get_data_dir('astrbot_plugin_galgame_box')
        self.data_dir = data_path / 'data'

    async def initialize(self, config: AstrBotConfig):
        self._check_dir()

    async def terminate(self):
        # await self._clean_all()
        pass

    async def store(self, data: SteamData, force = False):
        channel_id = data.channel_id
        path = self.build_path(channel_id)
        if force or not self.check_data(channel_id):
            await File.write_buffer(path, base64.b64encode(json.dumps(data.model_dump()).encode()))
        else:
            raise HasBoundException(channel_id)


    async def read(self, channel_id: str) -> SteamData | None:
        if self.check_data(channel_id):
            bs64 = base64.b64decode(await File.read_buffer(self.build_path(channel_id)))
            return SteamData.model_validate(json.loads(bs64.decode()))
        else:
            raise NoBoundException(channel_id)


    def build_path(self, channel_id: str) -> str:
        return str(self.data_dir / f'{channel_id}.secret')


    def check_data(self, channel_id: str) -> bool:
        path = self.build_path(channel_id)
        return os.path.exists(path)

    async def _clean_all(self):
        dirs = await asyncio.to_thread(os.listdir, self.data_dir)
        if len(dirs) == 0:
            return
        else:
            await asyncio.to_thread(shutil.rmtree, self.data_dir)

    def _check_dir(self):
        os.makedirs(self.data_dir, exist_ok=True)


_handler: Optional[DataHandler] = None
def get_data_handler():
    global _handler
    if _handler is None:
        _handler = DataHandler()
    return _handler