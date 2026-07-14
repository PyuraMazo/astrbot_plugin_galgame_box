from astrbot.api import AstrBotConfig

from ..services import Services
from ..type.exceptions import Tips
from ..type.outer_models import AnimeTraceResponse
from . import Http


class AnimeTrece:
    search_url = "https://api.animetrace.com/v1/search"
    model_url = "https://api.animetrace.com/v1/model/list"

    current_model = ""

    @classmethod
    async def initialize(cls, config: AstrBotConfig):
        cls.http = Services.get(Http)
        await cls.select_model()

        return cls()

    async def request_find(
        self, url: str, try_again: bool = False
    ) -> AnimeTraceResponse:
        resp = await self.http.post(
            self.search_url, self._build_payload(url, self.current_model)
        )
        # 特定检测状态码
        code = resp.get("code", 400)
        if code == 17703 and not try_again:
            await self.select_model()
            return await self.request_find(url, True)

        if code != 200 and code != 0:
            raise Tips(resp.get("zh_message", "识别失败。"))

        return AnimeTraceResponse.model_validate(resp)

    def _build_payload(self, url: str, model: str):
        base = {"model": model, "ai_detect": 1}
        if url.startswith("http"):
            base["url"] = url
        else:
            base["base64"] = url
        return base

    @classmethod
    async def select_model(cls):
        resp: dict = await cls.http.get(cls.model_url, "json")
        if resp["message"] == "success":
            for model in resp["data"]:
                if model["enabled"]:
                    cls.current_model = model["id"]
                    return
            else:
                raise Tips(resp.get("message", "无可用模型。"))
        else:
            raise Tips(resp.get("message", "模型获取失败。"))
