from pydantic import BaseModel


class Link(BaseModel):
    storage: str
    size: str
    content: str
    code: str
    password: str


class TouchGalWorkResponse(BaseModel):
    """
    id为TouchGal的全局ID
    uniqueId为作品ID，可以访问对应页面
    """

    id: int
    uniqueId: str
    banner: str
    name: str
    type: list[str]
    language: list[str]
    platform: list[str]
    averageRating: float
    # tags: list[str]


class TouchGalResourceResponse(BaseModel):
    id: int
    name: str
    section: str
    type: list[str]
    language: list[str]
    note: str
    platform: list[str]
    links: list[Link]
