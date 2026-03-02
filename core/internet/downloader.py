import asyncio
from pathlib import Path
from typing import Any

import aiohttp

from astrbot.api import AstrBotConfig, logger

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
        self.session: aiohttp.ClientSession | None = None
        self.err_image: bytes | None = None

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


_downloader: Downloader | None = None


def get_downloader():
    global _downloader
    if _downloader is None:
        _downloader = Downloader()
    return _downloader
