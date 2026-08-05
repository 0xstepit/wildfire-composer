"""Tests for `wildfire_composer.spectral`."""

import numpy as np
import xarray as xr

from wildfire_composer.spectral import _normalized_difference, compute_nbr


def _band_array(values: dict[str, list[float]]) -> xr.DataArray:
    """Build a (band, x) DataArray from a mapping of band name to values."""
    bands = list(values)
    return xr.DataArray(
        np.array([values[band] for band in bands], dtype="int16"),
        dims=("band", "x"),
        coords={"band": bands},
    )


def test_normalized_difference_values():
    """The index is (a - b) / (a + b), element-wise."""
    a = xr.DataArray(np.array([1.0, 3.0, 0.0]), dims="x")
    b = xr.DataArray(np.array([1.0, 1.0, 4.0]), dims="x")

    result = _normalized_difference(a, b)

    np.testing.assert_allclose(result.values, [0.0, 0.5, -1.0])


def test_normalized_difference_casts_to_float32():
    """Integer inputs are promoted so the division does not truncate."""
    a = xr.DataArray(np.array([1, 3], dtype="int16"), dims="x")
    b = xr.DataArray(np.array([2, 1], dtype="int16"), dims="x")

    result = _normalized_difference(a, b)

    assert result.dtype == np.float32
    np.testing.assert_allclose(result.values, [-1 / 3, 0.5], rtol=1e-6)


def test_normalized_difference_zero_denominator_is_nan():
    """Pixels where a + b == 0 become NaN instead of raising or yielding inf."""
    a = xr.DataArray(np.array([0.0, 2.0, -1.0]), dims="x")
    b = xr.DataArray(np.array([0.0, 2.0, 1.0]), dims="x")

    result = _normalized_difference(a, b)

    assert np.isnan(result.values[0])
    assert np.isnan(result.values[2])
    assert result.values[1] == 0.0


def test_normalized_difference_is_bounded():
    """For non-negative reflectances the index stays within [-1, 1]."""
    rng = np.random.default_rng(0)
    a = xr.DataArray(rng.uniform(0.01, 1.0, size=64), dims="x")
    b = xr.DataArray(rng.uniform(0.01, 1.0, size=64), dims="x")

    result = _normalized_difference(a, b)

    assert result.min() >= -1.0
    assert result.max() <= 1.0


def test_normalized_difference_is_antisymmetric():
    """Swapping the operands flips the sign of the index."""
    a = xr.DataArray(np.array([0.4, 0.1]), dims="x")
    b = xr.DataArray(np.array([0.1, 0.4]), dims="x")

    np.testing.assert_allclose(
        _normalized_difference(a, b).values, -_normalized_difference(b, a).values
    )


def test_compute_nbr_selects_nir_and_swir():
    """NBR is built from the `nir` and `swir16` bands, in that order."""
    da = _band_array(
        {
            "red": [100, 100],
            "nir": [300, 100],
            "swir16": [100, 300],
        }
    )

    nbr = compute_nbr(da)

    np.testing.assert_allclose(nbr.values, [0.5, -0.5])
    assert "band" not in nbr.dims


def test_compute_nbr_preserves_spatial_coords():
    """The spatial coordinates of the input survive the computation."""
    da = xr.DataArray(
        np.ones((2, 3), dtype="int16"),
        dims=("band", "x"),
        coords={"band": ["nir", "swir16"], "x": [10, 20, 30]},
    )

    nbr = compute_nbr(da)

    assert nbr.dims == ("x",)
    np.testing.assert_array_equal(nbr["x"].values, [10, 20, 30])
