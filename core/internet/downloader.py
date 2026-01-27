from typing import Optional
from pathlib import Path

from astrbot.core import AstrBotConfig

from .http import _Http, get_http
from ..api.exception import InternetException
from ..utils.file import File


class Downloader:
    def __init__(self):
        self.err_image_path = Path(__file__).parent / '..' / '..' / 'resources' / 'image' / 'error.jpg'

        self.http: Optional[_Http] = None
        self.err_image: Optional[bytes] = None

    async def initialize(self, config: AstrBotConfig):
        self.http = get_http()

        await self.http.initialize(config)
        await File.read_buffer(str(self.err_image_path))

    async def terminate(self):
        await self.http.terminate()


    async def do(self, url: str, **kwargs) -> bytes:
        try:
            return await self.http.get(url, 'bytes', **kwargs)
        except InternetException:
            return self.err_image



_downloader: Optional[Downloader] = None
def get_downloader():
    global _downloader
    if _downloader is None:
        _downloader = Downloader()
    return _downloader