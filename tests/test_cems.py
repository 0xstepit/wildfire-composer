"""Tests for `wildfire_composer.cems`."""

import dataclasses

import pytest

from wildfire_composer.cems import Product, ProductStatusCode, ProductType


def test_product_status_codes():
    """The status codes cover the CEMS vocabulary."""
    assert ProductStatusCode.F.value == "Finished"
    assert ProductStatusCode.W.value == "Waiting for data"
    assert ProductStatusCode.I.value == "In production"
    assert ProductStatusCode.N.value == "No visible impact/Product not feasible"
    assert [member.name for member in ProductStatusCode] == ["F", "N", "W", "I"]


def test_product_types():
    """The product types cover the Rapid Mapping portfolio."""
    assert ProductType.GRA.value == "Grading Product"
    assert ProductType.FEP.value == "First Estimate Product"
    assert ProductType.DEL.value == "Delineation Product"
    assert ProductType.REF.value == "Reference Product"
    assert ProductType.SR.value == "Situational Reporting"


@pytest.mark.parametrize("enum", [ProductStatusCode, ProductType])
def test_enums_are_addressable_by_name(enum):
    """Members can be looked up by the short code used by the CEMS API."""
    for member in enum:
        assert enum[member.name] is member


def test_product_is_frozen():
    """`Product` is an immutable value object."""
    product = Product(
        type=ProductType.GRA,
        status=ProductStatusCode.F,
        name="sardinia",
        extent="POLYGON ((0 0, 0 1, 1 1, 1 0, 0 0))",
        delivery_time="2024-07-12T00:00:00",
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        product.name = "other"
