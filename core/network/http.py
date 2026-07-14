import asyncio
from typing import Literal

from aiohttp import ClientSession, ClientTimeout

from astrbot.api import AstrBotConfig, logger

from ..type.exceptions import InternetException


class Http:
    headers = {"Content-Type": "application/json"}

    @classmethod
    async def initialize(cls, config: AstrBotConfig):
        cls.timeout_times = config.get("basicSetting", {}).get("requestTimeout", 3)
        cls.tls = config.get("safetySetting", {}).get("tls", "chrome136")

        cls.session = ClientSession(
            timeout=ClientTimeout(
                total=config.get("basicSetting", {}).get("requestTime", 30)
            )
        )
        return cls()

    async def terminate(self):
        if not self.session.closed:
            await self.session.close()

    async def get(
        self,
        url: str,
        res_type: Literal["json", "bytes", "text"] = "text",
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
