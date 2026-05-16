import asyncio

import aiohttp

from astrbot.api import AstrBotConfig, logger

from ..api.exception import InternetException


class Http:
    def __init__(self):
        self.headers = {"Content-Type": "application/json"}

        self.timeout_times = None
        self.session: aiohttp.ClientSession | None = None
        self.tls: str | None = None

    async def initialize(self, config: AstrBotConfig):
        self.timeout_times = config.get("basicSetting", {}).get("requestTimeout", 3)
        self.tls = config.get("safetySetting", {}).get("tls", "chrome136")
        if self.session is None:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(
                    total=config.get("basicSetting", {}).get("requestTime", 30)
                )
            )

    async def terminate(self):
        if not self.session.closed:
            await self.session.close()

    async def get(
        self,
        url: str,
        res_type: str = "text",
        err_handle=None,
        handle_cf=False,
        **kwargs,
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
            except Exception:
                count += 1
                await asyncio.sleep(0.5)
                # logger.info(f"网络请求失败一次...{str(e)}")
        if res_type == "bytes" and err_handle:
            return err_handle
        if handle_cf:
            return await self._cf_curl(
                method="get", res_type=res_type, url=url, **kwargs
            )
        else:
            raise InternetException(url)

    async def post(
        self, url: str, data: dict, handle_cf=False, **kwargs
    ) -> str | dict | bytes:
        headers = kwargs.pop("headers", self.headers)
        count = 0
        while count < self.timeout_times:
            try:
                async with self.session.post(
                    url, headers=headers, json=data, **kwargs
                ) as response:
                    return await response.json()
            except Exception:
                count += 1
                await asyncio.sleep(0.5)
                # logger.info(f"网络请求失败一次...{str(e)}")
        if handle_cf:
            return await self._cf_curl(
                method="post", url=url, json=data, headers=headers, **kwargs
            )
        else:
            raise InternetException(url)

    async def _cf_curl(self, **kwargs) -> str | dict | bytes:
        try:
            from curl_cffi.requests import AsyncSession

            async with AsyncSession() as session:
                t = kwargs.pop("res_type", None)
                m = kwargs.pop("method")
                if m == "get":
                    response = await session.get(impersonate=self.tls, **kwargs)
                    if t == "json":
                        return response.json()
                    elif t == "bytes":
                        return response.read()
                    else:
                        return response.text
                else:
                    response = await session.post(impersonate=self.tls, **kwargs)
                    return response.json()
        except ImportError:
            logger.warn(
                "网络请求失败。目前未安装curl_cffi模块，可能解决问题通过：pip install curl_cffi"
            )
            raise InternetException(kwargs["url"])
        except Exception:
            raise InternetException(kwargs["url"])


_http: Http | None = None


def get_http() -> Http:
    global _http
    if _http is None:
        _http = Http()
    return _http
