"""Tests for `wildfire_composer.stac`."""

import datetime

import pytest

from wildfire_composer import stac
from wildfire_composer.config import StacConfig

BBOX = (8.0, 39.0, 9.0, 40.0)
REF_DATE = datetime.datetime(2024, 7, 1, 12, 0, 0)
DELTA = datetime.timedelta(days=15)


class FakeSearch:
    """Captures the search parameters and returns a canned item collection."""

    def __init__(self, items):
        self.items = items

    def item_collection(self):
        """Return the canned items."""
        return self.items


class FakeCatalog:
    """A stand-in for `pystac_client.Client` recording the search arguments."""

    def __init__(self, items=("item",)):
        self.items = list(items)
        self.kwargs: dict = {}

    def search(self, **kwargs):
        """Record the search arguments and hand back a `FakeSearch`."""
        self.kwargs = kwargs
        return FakeSearch(self.items)


@pytest.fixture
def cfg_stac():
    """A STAC configuration section."""
    return StacConfig(
        url="https://example.invalid/stac/v1",
        collection="sentinel-2-l2a",
        chunk_size=512,
        bands=["red", "green", "blue", "nir", "swir16", "scl"],
    )


def _search(catalog, cfg_stac, pre_fire, max_cloud=20.0):
    """Run `catalog_search` with the shared fixtures."""
    return stac.catalog_search(
        cfg_stac, catalog, BBOX, max_cloud, REF_DATE, DELTA, pre_fire
    )


def test_catalog_search_returns_the_item_collection(cfg_stac):
    """The items of the underlying search are returned unchanged."""
    catalog = FakeCatalog(items=["a", "b"])

    assert _search(catalog, cfg_stac, pre_fire=True) == ["a", "b"]


def test_catalog_search_pre_fire_window_ends_at_the_reference_date(cfg_stac):
    """A pre-fire search looks back over `delta` from the reference date."""
    catalog = FakeCatalog()

    _search(catalog, cfg_stac, pre_fire=True)

    assert catalog.kwargs["datetime"] == (
        f"{(REF_DATE - DELTA).isoformat()}/{REF_DATE.isoformat()}"
    )


def test_catalog_search_post_fire_window_starts_at_the_reference_date(cfg_stac):
    """A post-fire search looks forward over `delta` from the reference date."""
    catalog = FakeCatalog()

    _search(catalog, cfg_stac, pre_fire=False)

    assert catalog.kwargs["datetime"] == (
        f"{REF_DATE.isoformat()}/{(REF_DATE + DELTA).isoformat()}"
    )


@pytest.mark.parametrize(
    ("pre_fire", "expected"), [(True, "desc"), (False, "asc")]
)
def test_catalog_search_sorts_towards_the_fire(cfg_stac, pre_fire, expected):
    """Scenes closest in time to the event are ranked first."""
    catalog = FakeCatalog()

    _search(catalog, cfg_stac, pre_fire=pre_fire)

    assert catalog.kwargs["sortby"] == [
        {"field": "properties.eo:cloud_cover", "direction": "asc"},
        {"field": "properties.datetime", "direction": expected},
    ]


def test_catalog_search_filters_on_collection_bbox_and_cloud(cfg_stac):
    """The collection, bounding box and cloud threshold are passed through."""
    catalog = FakeCatalog()

    _search(catalog, cfg_stac, pre_fire=True, max_cloud=35.0)

    assert catalog.kwargs["collections"] == ["sentinel-2-l2a"]
    assert catalog.kwargs["bbox"] == BBOX
    assert catalog.kwargs["query"] == {"eo:cloud_cover": {"lt": 35.0}}


def test_load_from_stac_passes_the_configured_bands_and_chunks(
    cfg_stac, monkeypatch
):
    """`stac_load` receives the bands, chunk size and grid settings from config."""
    captured: dict = {}

    def fake_stac_load(items, **kwargs):
        captured["items"] = items
        captured.update(kwargs)
        return "dataset"

    monkeypatch.setattr(stac, "stac_load", fake_stac_load)

    result = stac.load_from_stac(cfg_stac, ["item"], BBOX)

    assert result == "dataset"
    assert captured["items"] == ["item"]
    assert captured["bands"] == cfg_stac.bands
    assert captured["chunks"] == {"x": 512, "y": 512}
    assert captured["bbox"] == BBOX
    assert captured["resolution"] == 10
    assert captured["crs"] == "utm"
    assert captured["groupby"] == "solar_day"
