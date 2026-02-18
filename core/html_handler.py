import asyncio
from typing import Optional
from bs4 import BeautifulSoup

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

        last = soup.find('div', class_='grid gap-4 mt-6 sm:grid-cols-2').find_all('div')[-1]
        comp = last.find('svg').find_all('path')
        ex_link = True \
            if (comp[0].get('d') == 'M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71'
                and comp[1].get('d') == 'M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71') \
            else False

        third = last.find('span').get_text().split(': ') if ex_link else []

        title = soup.find('h1', class_='text-2xl font-bold leading-tight sm:text-3xl').get_text() if not third or third[0] != 'VNDB ID' else ''

        info = soup.find('div', class_='kun-prose max-w-none')
        entro = info.find_all('p', recursive=False)
        entro_text = '\n'.join([p.get_text() for p in entro])


        images = [img.get('src') for img in info.find('div', class_='data-kun-img-container').find_all('img')] \
            if info.find('div', class_='data-kun-img-container') \
            else []

        return TouchGalDetails(
            third_info=third,
            images=images,
            description=entro_text,
            title=title
        )




_handler: Optional[HTMLHandler] = None
def get_html_handler():
    global _handler
    if _handler is None:
        _handler = HTMLHandler()
    return _handler