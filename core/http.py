import asyncio
import aiohttp
from typing import Optional

from astrbot.api import logger
from astrbot.api import AstrBotConfig

from .api.exception import InternetException


class _Http:
    def __init__(self, config: AstrBotConfig):
        basic_config = config.get('basicSetting', {})
        self.timeout_times = basic_config.get('requestTimeout', 3)
        self.headers = {"Content-Type": "application/json"}

        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=basic_config.get('requestTime', 30))
        )


    async def get(self, url: str, res_type: str = 'text', **kwargs) -> str | dict | bytes:
        count = 0
        while count < self.timeout_times:
            try:
                if res_type == 'json':
                    async with self.session.get(url, **kwargs) as response:
                        return await response.json()
                elif res_type == 'byte':
                    async with self.session.get(url, **kwargs) as response:
                        return await response.read()
                else:
                    async with self.session.get(url, **kwargs) as response:
                        return await response.text()
            except Exception as e:
                count += 1
                await asyncio.sleep(0.5)
                logger.info(str(e) + '网络请求失败一次...')
        raise InternetException(url)


    async def post(self, url: str, data: dict, **kwargs) -> str | dict | bytes:
        count = 0
        while count < self.timeout_times:
            try:
                async with self.session.post(url, headers=self.headers, json=data, **kwargs) as response:
                    return await response.json()
            except Exception as e:
                count += 1
                await asyncio.sleep(0.5)
                logger.info(str(e) + '网络请求失败一次...')
        raise InternetException(url)

    async def close(self):
        if not self.session.closed:
            await self.session.close()


_http: Optional[_Http] = None

def get_http(config: AstrBotConfig) -> _Http:
    global _http
    if _http is None:
        _http = _Http(config)
    return _http