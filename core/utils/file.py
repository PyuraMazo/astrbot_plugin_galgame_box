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
    async def write_buffer(path: str | bytes, data: bytes) -> bool:
        if os.path.exists(path): raise FileExistsError(path)

        async with aiofiles.open(path, 'wb') as f:
            await f.write(data)
            return True

    @staticmethod
    async def read_buffer2base64(path: str) -> str:
        if not os.path.exists(path): raise FileNotFoundError(path)

        mime_type = const.MIME_TYPE[path.split('.')[-1]]
        async with aiofiles.open(path, 'rb') as f:
            buffer = await f.read()
            base64_data = await asyncio.to_thread(base64.b64encode, buffer)
            return f'data:{mime_type};base64,{base64_data.decode()}'

    @staticmethod
    async def buffer2base64(file_buffer: bytes, prefix: bool = True, extend: str = 'jpg') -> str:
        mime_type = const.MIME_TYPE[extend]
        base64_data = await asyncio.to_thread(base64.b64encode, file_buffer)
        return f'data:{mime_type};base64,{base64_data.decode("utf-8")}' if prefix else base64_data.decode('utf-8')

    @staticmethod
    def avif2jpg(avif_data: bytes) -> bytes:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(avif_data))

        if img.mode != 'RGB':
            img = img.convert('RGB')

        buffer = io.BytesIO()
        img.save(buffer, 'JPEG')

        return buffer.getvalue()

    @staticmethod
    async def avif2jpg_async(avif_data: bytes) -> bytes:
        return await asyncio.to_thread(File.avif2jpg, avif_data)