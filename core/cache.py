import os
import shutil
import asyncio

from astrbot.api import AstrBotConfig
from astrbot.api.star import StarTools

from .http import get_http
from .utils.file import File
from .api.type import CommandBody



class Cache:
    def __init__(self, config: AstrBotConfig):
        data_path = StarTools.get_data_dir('astrbot_plugin_galgame_box')
        self.cache_path = data_path / 'cache'
        self.http = get_http(config)

    async def download_get_image(self, url: str, tag: str | int | CommandBody = None, cache: bool = False) -> bytes:
        self._check_dir()
        source_suffix = url.split('.')[-1]

        if tag:
            formated = self._format_filename(tag)
            path = str(self.cache_path / formated)

            if self._check_cache(path):
                return await self.get_cache_async(formated)
            else:
                buffer = await self.http.get(url, 'byte')

                if source_suffix.lower() == 'avif':
                    buf = await File.avif2jpg_async(buffer)
                    if cache:
                        await self._do_cache_async(path, buf)
                    return buf
                else:
                    if cache:
                        await self._do_cache_async(path, buffer)
                    return buffer

        else:
            buffer = await self.http.get(url, 'byte')
            return await File.avif2jpg_async(buffer) if source_suffix.lower() == 'avif' else buffer

    async def get_cache_async(self, tag: str | int | CommandBody) -> bytes | None:
        self._check_dir()
        filename = self._format_filename(tag)
        path = str(self.cache_path / filename)

        cache = self._check_cache(path)
        return await File.read_buffer(path) if cache else None


    async def _do_cache_async(self, path: str, data: bytes):
        """filename统一使用【TouchGal ID】或者【命令-参数】"""
        self._check_dir()

        if self._check_cache(path):
            return

        await File.write_buffer(path, data)

    async def clean_cache_async(self):

        if os.path.exists(self.cache_path):
            dirs = await asyncio.to_thread(os.listdir, self.cache_path)
            if len(dirs) == 0:
                return
            else:
                await asyncio.to_thread(lambda: shutil.rmtree(self.cache_path))
        self._check_dir()

    async def close_http_session(self):
        await self.http.close()


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
        if not os.path.exists(self.cache_path):
            os.makedirs(self.cache_path)
