import base64
import os.path as p
from typing import LiteralString

from ..api.type import Dict

class File:
    @staticmethod
    def read_buffer(path: LiteralString | str) -> bytes:
        if not p.exists(path): raise FileNotFoundError(path)

        with open(path, 'rb') as f:
            return f.read()

    @staticmethod
    def read_text(path: LiteralString | str) -> str:
        if not p.exists(path): raise FileNotFoundError(path)

        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    @staticmethod
    def write_buffer(path: LiteralString | str | bytes, data: bytes) -> bool:
        if p.exists(path): raise FileExistsError(path)

        with open(path, 'wb') as f:
            f.write(data)
            return True

    @staticmethod
    def read_base64(path: str) -> str:
        if not p.exists(path): raise FileNotFoundError(path)

        mime_type = Dict.MIME_TYPE[path.split('.')[-1]]
        with open(path, 'rb') as f:
            base64_data = base64.b64encode(f.read()).decode('utf-8')
            return f'data:{mime_type};base64,{base64_data}'

    @staticmethod
    def buffer2base64(file_buffer: bytes, prefix: bool = True, extend: str = 'jpg') -> str:
        mime_type = Dict.MIME_TYPE[extend]
        base64_data = base64.b64encode(file_buffer).decode('utf-8')
        return f'data:{mime_type};base64,{base64_data}' if prefix else base64_data

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