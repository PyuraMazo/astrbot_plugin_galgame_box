import os
import shutil

from astrbot.api import AstrBotConfig

from .http import Http
from .utils.file import File
from .api.excption import NoCacheException
from .api.type import CommandBody


class Cache:
    cache_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'cache')


    def __init__(self, config: AstrBotConfig):
        self.http = Http(config)
        self._check_dir()


    async def download_get_image(self, url: str, tag: str | int | CommandBody = None, cache: bool = False, suffix: str = 'jpg') -> bytes:
        source_suffix = url.split('.')[-1]

        if tag:
            formated = self._format_filename(tag)
            path = os.path.join(self.cache_path, formated)

            if self._check_cache(path):
                return self.get_cache(formated)
            else:
                buffer = await self.http.get(url, 'byte')

                if source_suffix.lower() == suffix:
                    if cache:
                        self._do_cache(path, buffer)
                    return buffer
                else:
                    buf = File.avif2jpg(buffer)
                    if cache:
                        self._do_cache(path, buf)
                    return buf
        else:
            buffer = await self.http.get(url, 'byte')
            return File.avif2jpg(buffer) if source_suffix.lower() != suffix else buffer

    def get_cache(self, tag: str | int | CommandBody) -> bytes | None:
        filename = self._format_filename(tag)
        path = os.path.join(self.cache_path, filename)

        cache = self._check_cache(path)
        return File.read_buffer(path) if cache else None


    def _do_cache(self, path: str, data: bytes):
        """filename统一使用【TouchGal ID】或者【命令-参数】"""

        if self._check_cache(path):
            return

        File.write_buffer(path, data)

    def clean_cache(self):
        if os.path.exists(self.cache_path):
            if len(os.listdir(self.cache_path)) == 0:
                return
            else:
                shutil.rmtree(self.cache_path)

        self._check_dir()

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