"""Tests for `wildfire_composer.viz`."""

import matplotlib.pyplot as plt
import numpy as np
import pytest
import xarray as xr

from wildfire_composer.viz import add_text, mosaic, plot_compare


@pytest.fixture(autouse=True)
def close_figures():
    """Close every figure a test opened."""
    yield
    plt.close("all")


def make_raster(width=4, height=4):
    """An RGB raster shaped the way `get_raster_by_kind` returns it."""
    rng = np.random.default_rng(0)
    return xr.DataArray(
        rng.random((height, width, 3), dtype="float32"),
        dims=("y", "x", "band"),
        coords={"band": ["red", "green", "blue"]},
    )


def _texts(ax):
    """The strings drawn on an axes."""
    return [text.get_text() for text in ax.texts]


def test_add_text_places_a_centred_label():
    """The label is centred horizontally and anchored as requested."""
    _, ax = plt.subplots()

    add_text(ax, "Italy", 24, "bottom")

    (text,) = ax.texts
    assert text.get_text() == "Italy"
    assert text.get_position() == (0.5, 0.5)
    assert text.get_ha() == "center"
    assert text.get_va() == "bottom"
    assert text.get_fontsize() == 24
    assert text.get_color() == "white"


def test_add_text_uses_a_stroke_for_contrast():
    """A dark outline keeps the white label readable on bright imagery."""
    _, ax = plt.subplots()

    add_text(ax, "Italy", 12, "top")

    assert ax.texts[0].get_path_effects()


def test_mosaic_returns_a_figure_with_one_axes_per_raster():
    """Every raster gets a panel."""
    rasters = [make_raster() for _ in range(3)]

    fig = mosaic(rasters, ["Italy"] * 3, ["Sardinia"] * 3)

    assert len(fig.axes) == 3


@pytest.mark.parametrize(
    ("count", "expected_shape"),
    [(1, (1, 1)), (2, (1, 2)), (3, (1, 3)), (4, (2, 2)), (5, (3, 2))],
)
def test_mosaic_default_grid(count, expected_shape):
    """Up to three rasters go on one row, beyond that the grid is two columns."""
    rasters = [make_raster() for _ in range(count)]

    fig = mosaic(rasters, ["Italy"] * count, ["Sardinia"] * count)

    (nrows, ncols) = expected_shape
    assert fig.axes[0].get_subplotspec().get_gridspec().get_geometry() == (
        nrows,
        ncols,
    )


def test_mosaic_honours_an_explicit_ncols():
    """An explicit column count overrides the default layout."""
    rasters = [make_raster() for _ in range(4)]

    fig = mosaic(rasters, ["Italy"] * 4, ["Sardinia"] * 4, ncols=4)

    assert fig.axes[0].get_subplotspec().get_gridspec().get_geometry() == (1, 4)


def test_mosaic_default_figsize_scales_with_the_grid():
    """The figure grows by one panel per row and column."""
    rasters = [make_raster() for _ in range(4)]

    fig = mosaic(rasters, ["Italy"] * 4, ["Sardinia"] * 4, panel=3.0)

    assert tuple(fig.get_size_inches()) == (6.0, 6.0)


def test_mosaic_honours_an_explicit_figsize():
    """An explicit figure size is passed straight through."""
    fig = mosaic([make_raster()], ["Italy"], ["Sardinia"], figsize=(8, 2))

    assert tuple(fig.get_size_inches()) == (8.0, 2.0)


def test_mosaic_labels_each_panel_with_country_and_region():
    """Both captions are drawn inside the panel, and the xarray title is cleared."""
    fig = mosaic(
        [make_raster(), make_raster()],
        ["Italy", "France"],
        ["Sardinia", "Corsica"],
    )

    assert _texts(fig.axes[0]) == ["Italy", "Sardinia"]
    assert _texts(fig.axes[1]) == ["France", "Corsica"]
    assert all(ax.get_title() == "" for ax in fig.axes)


def test_mosaic_hides_the_axes_decorations():
    """Ticks, labels and the frame are turned off so only imagery shows."""
    fig = mosaic([make_raster()], ["Italy"], ["Sardinia"])

    assert not fig.axes[0].axison


def test_mosaic_uses_a_black_background_by_default():
    """The gaps between panels are black unless overridden."""
    fig = mosaic([make_raster()], ["Italy"], ["Sardinia"])

    assert fig.get_facecolor()[:3] == (0.0, 0.0, 0.0)


def test_mosaic_facecolor_is_configurable():
    """A caller-supplied background colour is applied to the figure."""
    fig = mosaic([make_raster()], ["Italy"], ["Sardinia"], facecolor="white")

    assert fig.get_facecolor()[:3] == (1.0, 1.0, 1.0)


def test_mosaic_leaves_extra_grid_cells_blank():
    """An odd raster count still produces a full grid, with the last panel empty."""
    rasters = [make_raster() for _ in range(3)]

    fig = mosaic(rasters, ["Italy"] * 3, ["Sardinia"] * 3, ncols=2)

    assert len(fig.axes) == 4
    assert _texts(fig.axes[3]) == []


def test_mosaic_stops_at_the_shortest_label_sequence():
    """Panels beyond the supplied labels are left unlabelled rather than raising."""
    rasters = [make_raster() for _ in range(2)]

    fig = mosaic(rasters, ["Italy"], ["Sardinia"])

    assert _texts(fig.axes[0]) == ["Italy", "Sardinia"]
    assert _texts(fig.axes[1]) == []


def test_plot_compare_draws_a_pre_post_pair():
    """The two panels are titled Pre Fire and Post Fire under a shared heading."""
    raster = make_raster()

    plot_compare("sardinia", "italy", "false colour", raster, raster)

    fig = plt.gcf()
    assert fig.axes[0].get_title() == "Pre Fire"
    assert fig.axes[1].get_title() == "Post Fire"
    assert fig.get_suptitle() == "Sardinia, Italy false colour"


def test_plot_compare_figsize_is_given_in_centimetres():
    """The 30x15 cm figure size is converted to inches by matplotlib."""
    raster = make_raster()

    plot_compare("sardinia", "italy", "false colour", raster, raster)

    (width, height) = plt.gcf().get_size_inches()
    assert (width, height) == pytest.approx((30 / 2.54, 15 / 2.54))


def test_plot_compare_uses_an_equal_aspect_and_rotated_ticks():
    """Both panels keep the pixel aspect ratio and stay readable."""
    raster = make_raster()

    plot_compare("sardinia", "italy", "false colour", raster, raster)

    for ax in plt.gcf().axes:
        assert ax.get_aspect() == 1.0
        assert all(label.get_rotation() == 45 for label in ax.get_xticklabels())
