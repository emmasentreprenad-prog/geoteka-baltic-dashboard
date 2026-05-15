import folium
import numpy as np
from matplotlib import cm


def raster_to_rgba(array, cmap_name="viridis", vmin=-1, vmax=1, visible_mask=None):
    if visible_mask is not None:
        array = np.where(visible_mask, array, np.nan)

    normalized = (array - vmin) / (vmax - vmin)
    normalized = np.clip(normalized, 0, 1)

    cmap = cm.get_cmap(cmap_name)
    rgba = cmap(normalized)
    rgba[np.isnan(array)] = [0, 0, 0, 0]

    return rgba


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
    if visible_mask is not None:
        array = np.where(visible_mask, array, np.nan)

    rgba = raster_to_rgba(array, cmap_name=cmap_name, vmin=vmin, vmax=vmax)

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
