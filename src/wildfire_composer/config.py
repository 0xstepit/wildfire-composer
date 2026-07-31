import tomllib
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Cems:
    url: str
    url_extended: str


@dataclass(frozen=True)
class AOI:
    name: str
    region: str
    latlon: tuple[float, float]
    dates: tuple[str, str]
    time_buffer_days: int
    max_cloud_coverage: float
    edge: int

    @property
    def lat(self) -> float:
        return self.latlon[0]

    @property
    def lon(self) -> float:
        return self.latlon[1]

    @property
    def start(self) -> str:
        return self.dates[0]

    @property
    def end(self) -> str:
        return self.dates[1]


@dataclass(frozen=True)
class StacConfig:
    url: str
    collection: str
    chunk_size: int
    bands: list[str] = field(default_factory=list)


@dataclass
class Config:
    stac: StacConfig
    cems: Cems
    aois: dict[str, AOI] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str) -> "Config":
        with open(path, "rb") as f:
            raw = tomllib.load(f)

        aois = {
            name: AOI(
                name=str(name),
                region=entry["region"],
                latlon=(float(entry["latlon"][0]), float(entry["latlon"][1])),
                dates=tuple(entry["dates"]),
                time_buffer_days=entry["time_buffer_days"],
                max_cloud_coverage=entry["max_cloud_coverage"],
                edge=entry["edge"],
            )
            for name, entry in raw["aois"].items()
        }

        stac = StacConfig(**raw.pop("stac"))
        cems = Cems(**raw.pop("cems"))

        return cls(
            stac=stac,
            cems=cems,
            aois=aois,
        )
