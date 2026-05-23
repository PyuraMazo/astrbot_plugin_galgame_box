from pathlib import Path
from jinja2 import Template

from astrbot.core.star import StarTools
from data.plugins.astrbot_plugin_galgame_box.core.api.const import html_list
from data.plugins.astrbot_plugin_galgame_box.core.api.type import UnrenderedData
from data.plugins.astrbot_plugin_galgame_box.core.utils.file import File


class Renderer:
    def __init__(self):
        self.template_dir = Path(__file__).parent / ".." / ".." / "resources" / "template"
        self.templates: dict[str, Template] = {}

    async def initialize(self):
        await self._load_template()

    async def _load_template(self):
        for i, j in html_list.items():
            if j not in self.templates:
                html_str = await File.read_text(self.template_dir / j)
                self.templates[j] = Template(html_str)

    def _local_render(self, template_name: str, data: UnrenderedData):
        return self.templates[html_list[template_name]].render(**data.model_dump())

    async def render_as_file(self, template_name: str, data: UnrenderedData, filename: str | Path):
        from playwright.async_api import async_playwright
        cache_dir = StarTools.get_data_dir("astrbot_plugin_galgame_box") / "cache" / f"{filename}.png"
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_content(self._local_render(template_name, data))
            await page.screenshot(path=cache_dir, full_page=True)
            await browser.close()
            print(f"长截图已保存: {cache_dir}")
        print("成功")