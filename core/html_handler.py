import asyncio
from typing import Optional
from bs4 import BeautifulSoup

from .api.const import id2command
from .api.type import TouchGalDetails


class HTMLHandler:
    def __init__(self):
        pass

    async def initialize(self):
        pass

    async def terminate(self):
        pass

    async def handle_touchgal_details(self, text: str) -> TouchGalDetails | None:
        soup = await asyncio.to_thread(lambda: BeautifulSoup(text, 'html.parser'))

        last = soup.find('div', class_='grid gap-4 mt-6 sm:grid-cols-2').find_all('div')[-1].find('a')
        vndb_id = last.get_text() if last else ''
        title = soup.find('h1', class_='text-2xl font-bold leading-tight sm:text-3xl').get_text() if not vndb_id else ''


        info = soup.find('div', class_='kun-prose max-w-none')
        entro = info.find_all('p', recursive=False)
        entro_text = '\n'.join([p.get_text() for p in entro])


        image = info.find('div', class_='data-kun-img-container').find_all('img')
        images = [img.get('src') for img in image]

        return TouchGalDetails(
            vndb_id=vndb_id,
            images=images,
            description=entro_text,
            title=title
        )




_handler: Optional[HTMLHandler] = None
def get_handler():
    global _handler
    if _handler is None:
        _handler = HTMLHandler()
    return _handler