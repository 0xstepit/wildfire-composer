"""Tests for `wildfire_composer.config`."""

import dataclasses

import pytest

from wildfire_composer.config import CemsConfig, Config, IoConfig, StacConfig


def test_load_populates_every_section(config_path):
    """`Config.load` maps each TOML table onto its dataclass."""
    cfg = Config.load(str(config_path))

    assert isinstance(cfg.cems, CemsConfig)
    assert isinstance(cfg.stac, StacConfig)
    assert isinstance(cfg.io, IoConfig)

    assert cfg.cems.url == "https://example.invalid/activations-info/"
    assert cfg.cems.url_extended == "https://example.invalid/activations/"
    assert cfg.stac.collection == "sentinel-2-l2a"
    assert cfg.stac.chunk_size == 1024
    assert cfg.stac.bands == ["red", "green", "blue", "nir", "swir16", "scl"]
    assert cfg.io.img_dir == "data/images"
    assert cfg.io.raster_dir == "data/rasters"
    assert cfg.io.db == "data/cems.duckdb"


def test_load_accepts_a_path_like(config_path):
    """`Config.load` works with a `Path` as well as a `str`."""
    assert Config.load(config_path) == Config.load(str(config_path))


def test_sections_are_frozen(cfg):
    """The section dataclasses are immutable."""
    for section in (cfg.cems, cfg.stac, cfg.io):
        with pytest.raises(dataclasses.FrozenInstanceError):
            section.url = "mutated"


def test_stac_bands_default_to_empty():
    """`StacConfig.bands` defaults to an empty list."""
    stac = StacConfig(url="u", collection="c", chunk_size=1)

    assert stac.bands == []


def test_stac_bands_default_is_not_shared():
    """Each `StacConfig` gets its own `bands` list."""
    first = StacConfig(url="u", collection="c", chunk_size=1)
    second = StacConfig(url="u", collection="c", chunk_size=1)

    first.bands.append("red")

    assert second.bands == []


def test_load_missing_file(tmp_path):
    """A missing configuration file surfaces as `FileNotFoundError`."""
    with pytest.raises(FileNotFoundError):
        Config.load(str(tmp_path / "nope.toml"))


def test_load_missing_section(tmp_path):
    """A configuration file without every section is rejected."""
    path = tmp_path / "partial.toml"
    path.write_text('[cems]\nurl = "a"\nurl_extended = "b"\n')

    with pytest.raises(KeyError):
        Config.load(str(path))


def test_load_unknown_key(tmp_path):
    """An unknown key inside a section is rejected rather than ignored."""
    path = tmp_path / "extra.toml"
    path.write_text(
        '[cems]\nurl = "a"\nurl_extended = "b"\nsurprise = 1\n'
        '[io]\nimg_dir = "i"\nraster_dir = "r"\ndb = "d"\n'
        '[stac]\nurl = "u"\ncollection = "c"\nchunk_size = 1\n'
    )

    with pytest.raises(TypeError):
        Config.load(str(path))
