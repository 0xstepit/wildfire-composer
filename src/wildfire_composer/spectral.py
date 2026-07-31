import xarray as xr


def _normalized_difference(a: xr.DataArray, b: xr.DataArray) -> xr.DataArray:
    """Compute the normalized difference (a - b) / (a + b).

    Inputs are cast to float32 and pixels where the denominator is zero are set to NaN.
    """
    a = a.astype("float32")
    b = b.astype("float32")

    den = a + b
    return (a - b) / den.where(den != 0)


def compute_nbr(ds: xr.DataArray) -> xr.DataArray:
    """Compute the Normalized Burn Ratio (NBR).

    NBR = (NIR - SWIR) / (NIR + SWIR)
    """
    return _normalized_difference(ds.sel(band="nir"), ds.sel(band="swir16"))
