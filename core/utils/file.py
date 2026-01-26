import asyncio
import base64
import os
import aiofiles
from PIL import Image
from io import BytesIO

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
    async def write_buffer(path: str, data: bytes) -> bool:
        if os.path.exists(path):
            return False

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
    def image2jpg(image_data: bytes) -> bytes:

        if not image_data:
            raise ValueError("图片数据为空")

        img = Image.open(BytesIO(image_data))
        try:
            if img.mode == 'RGBA':
                if img.getchannel('A').getextrema() != (255, 255):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])
                    img = background
                else:
                    img = img.convert('RGB')

            elif img.mode == 'P' and 'transparency' in img.info:
                img = img.convert('RGBA')
                return File._image2jpg_simple(img)

            elif img.mode == 'LA':
                img = img.convert('RGBA')
                return File._image2jpg_simple(img)

            elif img.mode not in ['RGB', 'L']:
                img = img.convert('RGB')

            buffer = BytesIO()
            img.save(buffer, 'JPEG', quality=85)
            result = buffer.getvalue()

            return result

        except Exception as e:
            raise ValueError(f"图片转换失败: {e}")
        finally:
            if 'img' in locals():
                img.close()

    @staticmethod
    def _image2jpg_simple(img: Image.Image) -> bytes:
        if img.mode == 'RGBA':
            if img.getchannel('A').getextrema() != (255, 255):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            else:
                img = img.convert('RGB')
        elif img.mode not in ['RGB', 'L']:
            img = img.convert('RGB')

        buffer = BytesIO()
        img.save(buffer, 'JPEG', quality=85)
        return buffer.getvalue()

    @staticmethod
    async def image2jpg_async(image_data: bytes) -> bytes:
        return await asyncio.to_thread(File.image2jpg, image_data)