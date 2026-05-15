import folium
import numpy as np
from matplotlib import cm


def raster_to_rgba(array, cmap_name="viridis", vmin=-1, vmax=1, visible_mask=None, opacity=0.65):
    finite_mask = np.isfinite(array)
    if visible_mask is not None:
        finite_mask &= visible_mask.astype(bool)

    normalized = np.zeros_like(array, dtype=np.float32)
    if vmax == vmin:
        vmax = vmin + 1e-6
    normalized[finite_mask] = (array[finite_mask] - vmin) / (vmax - vmin)
    normalized = np.clip(normalized, 0.0, 1.0)

    rgba = np.zeros((array.shape[0], array.shape[1], 4), dtype=np.uint8)
    if np.any(finite_mask):
        cmap = cm.get_cmap(cmap_name)
        rgb = np.round(cmap(normalized)[..., :3] * 255).astype(np.uint8)
        rgba[finite_mask, :3] = rgb[finite_mask]
        alpha_value = np.uint8(np.clip(opacity, 0.0, 1.0) * 255)
        rgba[finite_mask, 3] = alpha_value

    rgba[~finite_mask] = np.array([0, 0, 0, 0], dtype=np.uint8)
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
    rgba = raster_to_rgba(
        array,
        cmap_name=cmap_name,
        vmin=vmin,
        vmax=vmax,
        visible_mask=visible_mask,
        opacity=opacity,
    )

    if rgba.dtype != np.uint8 or rgba.ndim != 3 or rgba.shape[2] != 4:
        raise ValueError(
            f"Overlay image must be RGBA uint8 with shape (height, width, 4), got dtype={rgba.dtype}, shape={rgba.shape}"
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

    alpha = rgba[..., 3]
    return {
        "finite_pixels": int(np.count_nonzero(np.isfinite(array))),
        "transparent_pixels": int(np.count_nonzero(alpha == 0)),
        "alpha_min": int(alpha.min()),
        "alpha_max": int(alpha.max()),
        "rgba_shape": rgba.shape,
        "rgba_dtype": str(rgba.dtype),
    }


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
