import asyncio
import json
from typing import Optional, Any

import aiohttp

from astrbot.api import logger
from astrbot.api import AstrBotConfig

from ..api.exception import InternetException, CloudflareChallengeException

try:
    from curl_cffi.requests import AsyncSession as CurlAsyncSession
except Exception:  # pragma: no cover - optional dependency
    CurlAsyncSession = None


class Http:
    def __init__(self):
        self.headers = {"Content-Type": "application/json"}

        self.timeout_times = 3
        self.request_time = 30
        self.session: Optional[aiohttp.ClientSession] = None
        self.curl_session: Optional[Any] = None

        self.browser_impersonate = ""

    async def initialize(self, config: AstrBotConfig):
        ua = config.get("internetSetting", {}).get("userAgent", "")
        if ua:
            self.headers["user-agent"] = ua

        self.timeout_times = config.get("basicSetting", {}).get("requestTimeout", 3)
        self.request_time = config.get("basicSetting", {}).get("requestTime", 30)
        self.browser_impersonate = (
            config.get("internetSetting", {}).get("browserImpersonate", "chrome136")
        ).strip()

        if self.session is None:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.request_time),
                headers=self.headers,
            )

        if self._curl_ready() and self.curl_session is None:
            self.curl_session = CurlAsyncSession(
                headers=self.headers,
                timeout=self.request_time,
            )
        elif self.browser_impersonate and CurlAsyncSession is None:
            logger.warning(
                "未安装curl_cffi，TouchGal请求将回退为aiohttp，可能继续被Cloudflare拦截"
            )

    async def terminate(self):
        if self.session is not None and not self.session.closed:
            await self.session.close()

        if self.curl_session is not None:
            try:
                await self.curl_session.close()
            except Exception:
                pass
            self.curl_session = None

    def _curl_ready(self) -> bool:
        return bool(CurlAsyncSession and self.browser_impersonate)

    @staticmethod
    def _is_touchgal_url(url: str) -> bool:
        return "touchgal.top" in url

    def _should_use_curl(self, url: str) -> bool:
        return bool(self.curl_session and self._is_touchgal_url(url))

    @staticmethod
    def _is_cf_challenge(status: int, headers: dict | Any, text: str) -> bool:
        if status != 403:
            return False

        cf_mitigated = str(headers.get("cf-mitigated", "")).lower() if headers else ""
        if "challenge" in cf_mitigated:
            return True

        lower_text = (text or "").lower()
        return any(
            key in lower_text
            for key in (
                "just a moment",
                "enable javascript and cookies",
                "challenge-platform",
                "__cf_chl",
            )
        )

    @staticmethod
    def _curl_text(response: Any) -> str:
        text = getattr(response, "text", "")
        if callable(text):
            try:
                text = text()
            except TypeError:
                pass
        if isinstance(text, str) and text:
            return text

        content = getattr(response, "content", b"")
        if isinstance(content, (bytes, bytearray)):
            return bytes(content).decode("utf-8", errors="ignore")
        return str(content)

    def _curl_options(self, kwargs: dict) -> dict:
        options = {}
        for key in ("headers", "cookies", "params", "json", "data"):
            if key in kwargs and kwargs[key] is not None:
                options[key] = kwargs[key]

        options["timeout"] = kwargs.get("timeout", self.request_time)
        options["impersonate"] = self.browser_impersonate

        if "allow_redirects" in kwargs:
            options["allow_redirects"] = kwargs["allow_redirects"]

        return options

    def _parse_curl_response(
        self, response: Any, res_type: str, url: str
    ) -> str | dict | bytes:
        status = int(getattr(response, "status_code", 0))
        headers = getattr(response, "headers", {}) or {}
        text = self._curl_text(response)

        if self._is_cf_challenge(status, headers, text):
            raise CloudflareChallengeException(url)
        if status >= 400:
            raise RuntimeError(f"http status {status}")

        if res_type == "json":
            try:
                return response.json()
            except Exception:
                try:
                    return json.loads(text)
                except Exception as e:
                    raise RuntimeError(f"json parse error: {e}") from e

        if res_type == "bytes":
            content = getattr(response, "content", b"")
            if isinstance(content, (bytes, bytearray)):
                return bytes(content)
            return text.encode("utf-8")

        return text

    async def _aiohttp_response(
        self, response: aiohttp.ClientResponse, res_type: str, url: str
    ) -> str | dict | bytes:
        if res_type == "bytes":
            data = await response.read()
            text = data[:4000].decode("utf-8", errors="ignore")
            if self._is_cf_challenge(response.status, response.headers, text):
                raise CloudflareChallengeException(url)
            if response.status >= 400:
                raise RuntimeError(f"http status {response.status}")
            return data

        text = await response.text()
        if self._is_cf_challenge(response.status, response.headers, text):
            raise CloudflareChallengeException(url)
        if response.status >= 400:
            raise RuntimeError(f"http status {response.status}")

        if res_type == "json":
            try:
                return json.loads(text)
            except Exception as e:
                raise RuntimeError(f"json parse error: {e}") from e

        return text

    async def get(
        self, url: str, res_type: str = "text", err_handle=None, **kwargs
    ) -> str | dict | bytes:
        if res_type == "bytes" and not url.startswith("http"):
            if err_handle:
                return err_handle
            raise InternetException(url)

        count = 0
        while count < self.timeout_times:
            try:
                if self._should_use_curl(url):
                    response = await self.curl_session.get(
                        url, **self._curl_options(kwargs)
                    )
                    return self._parse_curl_response(response, res_type, url)

                async with self.session.get(url, **kwargs) as response:
                    return await self._aiohttp_response(response, res_type, url)
            except CloudflareChallengeException:
                raise
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
                if self._should_use_curl(url):
                    payload = {"headers": headers, "json": data} | kwargs
                    response = await self.curl_session.post(
                        url,
                        **self._curl_options(payload),
                    )
                    return self._parse_curl_response(response, "json", url)

                async with self.session.post(
                    url, headers=headers, json=data, **kwargs
                ) as response:
                    return await self._aiohttp_response(response, "json", url)
            except CloudflareChallengeException:
                raise
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
