import asyncio
from PIL import Image as PILImage
from io import BytesIO



class Image:
    @staticmethod
    def image2jpg(image_data: bytes) -> bytes:

        if not image_data:
            raise ValueError("图片数据为空")

        img = PILImage.open(BytesIO(image_data))
        try:
            if img.mode == 'RGBA':
                if img.getchannel('A').getextrema() != (255, 255):
                    background = PILImage.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])
                    img = background
                else:
                    img = img.convert('RGB')

            elif img.mode == 'P' and 'transparency' in img.info:
                img = img.convert('RGBA')
                return Image._image2jpg_simple(img)

            elif img.mode == 'LA':
                img = img.convert('RGBA')
                return Image._image2jpg_simple(img)

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
    def _image2jpg_simple(img: PILImage.Image) -> bytes:
        if img.mode == 'RGBA':
            if img.getchannel('A').getextrema() != (255, 255):
                background = PILImage.new('RGB', img.size, (255, 255, 255))
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
        return await asyncio.to_thread(Image.image2jpg, image_data)