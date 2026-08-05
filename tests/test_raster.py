"""Tests for `wildfire_composer.raster`."""

import dataclasses
from csv import Error
from datetime import datetime

import numpy as np
import pytest
import xarray as xr

from wildfire_composer import raster
from wildfire_composer.config import StacConfig
from wildfire_composer.raster import (
    FALSE_BANDS,
    RGB_BANDS,
    Aoi,
    CompositeKind,
    create_composite,
    fetch_and_store_data,
    get_raster_by_kind,
    get_rasters,
    mask_scl_noise,
    rescale_reflectance,
)

BANDS = ["red", "green", "blue", "nir", "swir16", "scl"]
EXTENT = "POLYGON ((8 39, 8 40, 9 40, 9 39, 8 39))"


@pytest.fixture
def cfg_stac():
    """A STAC configuration section listing the six bands the pipeline uses."""
    return StacConfig(
        url="https://example.invalid/stac/v1",
        collection="sentinel-2-l2a",
        chunk_size=512,
        bands=list(BANDS),
    )


def make_dataset(scl_values=None, reflectance=1000, ntime=2, size=2):
    """Build a (time, y, x) dataset with one variable per band."""
    shape = (ntime, size, size)
    data = {
        band: (("time", "y", "x"), np.full(shape, reflectance, dtype="int16"))
        for band in BANDS
        if band != "scl"
    }
    scl = np.full(shape, 4, dtype="int16") if scl_values is None else scl_values
    data["scl"] = (("time", "y", "x"), np.asarray(scl, dtype="int16"))
    return xr.Dataset(data, coords={"time": np.arange(ntime)})


def make_composite(size=2):
    """Build a (band, time, y, x) composite like the one written to zarr."""
    rng = np.random.default_rng(0)
    values = rng.random((len(BANDS) - 1, 2, size, size), dtype="float32")
    return xr.DataArray(
        values,
        dims=("band", "time", "y", "x"),
        coords={
            "band": [band for band in BANDS if band != "scl"],
            "time": ["pre", "post"],
        },
    )


def test_aoi_is_frozen():
    """`Aoi` is an immutable value object."""
    aoi = Aoi(name="sardinia", countries="Italy", extent=EXTENT)

    with pytest.raises(dataclasses.FrozenInstanceError):
        aoi.name = "other"


def test_composite_kind_members():
    """The supported composite kinds are stable identifiers."""
    assert {kind.value for kind in CompositeKind} == {"ALL", "FALSE", "RGB", "DNBR"}


def test_false_and_rgb_band_orders():
    """The band orders match the intended visual channel assignment."""
    assert FALSE_BANDS == ["swir16", "nir", "red"]
    assert RGB_BANDS == ["red", "green", "blue"]


def test_mask_scl_noise_drops_the_scl_variable():
    """The SCL band is not part of the masked output."""
    masked = mask_scl_noise(make_dataset(), BANDS)

    assert "scl" not in masked.data_vars
    assert set(masked.data_vars) == set(BANDS) - {"scl"}


@pytest.mark.parametrize("scl_class", [0, 1, 2, 3, 7, 8, 9, 10])
def test_mask_scl_noise_masks_the_noisy_classes(scl_class):
    """Pixels flagged as cloud, shadow, snow or no-data become NaN."""
    ds = make_dataset(scl_values=np.full((2, 2, 2), scl_class))

    masked = mask_scl_noise(ds, BANDS)

    assert bool(masked["red"].isnull().all())


@pytest.mark.parametrize("scl_class", [4, 5, 6, 11])
def test_mask_scl_noise_keeps_the_valid_classes(scl_class):
    """Vegetation, bare soil, water and cirrus pixels survive the mask."""
    ds = make_dataset(scl_values=np.full((2, 2, 2), scl_class))

    masked = mask_scl_noise(ds, BANDS)

    assert not bool(masked["red"].isnull().any())


def test_mask_scl_noise_masks_per_pixel():
    """Masking is applied pixel by pixel, not per scene."""
    scl = np.full((1, 2, 2), 4)
    scl[0, 0, 1] = 8  # a single cloudy pixel
    ds = make_dataset(scl_values=scl, ntime=1)

    masked = mask_scl_noise(ds, BANDS)

    assert bool(masked["red"].isel(time=0, y=0, x=1).isnull())
    assert int(masked["red"].isnull().sum()) == 1


def test_mask_scl_noise_masks_zero_reflectance():
    """Zero-valued reflectance is treated as no-data."""
    ds = make_dataset(reflectance=0)

    masked = mask_scl_noise(ds, BANDS)

    assert bool(masked["red"].isnull().all())


def test_rescale_reflectance_applies_the_l2a_offsets():
    """Digital numbers become surface reflectance via scale 1e-4 and offset -0.1."""
    ds = xr.Dataset({"red": ("x", np.array([1000.0, 5000.0]))})

    rescaled = rescale_reflectance(ds)

    np.testing.assert_allclose(rescaled["red"].values, [0.0, 0.4], atol=1e-7)


def test_create_composite_averages_over_time_and_stacks_bands(cfg_stac, monkeypatch):
    """The composite is the temporal mean, reshaped to a band-first DataArray."""
    ds = make_dataset(ntime=3)
    ds = ds.assign(red=ds["red"] * xr.DataArray([1, 2, 3], dims="time"))
    monkeypatch.setattr(raster, "load_from_stac", lambda cfg, items, bbox: ds)

    composite = create_composite(cfg_stac, ["item"], (0, 0, 1, 1))

    assert composite.dims[0] == "band"
    assert set(composite["band"].values) == set(BANDS) - {"scl"}
    assert "time" not in composite.dims
    # mean of 1000, 2000 and 3000 digital numbers, rescaled.
    np.testing.assert_allclose(
        composite.sel(band="red").values, np.full((2, 2), 0.1), atol=1e-6
    )


def test_create_composite_ignores_masked_scenes(cfg_stac, monkeypatch):
    """Cloudy acquisitions do not drag the composite mean down."""
    scl = np.full((2, 2, 2), 4)
    scl[1] = 8  # the whole second scene is cloudy
    ds = make_dataset(scl_values=scl, ntime=2)
    ds = ds.assign(red=ds["red"] * xr.DataArray([1, 5], dims="time"))
    monkeypatch.setattr(raster, "load_from_stac", lambda cfg, items, bbox: ds)

    composite = create_composite(cfg_stac, ["item"], (0, 0, 1, 1))

    np.testing.assert_allclose(
        composite.sel(band="red").values, np.full((2, 2), 0.0), atol=1e-6
    )


def test_create_composite_forwards_the_search_arguments(cfg_stac, monkeypatch):
    """The items and bounding box reach `load_from_stac` untouched."""
    captured: dict = {}

    def fake_load(cfg, items, bbox):
        captured.update(cfg=cfg, items=items, bbox=bbox)
        return make_dataset()

    monkeypatch.setattr(raster, "load_from_stac", fake_load)

    create_composite(cfg_stac, ["item-a", "item-b"], (1, 2, 3, 4))

    assert captured["cfg"] is cfg_stac
    assert captured["items"] == ["item-a", "item-b"]
    assert captured["bbox"] == (1, 2, 3, 4)


@pytest.mark.parametrize(
    ("kind", "expected"),
    [(CompositeKind.FALSE, FALSE_BANDS), (CompositeKind.RGB, RGB_BANDS)],
)
def test_get_raster_by_kind_selects_bands_and_times(kind, expected):
    """Each kind yields a (pre, post) pair carrying its own band triple."""
    da = make_composite()

    (pre, post) = get_raster_by_kind(da, kind)

    assert list(pre["band"].values) == expected
    assert list(post["band"].values) == expected
    assert pre["time"] == "pre"
    assert post["time"] == "post"


@pytest.mark.parametrize("kind", [CompositeKind.DNBR, CompositeKind.ALL])
def test_get_raster_by_kind_rejects_unsupported_kinds(kind):
    """Kinds that are not implemented yet raise rather than return junk."""
    with pytest.raises(Error, match="is not supported yet"):
        get_raster_by_kind(make_composite(), kind)


def test_get_rasters_reads_the_zarr_store(tmp_path):
    """`get_rasters` appends the `.zarr` suffix and reads the stored composite."""
    da = make_composite()
    stem = tmp_path / "raster_EMSR999"
    da.to_zarr(f"{stem}.zarr", mode="w")

    (pre, post) = get_rasters(stem, CompositeKind.RGB)

    assert list(pre["band"].values) == RGB_BANDS
    np.testing.assert_allclose(
        pre.values, da.sel(band=RGB_BANDS, time="pre").values, atol=1e-6
    )
    np.testing.assert_allclose(
        post.values, da.sel(band=RGB_BANDS, time="post").values, atol=1e-6
    )


def test_get_rasters_missing_store(tmp_path):
    """Reading a composite that was never written raises."""
    with pytest.raises(Exception):
        get_rasters(tmp_path / "absent", CompositeKind.RGB)


@pytest.fixture
def stubbed_pipeline(monkeypatch, cfg_stac):
    """Stub out the network-bound parts of `fetch_and_store_data`."""
    calls: dict = {"search": []}

    monkeypatch.setattr(raster, "configure_s3_access", lambda **kwargs: None)
    monkeypatch.setattr(
        raster.pystac_client.Client, "open", staticmethod(lambda url: "catalog")
    )

    def fake_search(cfg, catalog, bbox, max_cloud, ref_date, delta, pre_fire):
        calls["search"].append(
            {
                "bbox": bbox,
                "max_cloud": max_cloud,
                "ref_date": ref_date,
                "delta": delta,
                "pre_fire": pre_fire,
            }
        )
        return calls.get("pre_items", ["item"]) if pre_fire else calls.get(
            "post_items", ["item"]
        )

    monkeypatch.setattr(raster, "catalog_search", fake_search)
    monkeypatch.setattr(
        raster,
        "create_composite",
        lambda cfg, items, bbox: make_composite().isel(time=0, drop=True),
    )
    return calls


def test_fetch_and_store_data_writes_a_pre_post_zarr(
    stubbed_pipeline, cfg_stac, tmp_path
):
    """The two composites are concatenated along a labelled `time` dimension."""
    out_file = tmp_path / "raster_EMSR999"

    fetch_and_store_data(
        cfg_stac,
        out_file,
        Aoi(name="sardinia", countries="Italy", extent=EXTENT),
        datetime(2024, 7, 1),
        datetime(2024, 7, 12),
    )

    stored = xr.open_dataarray(f"{out_file}.zarr", engine="zarr")
    assert list(stored["time"].values) == ["pre", "post"]
    assert set(stored["band"].values) == set(BANDS) - {"scl"}


def test_fetch_and_store_data_derives_the_bbox_from_the_aoi_wkt(
    stubbed_pipeline, cfg_stac, tmp_path
):
    """The AOI polygon is converted to the bounding box handed to the catalog."""
    fetch_and_store_data(
        cfg_stac,
        tmp_path / "raster",
        Aoi(name="sardinia", countries="Italy", extent=EXTENT),
        datetime(2024, 7, 1),
        datetime(2024, 7, 12),
    )

    assert stubbed_pipeline["search"][0]["bbox"] == (8.0, 39.0, 9.0, 40.0)


def test_fetch_and_store_data_search_windows(stubbed_pipeline, cfg_stac, tmp_path):
    """Pre-fire searches start a day early and use a shorter window than post-fire."""
    fetch_and_store_data(
        cfg_stac,
        tmp_path / "raster",
        Aoi(name="sardinia", countries="Italy", extent=EXTENT),
        datetime(2024, 7, 1),
        datetime(2024, 7, 12),
    )

    (pre, post) = stubbed_pipeline["search"]
    assert pre["pre_fire"] is True
    assert pre["ref_date"] == datetime(2024, 6, 30)
    assert pre["delta"].days == 15
    assert post["pre_fire"] is False
    assert post["ref_date"] == datetime(2024, 7, 12)
    assert post["delta"].days == 30
    assert pre["max_cloud"] == post["max_cloud"] == 20


@pytest.mark.parametrize(
    ("empty", "message"),
    [("pre_items", "No PRE fire scenes found"), ("post_items", "No POST fire scenes")],
)
def test_fetch_and_store_data_requires_scenes(
    stubbed_pipeline, cfg_stac, tmp_path, empty, message
):
    """An empty search result aborts before anything is written."""
    stubbed_pipeline[empty] = []
    out_file = tmp_path / "raster"

    with pytest.raises(Error, match=message):
        fetch_and_store_data(
            cfg_stac,
            out_file,
            Aoi(name="sardinia", countries="Italy", extent=EXTENT),
            datetime(2024, 7, 1),
            datetime(2024, 7, 12),
        )

    assert not (tmp_path / "raster.zarr").exists()
