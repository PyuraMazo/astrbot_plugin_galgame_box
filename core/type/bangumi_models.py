from pydantic import BaseModel


class Images(BaseModel):
    small: str
    grid: str
    large: str
    medium: str
    common: str


class Tag(BaseModel):
    name: str
    count: int
    total_count: int


class Infobox(BaseModel):
    key: str
    value: str | list[dict[str, str]] | None = None


class Rating(BaseModel):
    rank: int
    total: int
    count: dict[str, int]
    score: float


class Collection(BaseModel):
    on_hold: int
    dropped: int
    wish: int
    collect: int
    doing: int


class BangumiSubjectResponse(BaseModel):
    id: int
    name: str
    type: int | None = None
    name_cn: str | None = None
    date: str | None = None
    platform: str | None = None
    image: str | None = None
    images: Images | None = None
    summary: str | None = None
    tags: list[Tag] | None = None
    infobox: list[Infobox] | None = None
    rating: Rating | None = None
    collection: Collection | None = None
    eps: int | None = None
    total_episodes: int | None = None
    meta_tags: list[str] | None = None
    volumes: int | None = None
    series: bool | None = None
    locked: bool | None = None
    nsfw: bool | None = None
