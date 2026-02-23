from typing import Optional

from astrbot.api import AstrBotConfig

from .http import Http, get_http
from ..api.model import AnimeTraceResponse
from ..api.type import AnimeTraceModel
from ..api.exception import CodeException


class AnimeTreceRequest:
    def __init__(self):
        self.api_url = "https://api.animetrace.com/v1/search"

        self.http: Optional[Http] = None

    async def initialize(self, config: AstrBotConfig):
        self.http = get_http()

        await self.http.initialize(config)

    async def terminate(self):
        await self.http.terminate()

    async def request_find(
        self, url: str, model: AnimeTraceModel
    ) -> AnimeTraceResponse:
        resp = await self.http.post(self.api_url, self._build_payload(model, url))
        # 特定检测状态码
        code = resp.get("code", 400)
        if code != 200 and code != 0:
            raise CodeException(code)

        return AnimeTraceResponse.model_validate(resp)

    def _build_payload(self, model: AnimeTraceModel, url: str):
        return {"model": model.value, "ai_detect": 1, "url": url}


_animetrace_request: Optional[AnimeTreceRequest] = None


def get_animetrace_request():
    global _animetrace_request
    if _animetrace_request is None:
        _animetrace_request = AnimeTreceRequest()
    return _animetrace_request
