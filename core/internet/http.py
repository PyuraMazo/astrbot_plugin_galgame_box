import asyncio
import aiohttp
from typing import Optional

from astrbot.api import logger
from astrbot.api import AstrBotConfig

from ..api.exception import InternetException


class Http:
    def __init__(self):
        self.headers = {"Content-Type": "application/json"}

        self.timeout_times = None
        self.session: Optional[aiohttp.ClientSession] = None

    async def initialize(self, config: AstrBotConfig):
        ua = config.get("internetSetting", {}).get("userAgent", "")
        if ua:
            self.headers["user-agent"] = ua

        self.timeout_times = config.get("basicSetting", {}).get("requestTimeout", 3)
        if self.session is None:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(
                    total=config.get("basicSetting", {}).get("requestTime", 30)
                ),
                headers=self.headers,
            )

    async def terminate(self):
        if not self.session.closed:
            await self.session.close()

    async def get(
        self, url: str, res_type: str = "text", err_handle=None, **kwargs
    ) -> str | dict | bytes:
        if res_type == "bytes" and not url.startswith("http"):
            if err_handle:
                return err_handle
            else:
                raise InternetException(url)
        count = 0
        while count < self.timeout_times:
            try:
                if res_type == "json":
                    async with self.session.get(url, **kwargs) as response:
                        return await response.json()
                elif res_type == "bytes":
                    async with self.session.get(url, **kwargs) as response:
                        return await response.read()
                else:
                    async with self.session.get(url, **kwargs) as response:
                        return await response.text()
            except Exception as e:
                count += 1
                await asyncio.sleep(0.5)
                logger.info(f"网络请求失败一次...{str(e)}")
        if res_type == "bytes" and err_handle:
            return err_handle
        raise InternetException(url)

    async def post(self, url: str, data: dict, **kwargs) -> str | dict | bytes:
        headers = self.headers | kwargs.pop("headers", {})
        count = 0
        while count < self.timeout_times:
            try:
                async with self.session.post(
                    url, headers=headers, json=data, **kwargs
                ) as response:
                    return await response.json()
            except Exception as e:
                count += 1
                await asyncio.sleep(0.5)
                logger.info(f"网络请求失败一次...{str(e)}")
        raise InternetException(url)


_http: Optional[Http] = None


def get_http() -> Http:
    global _http
    if _http is None:
        _http = Http()
    return _http
