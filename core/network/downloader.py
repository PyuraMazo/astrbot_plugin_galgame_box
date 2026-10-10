import asyncio

from aiohttp import ClientSession, ClientTimeout, TCPConnector

from astrbot.api import AstrBotConfig


class Downloader:
    @classmethod
    async def initialize(cls, config: AstrBotConfig):
        cls.timeout_times = config.get("basicSetting", {}).get("requestTimeout", 3)
        cls.proxy = config.get("safetySetting", {}).get("proxy", None)

        request_time = config.get("basicSetting", {}).get("requestTime", 30)
        connector = TCPConnector(
            limit_per_host=5, limit=20, ttl_dns_cache=300, keepalive_timeout=10
        )
        cls.session = ClientSession(
            timeout=ClientTimeout(total=request_time),
            connector=connector,
        )
        return cls()

    async def terminate(self):
        if not self.session.closed:
            await self.session.close()

    async def download_image(self, url: str, use_proxy=False) -> bytes | None:
        kwargs = {}
        if use_proxy:
            kwargs["proxy"] = self.proxy

        return await self._get(url, **kwargs)

    async def _get(self, url: str, **kwargs) -> bytes | None:
        if not url.startswith("http"):
            return None
        count = 0
        while count < self.timeout_times:
            try:
                async with self.session.get(url, **kwargs) as response:
                    return await response.read()

            except Exception:
                await asyncio.sleep(0.5 * (2**count))
                count += 1
        return None
