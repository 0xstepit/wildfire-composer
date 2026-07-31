import tomllib
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CemsConfig:
    url: str
    url_extended: str


@dataclass(frozen=True)
class StacConfig:
    url: str
    collection: str
    chunk_size: int
    bands: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class IoConfig:
    img_dir: str
    raster_dir: str
    db: str


@dataclass
class Config:
    stac: StacConfig
    cems: CemsConfig
    io: IoConfig

    @classmethod
    def load(cls, path: str) -> "Config":
        with open(path, "rb") as f:
            raw = tomllib.load(f)

        stac = StacConfig(**raw.pop("stac"))
        cems = CemsConfig(**raw.pop("cems"))
        io = IoConfig(**raw.pop("io"))

        return cls(stac=stac, cems=cems, io=io)
