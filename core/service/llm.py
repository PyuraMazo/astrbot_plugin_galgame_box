from astrbot.api import AstrBotConfig
from astrbot.core.star import Context

from ..type.prompts import TRANSLATION_PROMPTS


class LLM:
    @classmethod
    async def initialize(cls, context: Context, config: AstrBotConfig):
        provider_manager = context.provider_manager
        provider_id = config.get("basicSetting", {}).get("translationProvider", "")
        cls.provider = (
            await provider_manager.get_provider_by_id(provider_id)
            if provider_manager
            else None
        )

        return cls()

    async def generate(self, prompt: str, **kwargs) -> str | None:
        if self.provider is None:
            return None

        kwargs.pop("prompt", None)
        llm_resp = await self.provider.text_chat(prompt=prompt, **kwargs)
        return llm_resp.completion_text

    async def translate(self, source: str) -> str | None:
        prompt = TRANSLATION_PROMPTS.replace("{{text}}", source)
        return await self.generate(prompt)
