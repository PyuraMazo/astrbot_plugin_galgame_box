import asyncio

from bs4 import BeautifulSoup

from ..type.exceptions import SettingException
from ..type.inner_models import TouchGalDetails


class HTMLHandler:
    @staticmethod
    async def handle_touchgal_details(text: str) -> TouchGalDetails:
        soup = await asyncio.to_thread(lambda: BeautifulSoup(text, "html.parser"))

        try:
            last = soup.find("div", class_="grid gap-4 mt-6 sm:grid-cols-2").find_all(
                "div"
            )[-1]
            comp = last.find("svg").find_all("path")
            ex_link = (
                True
                if (
                    comp[0].get("d")
                    == "M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"
                    and comp[1].get("d")
                    == "M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"
                )
                else False
            )

            third = last.find("span").get_text().split(": ") if ex_link else []

            title = (
                soup.find(
                    "h1", class_="text-2xl font-bold leading-tight sm:text-3xl"
                ).get_text()
                if not third or third[0] != "VNDB ID"
                else ""
            )

            info = soup.find("div", class_="kun-prose max-w-none")
            entro = info.find_all("p", recursive=False)
            entro_text = "\n".join([p.get_text() for p in entro])

            images = (
                [
                    img.get("src")
                    for img in info.find(
                        "div", class_="data-kun-img-container"
                    ).find_all("img")
                ]
                if info.find("div", class_="data-kun-img-container")
                else []
            )

            return TouchGalDetails(
                third_info=third, previews=images, description=entro_text, title=title
            )
        except AttributeError:
            raise SettingException("TouchGal登录账号Token")
