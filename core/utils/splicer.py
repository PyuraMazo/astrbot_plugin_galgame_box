# type: ignore

from ..type.inner_models import (
    develop_type,
    gender,
    lang,
)
from ..type.outer_models import (
    Developer,
    Link,
    Title,
    Vn,
)


def empty_handler(part_null=False):
    def decorator(func):
        def wrapper(self, *args):
            disable = [i for i in args if not i]
            if not disable or (part_null and len(disable) < len(args)):
                func(self, *args)
            return self

        return wrapper

    return decorator


class Splicer:
    scheme: str

    _vndb_id = ""
    _average = ""
    _rating = ""
    _release = ""
    _length = ""
    _platform = ""
    _alias = ""
    _producer = ""
    _titles = ""

    _name = ""
    _birthday = ""
    _vns = ""
    _blood = ""
    _wh = ""
    _gender_outer = ""
    _gender_inner = ""
    _bwh = ""
    _cup = ""

    _text_lang = ""
    _co_type = ""

    _touchgal_id = ""
    _touchgal_score = ""
    _touchgal_tag = ""
    _touchgal_type = ""
    _touchgal_platform = ""
    _touchgal_language = ""

    _resource_title = ""
    _resource_category = ""
    _resource_tag = ""
    _resource_note = ""
    _resource_links = ""

    def __init__(self, scheme: str):
        self.scheme = scheme

    def do(self) -> list[str]:
        if self.scheme == "vn":
            elements = (
                self._vndb_id,
                self._titles,
                self._alias,
                self._rating,
                self._average,
                self._length,
                self._producer,
                self._release,
                self._platform,
            )
        elif self.scheme == "character":
            elements = (
                self._vndb_id,
                self._birthday,
                self._vns,
                self._blood,
                self._wh,
                self._gender_outer,
                self._gender_inner,
                self._bwh,
                self._cup,
            )
        elif self.scheme == "producer":
            elements = (
                self._name,
                self._vndb_id,
                self._alias,
                self._text_lang,
                self._co_type,
            )
        elif self.scheme == "touchgal":
            elements = (
                self._touchgal_id,
                self._touchgal_tag,
                self._touchgal_score,
                self._touchgal_language,
                self._touchgal_type,
                self._touchgal_platform,
            )
        elif self.scheme == "resource":
            elements = (
                self._resource_title,
                self._resource_category,
                self._touchgal_platform,
                self._resource_tag,
                self._touchgal_language,
                self._resource_note,
                self._resource_links,
            )
        else:
            raise ValueError(f"错误的Splider类型：{self.scheme}")

        return [i for i in elements if i]

    @classmethod
    def from_vndb_vn(cls):
        return cls("vn")

    @classmethod
    def from_vndb_character(cls):
        return cls("character")

    @classmethod
    def from_vndb_producer(cls):
        return cls("producer")

    @classmethod
    def from_touchgal_info(cls):
        return cls("touchgal")

    @classmethod
    def from_touchgal_resource(cls):
        return cls("resource")

    @empty_handler()
    def vndb_id(self, id: str) -> "Splicer":
        self._vndb_id = f"VNDB ID：{id}"

    @empty_handler()
    def average(self, avg: str) -> "Splicer":
        self._average = f"平均分：{avg}"

    @empty_handler()
    def rating(self, rating: str) -> "Splicer":
        self._rating = f"贝叶斯评分：{rating}"

    @empty_handler()
    def release(self, release: str) -> "Splicer":
        self._release = f"发布日期：{release}"

    @empty_handler()
    def length(self, length: int) -> "Splicer":
        self._length = f"游玩时间：{round(length / 60, 1)}小时"

    @empty_handler()
    def platform(self, platform: str) -> "Splicer":
        self._platform = f"支持平台：{'、'.join(platform)}"

    @empty_handler()
    def alias(self, alias: str) -> "Splicer":
        self._alias = f"{'别名' if self.scheme == 'vn' else '别称'}：{'、'.join(alias)}"

    @empty_handler()
    def producer(self, producer: list[Developer]) -> "Splicer":
        pro = [f"{p.original or p.name}（{p.id}）" for p in producer]
        self._producer = f"制作者（VNDB ID）：{'、'.join(pro)}"

    @empty_handler()
    def titles(self, titles: list[Title]) -> "Splicer":
        lang_list = []
        for title in titles:
            if title.lang in lang:
                lang_list.append(
                    f"{lang[title.lang]}标题（{'官方' if title.official else '非官方'}）：{title.title}"
                )
        self._titles = "<br>".join(lang_list)

    @empty_handler()
    def name(self, original: str | None, name: str) -> "Splicer":
        self._name = original or name

    @empty_handler()
    def birthday(self, birthday: list[int]) -> "Splicer":
        self._birthday = f"生日：{birthday[0]}月{birthday[1]}日"

    @empty_handler()
    def vns(self, vns: list[Vn]) -> "Splicer":
        vn_list = [f"「{vn.alttitle or vn.title}」（{vn.id}）" for vn in vns]
        self._vns = f"出场作品（VNDB ID）：{'、'.join(vn_list)}"

    @empty_handler()
    def blood(self, blood: str) -> "Splicer":
        self._blood = f"血型：{blood}"

    @empty_handler(part_null=True)
    def wh(self, weight: int | None, height: int | None) -> "Splicer":
        self._wh = f"身高/体重（cm/kg）：{height or '??'}/{weight or '??'}"

    @empty_handler()
    def gender_o(self, sex: list[str]) -> "Splicer":
        self._gender_outer = f"性别：{gender[sex[0]]}"

    @empty_handler()
    def gender_i(self, sex: list[str]) -> "Splicer":
        self._gender_inner = f"真实性别：{gender[sex[1]]}"

    @empty_handler(part_null=True)
    def bwh(self, bust: int | None, waist: int | None, hips: int | None) -> "Splicer":
        self._bwh = f"三围：{bust or '??'}-{waist or '??'}-{hips or '??'}"

    @empty_handler()
    def cup(self, cup: str) -> "Splicer":
        self._cup = f"罩杯：{cup}"

    @empty_handler()
    def text_lang(self, language: str) -> "Splicer":
        self._text_lang = f"文本语言：{lang[language]}" if language in lang else ""

    @empty_handler()
    def co_type(self, co_type: str) -> "Splicer":
        self._co_type = f"类型：{develop_type[co_type]}"

    @empty_handler()
    def touchgal_id(self, id: int) -> "Splicer":
        self._touchgal_id = f"TouchGal ID：{id}"

    @empty_handler()
    def touchgal_score(self, avg: float) -> "Splicer":
        self._touchgal_score = f"站内评分：{avg}"

    @empty_handler()
    def touchgal_type(self, type: str) -> "Splicer":
        self._touchgal_type = f"资源属性：{'、'.join(type)}"

    @empty_handler()
    def touchgal_platforms(self, platforms: list[str]) -> "Splicer":
        self._touchgal_platform = f"资源平台：{'、'.join(platforms)}"

    @empty_handler()
    def touchgal_tags(self, tags: list[str]) -> "Splicer":
        self._touchgal_tag = f"标签：{'、'.join(tags)}"

    @empty_handler()
    def touchgal_lang(self, languages: list[str]) -> "Splicer":
        lang_list = []
        for i in languages:
            if i in lang:
                lang_list.append(lang[i])
        self._touchgal_language = f"资源语言：{'、'.join(lang_list)}"

    @empty_handler()
    def resource_title(self, title: str) -> "Splicer":
        self._resource_title = f"标题：{title}"

    @empty_handler()
    def resource_category(self, category: list[str]) -> "Splicer":
        self._resource_category = f"类型：{category}"

    @empty_handler()
    def resource_tags(self, tags: list[str]) -> "Splicer":
        self._resource_tag = f"标签：{'、'.join(tags)}"

    @empty_handler()
    def resource_note(self, note: str) -> "Splicer":
        self._resource_note = f"备注：{note}"

    @empty_handler()
    def resource_links(self, links: list[Link]) -> "Splicer":
        links_list = []
        for j in links:
            gap = "-" * 10
            storage = f"资源平台：{j.storage}" if j.storage else ""
            size = f"文件大小：{j.size}" if j.size else ""
            content = f"链接：{j.content}" if j.content else ""
            code = f"提取码：{j.code}" if j.code else ""
            password = f"解压码：{j.password}" if j.password else ""
            links_list.append(
                "\n".join(
                    [k for k in [gap, storage, size, content, code, password] if k]
                )
            )
        self._resource_links = "\n".join(links_list)
