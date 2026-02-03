import asyncio
import base64
import os
import aiofiles


from ..api import const

class File:
    @staticmethod
    async def read_buffer(path: str) -> bytes:
        if not os.path.exists(path): raise FileNotFoundError(path)

        async with aiofiles.open(path, 'rb') as f:
            return await f.read()

    @staticmethod
    async def read_text(path: str) -> str:

        if not os.path.exists(path): raise FileNotFoundError(path)

        async with aiofiles.open(path, 'r', encoding='utf-8') as f:
            return await f.read()


    @staticmethod
    async def read_buffer2base64(path: str) -> str:
        if not os.path.exists(path): raise FileNotFoundError(path)

        mime_type = const.MIME_TYPE[path.split('.')[-1]]
        async with aiofiles.open(path, 'rb') as f:
            buffer = await f.read()
            base64_data = await asyncio.to_thread(base64.b64encode, buffer)
            return f'data:{mime_type};base64,{base64_data.decode()}'

    @staticmethod
    async def write_buffer(path: str, data: bytes) -> bool:
        async with aiofiles.open(path, 'wb') as f:
            await f.write(data)
            return True

    @staticmethod
    async def write_base64(path: str, data: str) -> bool:
        if os.path.exists(path):
            return False

        async with aiofiles.open(path, 'w') as f:
            await f.write(data)
            return True

    @staticmethod
    async def write_text(path: str, data: str) -> bool:
        if os.path.exists(path):
            return False

        async with aiofiles.open(path, 'w') as f:
            await f.write(data)
            return True

    @staticmethod
    async def buffer2base64(file_buffer: bytes, prefix: bool = True, suffix: str = 'jpg') -> str:
        mime_type = const.MIME_TYPE[suffix]
        base64_data = await asyncio.to_thread(base64.b64encode, file_buffer)
        return f'data:{mime_type};base64,{base64_data.decode("utf-8")}' if prefix else base64_data.decode('utf-8')

    @staticmethod
    async def copy_delete(path_before: str, path_after: str) -> bool:
        if not os.path.exists(path_before) or os.path.exists(path_after):
            return False

        buf = await File.read_buffer(path_before)
        await File.write_buffer(path_after, buf)
        os.remove(path_before)
        return True