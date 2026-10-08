from pydantic import BaseModel


class Image(BaseModel):
    id: str | None = None
    url: str
    dims: list[int] | None = None
    sexual: float | None = None
    violence: float | None = None
    votecount: int | None = None
    thumbnail: str | None = None
    thumbnail_dims: list[int] | None = None


class Title(BaseModel):
    lang: str
    title: str
    latin: str | None = None
    official: bool
    main: bool | None = None


class ExternalLink(BaseModel):
    url: str
    label: str | None = None
    name: str | None = None


class Release(BaseModel):
    id: str | None = None
    title: str | None = None
    alttitle: str | None = None
    released: str | None = None
    platforms: list[str] | None = None
    languages: list[str] | None = None


class Screenshot(Image):
    release: Release | None = None


class Relation(BaseModel):
    relation: str
    relation_official: bool
    id: str | None = None
    title: str | None = None
    alttitle: str | None = None
    olang: str | None = None
    devstatus: int | None = None
    released: str | None = None
    languages: list[str] | None = None
    platforms: list[str] | None = None
    image: Image | None = None
    length: int | None = None
    length_minutes: int | None = None
    length_votes: int | None = None
    description: str | None = None
    average: float | None = None
    rating: float | None = None
    votecount: int | None = None


class Tag(BaseModel):
    rating: float
    spoiler: int
    lie: bool
    id: str | None = None
    name: str | None = None
    description: str | None = None
    category: str | None = None
    aliases: list[str] | None = None


class Developer(BaseModel):
    id: str | None = None
    name: str | None = None
    original: str | None = None
    type: str | None = None
    language: str | None = None
    aliases: list[str] | None = None
    description: str | None = None


class Edition(BaseModel):
    eid: int
    lang: str | None = None
    name: str
    official: bool


class Staff(BaseModel):
    eid: int | None = None
    role: str
    note: str | None = None
    id: str | None = None
    name: str | None = None
    original: str | None = None
    gender: str | None = None
    language: str | None = None
    aliases: list[str] | None = None
    description: str | None = None


class VN(BaseModel):
    id: str
    alttitle: str | None = None
    title: str | None = None
    image: Image | None = None
    rating: float | None = None


class VNDBVnResponse(BaseModel):
    id: str
    title: str
    image: Image
    alttitle: str | None = None
    titles: list[Title] | None = None
    aliases: list[str] | None = None
    olang: str | None = None
    devstatus: int | None = None
    released: str | None = None
    languages: list[str] | None = None
    platforms: list[str] | None = None
    length: int | None = None
    length_minutes: int | None = None
    length_votes: int | None = None
    description: str | None = None
    average: float | None = None
    rating: float | None = None
    votecount: int | None = None
    screenshots: list[Screenshot] | None = None
    relations: list[Relation] | None = None
    tags: list[Tag] | None = None
    developers: list[Developer] | None = None
    editions: list[Edition] | None = None
    staff: list[Staff] | None = None
    extlinks: list[ExternalLink] | None = None


class VNDBCharacterResponse(BaseModel):
    id: str
    name: str
    original: str | None = None
    aliases: list[str] | None = None
    description: str | None = None
    image: Image | None = None
    blood_type: str | None = None
    height: int | None = None
    weight: int | None = None
    bust: int | None = None
    waist: int | None = None
    hips: int | None = None
    cup: str | None = None
    age: int | None = None
    birthday: list[int] | None = None
    sex: list[str | None] | None = None
    gender: list[str | None] | None = None
    vns: list[VN] | None = None


class VNDBProducerResponse(BaseModel):
    id: str
    name: str
    original: str | None = None
    aliases: list[str] | None = None
    lang: str | None = None
    type: str | None = None
    description: str | None = None
    extlinks: list[ExternalLink] | None = None


class VNDBReleaseResponse(BaseModel):
    id: str
    extlinks: list[ExternalLink]
    vns: list[VN]
