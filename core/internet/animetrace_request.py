from astrbot.api import AstrBotConfig

from ..api.exception import CodeException
from ..api.model import AnimeTraceResponse
from .http import Http, get_http


class AnimeTreceRequest:
    def __init__(self):
        self.api_url = "https://api.animetrace.com/v1/search"

        self.http: Http | None = None

    async def initialize(self, config: AstrBotConfig):
        self.http = get_http()

        await self.http.initialize(config)

    async def terminate(self):
        await self.http.terminate()

    async def request_find(
        self, url: str, model: str = "animetrace-yuri-4.2"
    ) -> AnimeTraceResponse:
        resp = await self.http.post(self.api_url, self._build_payload(model, url))
        # 特定检测状态码
        code = resp.get("code", 400)
        if code != 200 and code != 0:
            raise CodeException(code)

        return AnimeTraceResponse.model_validate(resp)

    def _build_payload(self, model: str, url: str):
        base = {"model": model, "ai_detect": 1}
        if url.startswith("http"):
            base["url"] = url
        else:
            base["base64"] = url
        return base


_animetrace_request: AnimeTreceRequest | None = None


def get_animetrace_request():
    global _animetrace_request
    if _animetrace_request is None:
        _animetrace_request = AnimeTreceRequest()
    return _animetrace_request
