import numpy as np
import planetary_computer
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import transform_bounds, reproject
from rasterio.windows import from_bounds


def get_asset_href(item, band_name):
    signed_item = planetary_computer.sign(item)
    return signed_item.assets[band_name].href


def read_band_from_item(item, band_name, bbox, max_size=900):
    href = get_asset_href(item, band_name)

    with rasterio.open(href) as src:
        image_bounds = transform_bounds(
            "EPSG:4326",
            src.crs,
            bbox[0], bbox[1], bbox[2], bbox[3],
            densify_pts=21,
        )

        window = from_bounds(*image_bounds, transform=src.transform)
        window = window.round_offsets().round_lengths()

        height = max(1, int(window.height))
        width = max(1, int(window.width))
        scale = max(width / max_size, height / max_size, 1)

        out_height = max(1, int(height / scale))
        out_width = max(1, int(width / scale))

        data = src.read(
            1,
            window=window,
            out_shape=(out_height, out_width),
            resampling=Resampling.bilinear,
            boundless=True,
            fill_value=np.nan,
        ).astype("float32")

        nodata = src.nodata
        if nodata is not None:
            data[data == nodata] = np.nan

        data[data <= 0] = np.nan
        transform = src.window_transform(window)

        return data, transform, src.crs


def calculate_ndvi(item, bbox):
    nir, transform, crs = read_band_from_item(item, "B08", bbox)
    red, _, _ = read_band_from_item(item, "B04", bbox)

    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = (nir - red) / (nir + red)

    return np.clip(ndvi, -1, 1), transform, crs


def calculate_ndwi(item, bbox):
    green, transform, crs = read_band_from_item(item, "B03", bbox)
    nir, _, _ = read_band_from_item(item, "B08", bbox)

    with np.errstate(divide="ignore", invalid="ignore"):
        ndwi = (green - nir) / (green + nir)

    return np.clip(ndwi, -1, 1), transform, crs


def align_date_b_to_date_a(array_a, transform_a, crs_a, array_b, transform_b, crs_b):
    aligned_b = np.full(array_a.shape, np.nan, dtype="float32")

    reproject(
        source=array_b.astype("float32"),
        destination=aligned_b,
        src_transform=transform_b,
        src_crs=crs_b,
        src_nodata=np.nan,
        dst_transform=transform_a,
        dst_crs=crs_a,
        dst_nodata=np.nan,
        resampling=Resampling.bilinear,
    )

    return aligned_b


def calculate_change(array_a, transform_a, crs_a, array_b, transform_b, crs_b):
    aligned_b = align_date_b_to_date_a(array_a, transform_a, crs_a, array_b, transform_b, crs_b)

    valid_mask = np.isfinite(array_a) & np.isfinite(aligned_b)
    change = np.full(array_a.shape, np.nan, dtype="float32")
    change[valid_mask] = aligned_b[valid_mask] - array_a[valid_mask]

    return np.clip(change, -2, 2)


def calculate_area_stats(index_array, threshold, pixel_size=10):
    mask = index_array > threshold
    pixels = int(np.count_nonzero(mask))
    area_m2 = pixels * pixel_size * pixel_size
    area_ha = area_m2 / 10_000
    return pixels, area_m2, area_ha


def calculate_change_stats(change_array, positive_threshold=0.15, negative_threshold=-0.15, pixel_size=10):
    positive_pixels = int(np.count_nonzero(change_array > positive_threshold))
    negative_pixels = int(np.count_nonzero(change_array < negative_threshold))

    positive_area_m2 = positive_pixels * pixel_size * pixel_size
    negative_area_m2 = negative_pixels * pixel_size * pixel_size

    return {
        "positive_pixels": positive_pixels,
        "negative_pixels": negative_pixels,
        "positive_area_m2": positive_area_m2,
        "negative_area_m2": negative_area_m2,
        "positive_area_ha": positive_area_m2 / 10_000,
        "negative_area_ha": negative_area_m2 / 10_000,
    }
