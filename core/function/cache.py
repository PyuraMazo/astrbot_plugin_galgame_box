import asyncio
import os
import shutil
from pathlib import Path
from typing import Literal

from astrbot.api import AstrBotConfig
from astrbot.api.star import StarTools

from ..type.inner_models import bs64
from ..utils import File, Image


class Cache:
    cache_path = StarTools.get_data_dir("astrbot_plugin_galgame_box") / "cache"
    err_path = Path(__file__).parent / ".." / ".." / "resources" / "image" / "error.jpg"

    def __init__(self):
        os.makedirs(self.cache_path, exist_ok=True)

    @classmethod
    async def initialize(cls, config: AstrBotConfig):
        cls.err_image = await File.read_buffer2base64(cls.err_path)
        cls.clean_on_restart = config.get("basicSetting", {}).get(
            "cleanOnRestart", False
        )

        return cls()

    async def terminate(self):
        if self.clean_on_restart:
            await self.clean_cache()

    async def read_cache(
        self, group: Literal["vndb", "touchgal"], url: str, prefix: bool = True
    ) -> bs64 | None:
        filename, source_suffix = self._convert(group, url)
        file_path = self.cache_path / filename

        if file_path.exists():
            base64_prefix = await File.read_text(file_path)
            return base64_prefix if prefix else File.erase_base64_prefix(base64_prefix)
        else:
            return None

    async def write_cache(
        self,
        group: Literal["vndb", "touchgal"],
        url: str,
        buffer: bytes,
        prefix: bool = True,
    ) -> bs64 | None:
        filename, source_suffix = self._convert(group, url)
        file_path = self.cache_path / filename

        if source_suffix not in ("jpg", "jpeg"):
            buffer = await Image.image2jpg_async(buffer)
        bs64_image = await File.buffer2base64(buffer)
        await File.write_text(file_path, bs64_image)
        return bs64_image if prefix else File.erase_base64_prefix(bs64_image)

    async def clean_cache(self):
        if os.path.exists(self.cache_path):
            await asyncio.to_thread(shutil.rmtree, self.cache_path)
        await self._create_dir()

    def _convert(
        self, group: Literal["vndb", "touchgal"], link: str
    ) -> tuple[Path, str]:
        left, _ = link.rsplit(".", maxsplit=1)
        if group == "vndb":
            return (
                self.cache_path / f"{group}_{left.rsplit('/', maxsplit=1)[1]}",
                left.lower(),
            )
        else:
            split_count = 3 if "banner" in link else 1
            return (
                self.cache_path
                / f"{group}_{left.rsplit('/', maxsplit=split_count)[1]}",
                left.lower(),
            )

    def _check_cache(self, path: str) -> bool:
        return os.path.exists(path)

    async def _create_dir(self):
        os.makedirs(self.cache_path, exist_ok=True)
