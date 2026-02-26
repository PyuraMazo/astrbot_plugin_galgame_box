import asyncio
import aiohttp
from typing import Optional, Any
from pathlib import Path

from astrbot.api import logger
from astrbot.api import AstrBotConfig

from ..utils.file import File

try:
    from curl_cffi.requests import AsyncSession as CurlAsyncSession
except Exception:  # pragma: no cover - optional dependency
    CurlAsyncSession = None


class Downloader:
    def __init__(self):
        self.err_image_path = (
            Path(__file__).parent / ".." / ".." / "resources" / "image" / "error.jpg"
        )
        self.headers = {"Content-Type": "application/json"}
        self.connector = aiohttp.TCPConnector(limit_per_host=2, limit=10)

        self.timeout_times = None
        self.request_time = 30
        self.session: Optional[aiohttp.ClientSession] = None
        self.curl_session: Optional[Any] = None
        self.err_image: Optional[bytes] = None
        self.browser_impersonate: str = ""

    async def initialize(self, config: AstrBotConfig):
        self.timeout_times = config.get("basicSetting", {}).get("requestTimeout", 3)
        self.request_time = config.get("basicSetting", {}).get("requestTime", 30)
        self.browser_impersonate = (
            config.get("internetSetting", {}).get("browserImpersonate", "chrome136")
        ).strip()
        ua = config.get("internetSetting", {}).get("userAgent", "")
        if ua:
            self.headers["user-agent"] = ua
        self.err_image = await File.read_buffer(str(self.err_image_path))

        if self.session is None:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(
                    total=self.request_time
                ),
                headers=self.headers,
                connector=self.connector,
            )
        if self._curl_ready() and self.curl_session is None:
            self.curl_session = CurlAsyncSession(
                headers=self.headers,
                timeout=self.request_time,
            )
        elif self.browser_impersonate and CurlAsyncSession is None:
            logger.warning(
                "未安装curl_cffi，封面图下载回退为aiohttp，可能被Cloudflare拦截"
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

    async def download_once(self, url: str, **kwargs) -> bytes:
        return await self.get(url, **kwargs)

    async def download_more(self, url: list[str]) -> Any:
        co = [self.get(i) for i in url]
        return await asyncio.gather(*co)

    def _curl_ready(self) -> bool:
        return bool(CurlAsyncSession and self.browser_impersonate)

    @staticmethod
    def _is_touchgal_asset_url(url: str) -> bool:
        return "touchgal.top" in url or "touchgaloss.com" in url

    def _should_use_curl(self, url: str) -> bool:
        return bool(self.curl_session and self._is_touchgal_asset_url(url))

    @staticmethod
    def _looks_like_html(data: bytes) -> bool:
        if not data:
            return False
        head = data[:512].lstrip().lower()
        return (
            head.startswith(b"<!doctype html")
            or head.startswith(b"<html")
            or b"just a moment" in head
            or b"__cf_chl" in head
        )

    @classmethod
    def _is_cf_or_html_response(cls, status: int, headers: Any, body: bytes) -> bool:
        if status == 403:
            cf_mitigated = str(headers.get("cf-mitigated", "")).lower()
            if "challenge" in cf_mitigated:
                return True
        content_type = str(headers.get("content-type", "")).lower()
        if "text/html" in content_type:
            return True
        return cls._looks_like_html(body)

    async def get(self, url: str, **kwargs) -> bytes:
        if not url.startswith("http"):
            return self.err_image
        count = 0
        while count < self.timeout_times:
            try:
                if self._should_use_curl(url):
                    response = await self.curl_session.get(
                        url,
                        timeout=kwargs.get("timeout", self.request_time),
                        impersonate=self.browser_impersonate,
                    )
                    body = (
                        bytes(response.content)
                        if isinstance(response.content, (bytes, bytearray))
                        else str(response.content).encode("utf-8", errors="ignore")
                    )
                    if self._is_cf_or_html_response(
                        response.status_code, response.headers, body
                    ):
                        return self.err_image
                    return body

                async with self.session.get(url, **kwargs) as response:
                    body = await response.read()
                    if self._is_cf_or_html_response(
                        response.status, response.headers, body
                    ):
                        return self.err_image
                    return body

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
