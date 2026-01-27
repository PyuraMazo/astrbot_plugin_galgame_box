import asyncio
from typing import Optional
from bs4 import BeautifulSoup

from .api.const import id2command
from .api.type import TouchGalDetails


class _HTMLHandler:
    def __init__(self):
        pass

    async def initialize(self):
        pass

    async def terminate(self):
        pass

    async def handle_touchgal_details(self, text: str) -> TouchGalDetails | None:
        soup = await asyncio.to_thread(lambda: BeautifulSoup(text, 'lxml'))

        last = soup.find('div', class_='grid gap-4 mt-6 sm:grid-cols-2').find_all('div')[-1].find('a').get_text()
        vndb_id = last if last[0] in id2command.keys() else ''


        info = soup.find('div', class_='kun-prose max-w-none')
        entro = info.find_all('p', recursive=False)
        entro_text = '\n'.join([p.get_text() for p in entro])


        image = info.find('div', class_='data-kun-img-container').find_all('img')
        images = [img.get('src') for img in image]

        return TouchGalDetails(
            vndb_id=vndb_id,
            images=images,
            description=entro_text
        )




_handler: Optional[_HTMLHandler] = None
def get_handler():
    global _handler
    if _handler is None:
        _handler = _HTMLHandler()
    return _handler