import asyncio
import aiohttp
from typing import Optional, Any
from pathlib import Path

from astrbot.api import logger
from astrbot.api import AstrBotConfig

from ..utils.file import File


class Downloader:
    def __init__(self):
        self.err_image_path = (
            Path(__file__).parent / ".." / ".." / "resources" / "image" / "error.jpg"
        )
        self.headers = {"Content-Type": "application/json"}
        self.connector = aiohttp.TCPConnector(limit_per_host=2, limit=10)

        self.timeout_times = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.err_image: Optional[bytes] = None

    async def initialize(self, config: AstrBotConfig):
        self.timeout_times = config.get("basicSetting", {}).get("requestTimeout", 3)
        self.err_image = await File.read_buffer(str(self.err_image_path))

        if self.session is None:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(
                    total=config.get("basicSetting", {}).get("requestTime", 30)
                ),
                headers=self.headers,
                connector=self.connector,
            )

    async def terminate(self):
        if not self.session.closed:
            await self.session.close()

    async def download_once(self, url: str, **kwargs) -> bytes:
        return await self.get(url, **kwargs)

    async def download_more(self, url: list[str]) -> Any:
        co = [self.get(i) for i in url]
        return await asyncio.gather(*co)

    async def get(self, url: str, **kwargs) -> bytes:
        if not url.startswith("http"):
            return self.err_image
        count = 0
        while count < self.timeout_times:
            try:
                async with self.session.get(url, **kwargs) as response:
                    return await response.read()

            except Exception as e:
                count += 1
                await asyncio.sleep(0.5)
                logger.info(f"网络请求失败一次...{str(e)}")
        return self.err_image


_downloader: Optional[Downloader] = None


def get_downloader():
    global _downloader
    if _downloader is None:
        _downloader = Downloader()
    return _downloader
