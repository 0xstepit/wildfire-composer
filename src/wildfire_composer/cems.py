from dataclasses import dataclass
from enum import Enum


class ProductStatusCode(Enum):
    F = "Finished"
    N = "No visible impact/Product not feasible"
    W = "Waiting for data"
    I = "In production"


# https://mapping.emergency.copernicus.eu/about/rapid-mapping-portfolio/
class ProductType(Enum):
    FEP = "First Estimate Product"
    DEL = "Delineation Product"
    GRA = "Grading Product"
    REF = "Reference Product"
    SR = "Situational Reporting"


@dataclass(frozen=True)
class Product:
    type: ProductType
    status: ProductStatusCode
    name: str
    extent: str
    delivery_time: str
