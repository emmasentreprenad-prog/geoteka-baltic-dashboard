import folium
import numpy as np
from matplotlib import cm
from matplotlib.colors import ListedColormap


def raster_to_rgba(array, cmap_name="viridis", vmin=-1, vmax=1, visible_mask=None):
    if visible_mask is not None:
        array = np.where(visible_mask, array, np.nan)

    finite_mask = np.isfinite(array)
    normalized = np.zeros_like(array, dtype=np.float32)
    normalized[finite_mask] = (array[finite_mask] - vmin) / (vmax - vmin)
    normalized = np.clip(normalized, 0, 1)

    base_cmap = cm.get_cmap(cmap_name)
    cmap = ListedColormap(base_cmap(np.linspace(0, 1, 256)))

    rgba = cmap(normalized)
    rgba[~finite_mask, 3] = 0

    return np.round(rgba * 255).astype(np.uint8)


def add_array_overlay(
    m,
    array,
    bbox,
    name,
    cmap_name="viridis",
    opacity=0.65,
    vmin=-1,
    vmax=1,
    visible_mask=None,
):
    rgba = raster_to_rgba(
        array,
        cmap_name=cmap_name,
        vmin=vmin,
        vmax=vmax,
        visible_mask=visible_mask,
    )

    folium.raster_layers.ImageOverlay(
        image=rgba,
        bounds=[[bbox[1], bbox[0]], [bbox[3], bbox[2]]],
        name=name,
        opacity=opacity,
        interactive=True,
        cross_origin=False,
        zindex=20,
    ).add_to(m)


def add_stac_true_color(m, item, name, opacity):
    m.add_stac_layer(
        item,
        bands=["B04", "B03", "B02"],
        name=name,
        opacity=opacity,
    )


def add_stac_false_color(m, item, name, opacity):
    m.add_stac_layer(
        item,
        bands=["B08", "B04", "B03"],
        name=name,
        opacity=opacity,
    )


def add_stac_water_highlight(m, item, name, opacity):
    m.add_stac_layer(
        item,
        bands=["B08", "B03", "B02"],
        name=name,
        opacity=opacity,
    )
