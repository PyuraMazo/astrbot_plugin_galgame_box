from pydantic import BaseModel


class Image(BaseModel):
    url: str


class Developer(BaseModel):
    id: str
    original: str | None = None
    name: str


class Title(BaseModel):
    lang: str
    title: str
    official: bool


class Vn(BaseModel):
    id: str
    alttitle: str | None = None
    title: str | None = None
    image: Image | None = None
    rating: float | None = None


class Extlink(BaseModel):
    id: str
    label: str


class VNDBVnResponse(BaseModel):
    id: str
    rating: float | None = None
    released: str | None = None
    alttitle: str | None = None
    title: str
    image: Image
    average: float | None = None
    length_minutes: int | None = None
    platforms: list[str] | None = None
    aliases: list[str] | None = None
    developers: list[Developer] | None = None
    titles: list[Title] | None = None


class VNDBCharacterResponse(BaseModel):
    id: str
    name: str
    original: str | None = None
    birthday: list[int] | None = None
    image: Image | None = None
    vns: list[Vn] | None = None
    aliases: list[str] | None = None
    sex: list[str] | None = None
    waist: int | None = None
    hips: int | None = None
    bust: int | None = None
    blood_type: str | None = None
    weight: int | None = None
    height: int | None = None
    cup: str | None = None


class VNDBProducerResponse(BaseModel):
    id: str
    name: str
    original: str | None = None
    aliases: list[str] | None = None
    lang: str | None = None
    type: str | None = None


class VNDBReleaseResponse(BaseModel):
    id: str
    extlinks: list[Extlink]
    vns: list[Vn]
