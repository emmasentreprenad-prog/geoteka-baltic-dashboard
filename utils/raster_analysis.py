import numpy as np
import planetary_computer
import rasterio
from rasterio.features import geometry_mask
from rasterio.enums import Resampling
from rasterio.warp import transform_bounds, reproject, transform
from rasterio.windows import from_bounds
from shapely.geometry import LineString, Polygon, mapping


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


def _binary_dilation(mask, iterations=1):
    dilated = mask.copy()
    for _ in range(max(0, iterations)):
        padded = np.pad(dilated, 1, mode="constant", constant_values=False)
        next_mask = np.zeros_like(dilated, dtype=bool)
        for row_offset in (-1, 0, 1):
            for col_offset in (-1, 0, 1):
                next_mask |= padded[
                    1 + row_offset:1 + row_offset + dilated.shape[0],
                    1 + col_offset:1 + col_offset + dilated.shape[1],
                ]
        dilated = next_mask
    return dilated


def build_coastal_contact_zone_mask(
    ndwi_a,
    transform_a,
    crs_a,
    ndwi_b,
    transform_b,
    crs_b,
    water_threshold=0.2,
    buffer_pixels=3,
):
    aligned_ndwi_b = align_date_b_to_date_a(ndwi_a, transform_a, crs_a, ndwi_b, transform_b, crs_b)
    valid = np.isfinite(ndwi_a) & np.isfinite(aligned_ndwi_b)

    water_a = (ndwi_a > water_threshold) & valid
    water_b = (aligned_ndwi_b > water_threshold) & valid

    edge_seed = (water_a != water_b) & valid
    edge_seed |= _binary_dilation(water_a, 1) & (~water_a) & valid
    edge_seed |= _binary_dilation(~water_a & valid, 1) & water_a & valid
    edge_seed |= _binary_dilation(water_b, 1) & (~water_b) & valid
    edge_seed |= _binary_dilation(~water_b & valid, 1) & water_b & valid

    contact_zone = _binary_dilation(edge_seed, iterations=buffer_pixels) & valid
    return contact_zone


def calculate_area_stats(index_array, threshold, pixel_size=10):
    mask = index_array > threshold
    pixels = int(np.count_nonzero(mask))
    area_m2 = pixels * pixel_size * pixel_size
    area_ha = area_m2 / 10_000
    return pixels, area_m2, area_ha


def calculate_change_stats(
    change_array,
    positive_threshold=0.15,
    negative_threshold=-0.15,
    pixel_size=10,
    contact_zone_mask=None,
):
    finite_mask = np.isfinite(change_array)
    if contact_zone_mask is not None:
        finite_mask &= contact_zone_mask

    positive_mask = (change_array > positive_threshold) & finite_mask
    negative_mask = (change_array < negative_threshold) & finite_mask

    positive_pixels = int(np.count_nonzero(positive_mask))
    negative_pixels = int(np.count_nonzero(negative_mask))

    pixel_area_m2 = pixel_size * pixel_size
    positive_area_m2 = positive_pixels * pixel_area_m2
    negative_area_m2 = negative_pixels * pixel_area_m2

    valid_pixels = int(np.count_nonzero(finite_mask))
    analysed_mask_area_m2 = valid_pixels * pixel_area_m2

    return {
        "positive_pixels": positive_pixels,
        "negative_pixels": negative_pixels,
        "positive_area_m2": positive_area_m2,
        "negative_area_m2": negative_area_m2,
        "positive_area_ha": positive_area_m2 / 10_000,
        "negative_area_ha": negative_area_m2 / 10_000,
        "valid_pixels": valid_pixels,
        "pixel_area_m2": pixel_area_m2,
        "analysed_mask_area_ha": analysed_mask_area_m2 / 10_000,
    }


def build_line_buffer_mask(line_coordinates, buffer_meters, raster_shape, transform_a, crs_a):
    if not line_coordinates or len(line_coordinates) != 2:
        return None

    lon_lat = [(coord[1], coord[0]) for coord in line_coordinates]
    xs, ys = zip(*lon_lat)
    tx, ty = transform("EPSG:4326", crs_a, list(xs), list(ys))
    projected_line = LineString(zip(tx, ty))
    buffered_geom = projected_line.buffer(buffer_meters)

    mask = geometry_mask(
        [mapping(buffered_geom)],
        transform=transform_a,
        invert=True,
        out_shape=raster_shape,
        all_touched=True,
    )

    return mask


def build_polygon_mask_and_area(polygon_coordinates, raster_shape, transform_a, crs_a):
    if not polygon_coordinates or len(polygon_coordinates) < 3:
        return None, 0.0

    lon_lat_ring = []
    for coord in polygon_coordinates:
        if len(coord) < 2:
            continue
        lon_lat_ring.append((coord[0], coord[1]))

    if len(lon_lat_ring) < 3:
        return None, 0.0

    if lon_lat_ring[0] != lon_lat_ring[-1]:
        lon_lat_ring.append(lon_lat_ring[0])

    xs, ys = zip(*lon_lat_ring)
    tx, ty = transform("EPSG:4326", crs_a, list(xs), list(ys))
    projected_polygon = Polygon(zip(tx, ty))
    if not projected_polygon.is_valid:
        projected_polygon = projected_polygon.buffer(0)
    if projected_polygon.is_empty:
        return None, 0.0

    mask = geometry_mask(
        [mapping(projected_polygon)],
        transform=transform_a,
        invert=True,
        out_shape=raster_shape,
        all_touched=True,
    )

    area_ha = float(projected_polygon.area) / 10_000
    return mask, area_ha
