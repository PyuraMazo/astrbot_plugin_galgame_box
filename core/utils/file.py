import asyncio
import base64
import os
import re
from pathlib import Path

import aiofiles

from ..type.inner_models import bs64, mime_type


class File:
    @staticmethod
    async def read_buffer(path: str | Path) -> bytes:
        if not os.path.exists(path):
            raise FileNotFoundError(path)

        async with aiofiles.open(path, "rb") as f:
            return await f.read()

    @staticmethod
    async def read_text(path: str | Path) -> str:

        if not os.path.exists(path):
            raise FileNotFoundError(path)

        async with aiofiles.open(path, encoding="utf-8") as f:
            return await f.read()

    @staticmethod
    async def read_buffer2base64(path: str | Path) -> bs64:
        if not os.path.exists(path):
            raise FileNotFoundError(path)

        mime = mime_type[str(path).split(".")[-1]]
        async with aiofiles.open(path, "rb") as f:
            buffer = await f.read()
            base64_data = await asyncio.to_thread(base64.b64encode, buffer)
            return f"data:{mime};base64,{base64_data.decode()}"

    @staticmethod
    async def write_buffer(path: str | Path, data: bytes) -> bool:
        async with aiofiles.open(path, "wb") as f:
            await f.write(data)
            return True

    @staticmethod
    async def write_text(path: str | Path, data: str) -> bool:
        if os.path.exists(path):
            return False

        async with aiofiles.open(path, "w") as f:
            await f.write(data)
            return True

    @staticmethod
    def erase_base64_prefix(base64_str: bs64):
        pattern = r"^data:[^;]+;base64,"
        return re.sub(pattern, "", base64_str)

    @staticmethod
    async def buffer2base64(
        file_buffer: bytes, prefix: bool = True, suffix: str = "jpg"
    ) -> bs64:
        mime = mime_type[suffix]
        base64_str = await asyncio.to_thread(base64.b64encode, file_buffer)
        return (
            f"data:{mime};base64,{base64_str.decode('utf-8')}"
            if prefix
            else base64_str.decode("utf-8")
        )

    @classmethod
    def base64_to_buffer(cls, base64_str: bs64) -> bytes:
        return base64.b64decode(
            cls.erase_base64_prefix(base64_str)
            if base64_str.startswith("data:")
            else base64_str
        )

    @classmethod
    async def copy_delete(cls, path_before: str, path_after: str) -> bool:
        if not os.path.exists(path_before) or os.path.exists(path_after):
            return False

        buf = await cls.read_buffer(path_before)
        await cls.write_buffer(path_after, buf)
        os.remove(path_before)
        return True
