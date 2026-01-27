import os
import shutil
import asyncio
from typing import Optional

from astrbot.api import AstrBotConfig
from astrbot.api.star import StarTools

from .utils.file import File
from .utils.image import Image
from .api.type import CommandBody



class Cache:
    def __init__(self):
        data_path = StarTools.get_data_dir('astrbot_plugin_galgame_box')
        self.cache_path = data_path / 'cache'


    async def initialize(self, config: AstrBotConfig):
        self._check_dir()

    async def terminate(self):
        await self.clean_cache()

    async def store_image(self, filename: str | int | CommandBody, buffer: bytes, source_suffix = 'jpg'):
        path = str(self.get_cache_path(filename))

        if self._check_cache(path):
            return
        else:
            if source_suffix.lower() != 'jpg' and source_suffix.lower() != 'jpeg':
                buffer = await Image.image2jpg_async(buffer)
            await File.write_buffer(path, buffer)



    async def get_cache(self, filename: str | int | CommandBody) -> bytes | None:
        path = str(self.get_cache_path(filename))

        cache = self._check_cache(path)
        return await File.read_buffer(path) if cache else None

    async def clean_cache(self):
        if os.path.exists(self.cache_path):
            dirs = await asyncio.to_thread(os.listdir, self.cache_path)
            if len(dirs) == 0:
                return
            else:
                await asyncio.to_thread(lambda: shutil.rmtree(self.cache_path))
        self._check_dir()


    def get_cache_path(self, filename: str | int | CommandBody):
        formated = self._format_filename(filename)
        return self.cache_path / formated

    def _format_filename(self, tag: str | int | CommandBody) -> str:
        formated_filename: str
        if isinstance(tag, CommandBody):
            formated_filename = f'{tag.type.value}-{tag.value}'
        elif isinstance(tag, int):
            formated_filename = str(tag)
        else:
            formated_filename = tag
        return formated_filename + '.jpg'


    def _check_cache(self, path: str) -> bool:
        return os.path.exists(path)


    def _check_dir(self):
        os.makedirs(self.cache_path, exist_ok=True)



_cache: Optional[Cache] = None
def get_cache():
    global _cache
    if _cache is None:
        _cache = Cache()
    return _cache