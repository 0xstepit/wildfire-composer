"""Shared fixtures for the wildfire-composer test suite."""

import httpx
import matplotlib
import pytest

# Tests must never try to open a GUI window.
matplotlib.use("Agg")


CONFIG_TOML = """
[cems]
url = "https://example.invalid/activations-info/"
url_extended = "https://example.invalid/activations/"

[io]
img_dir = "data/images"
raster_dir = "data/rasters"
db = "data/cems.duckdb"

[stac]
url = "https://example.invalid/stac/v1"
collection = "sentinel-2-l2a"
chunk_size = 1024
bands = ["red", "green", "blue", "nir", "swir16", "scl"]
"""


@pytest.fixture
def config_path(tmp_path):
    """Write a valid configuration file and return its path."""
    path = tmp_path / "config.toml"
    path.write_text(CONFIG_TOML)
    return path


@pytest.fixture
def cfg(config_path):
    """A `Config` loaded from the fixture configuration file."""
    from wildfire_composer.config import Config

    return Config.load(str(config_path))


@pytest.fixture
def mock_http(monkeypatch):
    """Route every `httpx.Client` request through a caller-supplied handler.

    The returned callable takes a handler `(httpx.Request) -> httpx.Response` and
    installs it for the remainder of the test.
    """
    real_client = httpx.Client

    def install(handler):
        def factory(*args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            return real_client(*args, **kwargs)

        monkeypatch.setattr(httpx, "Client", factory)

    return install


@pytest.fixture
def activation_record():
    """An extended CEMS activation payload with a single, finished AOI product."""
    return {
        "code": "EMSR999",
        "eventTime": "2024-07-01T00:00:00",
        "countries": [{"name": "Italy"}, {"name": "France"}],
        "aois": [
            {
                "products": [
                    {
                        "type": "DEL",
                        "aoiName": "ignored",
                        "extent": "POLYGON ((0 0, 0 1, 1 1, 1 0, 0 0))",
                        "version": {"statusCode": "F", "deliveryTime": "2024-07-10"},
                    },
                    {
                        "type": "GRA",
                        "aoiName": "sardinia",
                        "extent": "POLYGON ((8 39, 8 40, 9 40, 9 39, 8 39))",
                        "version": {
                            "statusCode": "F",
                            "deliveryTime": "2024-07-12T00:00:00",
                        },
                    },
                ]
            }
        ],
    }
