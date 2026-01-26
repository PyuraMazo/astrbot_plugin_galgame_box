import asyncio
from bs4 import BeautifulSoup

from astrbot.api import logger

from .api.type import TouchGalDetails
from .api import const


class Handler:
    async def handle_touchgal_details(self, text: str) -> TouchGalDetails | None:
        soup = await asyncio.to_thread(lambda: BeautifulSoup(text, 'lxml'))
        vndb_id = ''
        try:
            last = soup.find('div', class_='grid gap-4 mt-6 sm:grid-cols-2').find_all('div')[-1].find('a').get_text()
            vndb_id = last if last[0] in const.id2command.keys() else ''
        except Exception as e:
            logger.error('bs4解析错误' + str(e))

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



