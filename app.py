import streamlit as st
import leafmap.foliumap as leafmap
import planetary_computer
import numpy as np
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium

from config import AREAS, CENTERS, ANALYSIS_MODES
from utils.logo import create_clean_logo
from utils.sentinel import search_sentinel1, search_sentinel2
from utils.raster_analysis import (
    calculate_area_stats,
    calculate_change,
    calculate_change_stats,
    build_coastal_contact_zone_mask,
    calculate_ndvi,
    calculate_ndwi,
    build_polygon_mask_and_area,
)
from utils.map_layers import (
    add_array_overlay,
    add_stac_false_color,
    add_stac_true_color,
    add_stac_water_highlight,
)
from utils.reports import build_report


st.set_page_config(
    page_title="GeoTeka Baltic Dashboard",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #031f24 0%, #063b3b 55%, #021417 100%);
        color: white;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #021417 0%, #064242 100%);
        border-right: 2px solid #25d9d9;
    }

    h1 {
        font-size: 56px !important;
        font-weight: 900 !important;
    }

    h2, h3, h4, h5, h6, p, label {
        color: white !important;
    }

    .geo-blue {
        color: #1742d8;
    }

    .baltic {
        color: #25d9ff;
    }

    .sidebar-title {
        color: #25d9ff;
        font-size: 24px;
        font-weight: 800;
        margin-top: 10px;
        margin-bottom: 10px;
    }

    div.stButton > button {
        background-color: #063b3b;
        color: white;
        border-radius: 10px;
        border: 1px solid #25d9ff;
        padding: 0.6rem 1.2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


clean_logo = create_clean_logo()
if clean_logo:
    st.sidebar.image(clean_logo, width=190)

st.sidebar.markdown("---")
st.sidebar.markdown('<div class="sidebar-title">Choose layers</div>', unsafe_allow_html=True)

show_satellite = st.sidebar.checkbox("🛰️ Satellite background", True)
show_sentinel1 = st.sidebar.checkbox("⚫ Sentinel-1 SAR radar", False)
compare_dates = st.sidebar.checkbox("🆚 Compare two dates", False)

st.sidebar.markdown("---")
st.sidebar.markdown('<div class="sidebar-title">Area</div>', unsafe_allow_html=True)

area = st.sidebar.selectbox("Area", list(AREAS.keys()))
bbox = AREAS[area]
center = CENTERS[area]

st.sidebar.markdown("---")
st.sidebar.markdown('<div class="sidebar-title">Sentinel settings</div>', unsafe_allow_html=True)

cloud_cover = st.sidebar.slider("Max cloud cover", 0, 100, 40)
zoom = st.sidebar.slider("Zoom level", 5, 18, 10)
analysis = st.sidebar.selectbox("Analysis mode", ANALYSIS_MODES)
coastline_buffer_m = st.sidebar.slider("Coastline section buffer (m)", 50, 1000, 200, 25)
show_coastline_raster_overlay_debug = st.sidebar.checkbox("Show debug raster overlay", False)

if compare_dates:
    st.sidebar.markdown("### Compare dates")
    date_range_a = st.sidebar.text_input("Date A / older date", "2017-08-01/2017-08-14")
    date_range_b = st.sidebar.text_input("Date B / newer date", "2025-08-01/2025-08-14")
    opacity_a = st.sidebar.slider("Opacity Date A", 0, 100, 55)
    opacity_b = st.sidebar.slider("Opacity Date B", 0, 100, 85)
else:
    date_range_a = None
    date_range_b = st.sidebar.text_input("Date", "2025-08-01/2025-08-14")
    opacity_a = 0
    opacity_b = 85

st.markdown(
    """
    <h1>
        <span class="geo-blue">GeoTeka</span>
        <span class="baltic"> Baltic Dashboard</span>
    </h1>
    """,
    unsafe_allow_html=True,
)

st.write("Satellite intelligence for land and Baltic Sea analysis.")

m = leafmap.Map(center=center, zoom=zoom)
Draw(
    export=False,
    draw_options={
        "polyline": True,
        "polygon": True,
        "rectangle": True,
        "circle": False,
        "marker": False,
        "circlemarker": False,
    },
    edit_options={"edit": True, "remove": True},
).add_to(m)

if show_satellite:
    m.add_basemap("HYBRID")
else:
    m.add_basemap("OpenStreetMap")

scene_a_id = "Not loaded"
scene_b_id = "Not loaded"
sar_id = "Not loaded"
scene_a_date = "Not loaded"
scene_b_date = "Not loaded"

s2_a_item = None
s2_b_item = None
calculated_ndvi = None
calculated_ndwi = None
calculated_change = None
masked_change = None
ndvi_stats = None
ndwi_stats = None
change_stats = None
coastal_contact_zone_mask = None
polygon_mask = None
drawn_polygon_coords = None
analysed_polygon_area_ha = 0.0
overlay_finite_pixels = None
overlay_nan_pixels = None
overlay_min_finite_change = None
overlay_max_finite_change = None
overlay_rgba_debug = None
raster_overlay_rendered = False
coastline_vector_feature_count = 0
draw_controls_enabled = True

# Load Date A if comparison is enabled
if compare_dates:
    try:
        with st.spinner("Loading Sentinel-2 Date A..."):
            s2_a_items = search_sentinel2(bbox, date_range_a, cloud_cover)

        if len(s2_a_items) > 0:
            s2_a_item = s2_a_items[0]
            s2_a_signed = planetary_computer.sign(s2_a_item)
            scene_a_id = s2_a_item.id
            scene_a_date = str(s2_a_item.properties.get("datetime", "Unknown"))[:10]

            add_stac_true_color(
                m,
                s2_a_signed,
                "DATE A - older true color",
                opacity_a / 100,
            )
            st.success(f"Date A loaded: {scene_a_id}")
        else:
            st.warning("No Sentinel-2 image found for Date A.")

    except Exception as e:
        st.error(f"Date A error: {e}")

# Load Date B
try:
    with st.spinner("Loading Sentinel-2 Date B..."):
        s2_b_items = search_sentinel2(bbox, date_range_b, cloud_cover)

    if len(s2_b_items) > 0:
        s2_b_item = s2_b_items[0]
        s2_b_signed = planetary_computer.sign(s2_b_item)
        scene_b_id = s2_b_item.id
        scene_b_date = str(s2_b_item.properties.get("datetime", "Unknown"))[:10]

        if analysis == "NDVI vegetation health":
            calculated_ndvi, _, _ = calculate_ndvi(s2_b_item, bbox)
            add_array_overlay(
                m,
                calculated_ndvi,
                bbox,
                "REAL NDVI calculated raster",
                cmap_name="YlGn",
                opacity=opacity_b / 100,
                vmin=-1,
                vmax=1,
            )

        elif analysis == "NDWI water detection":
            calculated_ndwi, _, _ = calculate_ndwi(s2_b_item, bbox)
            add_array_overlay(
                m,
                calculated_ndwi,
                bbox,
                "REAL NDWI calculated raster",
                cmap_name="Blues",
                opacity=opacity_b / 100,
                vmin=-1,
                vmax=1,
            )

        elif analysis == "Coastline change" and compare_dates and s2_a_item is not None:
            ndwi_a, transform_a, crs_a = calculate_ndwi(s2_a_item, bbox)
            ndwi_b, transform_b, crs_b = calculate_ndwi(s2_b_item, bbox)
            calculated_change = calculate_change(
                ndwi_a,
                transform_a,
                crs_a,
                ndwi_b,
                transform_b,
                crs_b,
            )
            drawn_polygon_coords = st.session_state.get("analysis_polygon_coords")
            if drawn_polygon_coords is not None:
                polygon_mask, analysed_polygon_area_ha = build_polygon_mask_and_area(
                    drawn_polygon_coords,
                    calculated_change.shape,
                    transform_a,
                    crs_a,
                )
            coastal_contact_zone_mask = build_coastal_contact_zone_mask(
                ndwi_a,
                transform_a,
                crs_a,
                ndwi_b,
                transform_b,
                crs_b,
                buffer_pixels=max(1, int(np.ceil(coastline_buffer_m / 40))),
            )

            if polygon_mask is not None:
                combined_mask = coastal_contact_zone_mask & polygon_mask
            else:
                combined_mask = coastal_contact_zone_mask

            masked_change = np.where(
                combined_mask & np.isfinite(calculated_change),
                calculated_change,
                np.nan,
            ).astype("float32")

            finite_change_mask = np.isfinite(masked_change)
            overlay_finite_pixels = int(np.count_nonzero(finite_change_mask))
            overlay_nan_pixels = int(masked_change.size - overlay_finite_pixels)
            if overlay_finite_pixels > 0:
                overlay_min_finite_change = float(np.min(masked_change[finite_change_mask]))
                overlay_max_finite_change = float(np.max(masked_change[finite_change_mask]))

            if show_coastline_raster_overlay_debug:
                raster_overlay_rendered = True
                overlay_rgba_debug = add_array_overlay(
                    m,
                    calculated_change,
                    bbox,
                    "REAL coastline change raster",
                    cmap_name="RdYlGn",
                    opacity=opacity_b / 100,
                    vmin=-1,
                    vmax=1,
                    visible_mask=combined_mask,
                )

        elif compare_dates:
            add_stac_water_highlight(
                m,
                s2_b_signed,
                "DATE B - water/vegetation highlight",
                opacity_b / 100,
            )

        elif analysis in ["Ålgräs / shallow water", "Algae bloom detection", "Moisture analysis"]:
            add_stac_water_highlight(
                m,
                s2_b_signed,
                "Sentinel-2 water/vegetation highlight",
                opacity_b / 100,
            )

        elif analysis == "NDVI vegetation health":
            add_stac_false_color(
                m,
                s2_b_signed,
                "Sentinel-2 false color",
                opacity_b / 100,
            )

        else:
            add_stac_true_color(
                m,
                s2_b_signed,
                "Sentinel-2 true color",
                opacity_b / 100,
            )

        st.success(f"Date B loaded: {scene_b_id}")

    else:
        st.warning("No Sentinel-2 image found for Date B.")

except Exception as e:
    st.error(f"Date B error: {e}")

# Sentinel-1 SAR
if show_sentinel1:
    try:
        with st.spinner("Loading Sentinel-1 SAR..."):
            s1_items = search_sentinel1(bbox, date_range_b)

        if len(s1_items) > 0:
            s1_signed = planetary_computer.sign(s1_items[0])
            sar_id = s1_items[0].id

            m.add_stac_layer(
                s1_signed,
                bands=["vv"],
                name="Sentinel-1 SAR radar",
                opacity=0.55,
            )
            st.success(f"SAR loaded: {sar_id}")
        else:
            st.warning("No Sentinel-1 SAR image found.")

    except Exception as e:
        st.error(f"SAR error: {e}")

st.caption(f"Map debug (above) — draw controls enabled: {draw_controls_enabled} | displayed coastline vector features: {coastline_vector_feature_count}")

map_state = st_folium(m, height=560, width=None, returned_objects=["all_drawings", "last_active_drawing"])

st.caption(f"Map debug (below) — draw controls enabled: {draw_controls_enabled} | displayed coastline vector features: {coastline_vector_feature_count}")
st.caption(f"Coastline raster overlay rendered: {raster_overlay_rendered}")

if calculated_change is not None:
    calculated_shape = calculated_change.shape
    finite_in_change = int(np.count_nonzero(np.isfinite(calculated_change)))
    finite_after_mask = int(np.count_nonzero(np.isfinite(masked_change))) if masked_change is not None else 0
    debug_positive_area_m2 = 0.0
    debug_positive_area_ha = 0.0
    debug_negative_area_m2 = 0.0
    debug_negative_area_ha = 0.0

    if masked_change is not None:
        positive_debug_mask = np.isfinite(masked_change) & (masked_change > 0)
        negative_debug_mask = np.isfinite(masked_change) & (masked_change < 0)
        debug_positive_area_m2 = float(np.count_nonzero(positive_debug_mask) * 100)
        debug_negative_area_m2 = float(np.count_nonzero(negative_debug_mask) * 100)
        debug_positive_area_ha = debug_positive_area_m2 / 10000
        debug_negative_area_ha = debug_negative_area_m2 / 10000

    st.caption(
        "Coastline debug — "
        f"calculated_change shape: {calculated_shape} | "
        f"finite pixels in calculated_change: {finite_in_change:,} | "
        f"finite pixels after mask: {finite_after_mask:,} | "
        f"positive area: {debug_positive_area_m2:,.0f} m² ({debug_positive_area_ha:,.2f} ha) | "
        f"negative area: {debug_negative_area_m2:,.0f} m² ({debug_negative_area_ha:,.2f} ha)"
    )

if map_state:
    latest_polygon = None
    for drawing in (map_state.get("all_drawings") or [])[::-1]:
        geometry = drawing.get("geometry", {})
        coords = geometry.get("coordinates", [])
        if geometry.get("type") == "Polygon" and len(coords) > 0 and len(coords[0]) >= 3:
            latest_polygon = coords[0]
            break

    previous_polygon = st.session_state.get("analysis_polygon_coords")
    if latest_polygon is not None:
        if previous_polygon != latest_polygon:
            st.session_state["analysis_polygon_coords"] = latest_polygon
            st.rerun()
    elif (map_state.get("all_drawings") == []):
        if previous_polygon is not None:
            st.session_state["analysis_polygon_coords"] = None
            st.rerun()


if map_state:
    st.caption(f"Drawing debug — latest map drawing payload: {map_state.get('last_active_drawing')}")
    st.caption(f"Drawing debug — all drawings: {map_state.get('all_drawings')}")

st.markdown("## 🌊 Analysis")

if calculated_ndwi is not None:
    st.success("Real NDWI water detection selected 💧")
    water_threshold = st.slider("NDWI water threshold", -1.0, 1.0, 0.2, 0.05)
    pixels, area_m2, area_ha = calculate_area_stats(calculated_ndwi, water_threshold)

    ndwi_stats = {
        "pixels": pixels,
        "area_m2": area_m2,
        "area_ha": area_ha,
        "threshold": water_threshold,
    }

    st.write(f"Detected water/wet pixels: {pixels}")
    st.write(f"Approximate detected area: {area_m2:,.0f} m²")
    st.write(f"Approximate detected area: {area_ha:,.2f} ha")

elif calculated_ndvi is not None:
    st.success("Real NDVI vegetation health selected 🌱")
    vegetation_threshold = st.slider("NDVI vegetation threshold", -1.0, 1.0, 0.3, 0.05)
    pixels, area_m2, area_ha = calculate_area_stats(calculated_ndvi, vegetation_threshold)

    ndvi_stats = {
        "pixels": pixels,
        "area_m2": area_m2,
        "area_ha": area_ha,
        "threshold": vegetation_threshold,
    }

    st.write(f"Detected vegetation pixels: {pixels}")
    st.write(f"Approximate vegetation area: {area_m2:,.0f} m²")
    st.write(f"Approximate vegetation area: {area_ha:,.2f} ha")

elif calculated_change is not None:
    st.success("Real coastline/water change detection selected 🌊")
    positive_threshold = st.slider("Positive change threshold", 0.0, 1.0, 0.15, 0.05)
    negative_threshold = st.slider("Negative change threshold", -1.0, 0.0, -0.15, 0.05)

    if polygon_mask is None:
        st.warning("Draw an analysis area on the map first.")
        change_stats = None
    else:
        change_stats = calculate_change_stats(
            calculated_change,
            positive_threshold=positive_threshold,
            negative_threshold=negative_threshold,
            contact_zone_mask=polygon_mask,
        )

        st.write(f"Positive change area: {change_stats['positive_area_m2']:,.0f} m²")
        st.write(f"Positive change area: {change_stats['positive_area_ha']:,.2f} ha")
        st.write(f"Negative change area: {change_stats['negative_area_m2']:,.0f} m²")
        st.write(f"Negative change area: {change_stats['negative_area_ha']:,.2f} ha")

    finite_displayed_count = int(np.count_nonzero(np.isfinite(masked_change))) if masked_change is not None else 0
    st.markdown("#### Debug")
    st.caption(f"Drawn polygon coordinates: {drawn_polygon_coords}")
    st.caption(f"Raster shape: {calculated_change.shape}")
    st.caption(f"Number of finite pixels inside polygon: {finite_displayed_count:,}")
    st.caption(f"Analysed polygon area: {analysed_polygon_area_ha:,.2f} ha")

elif analysis == "Algae bloom detection":
    st.success("Algae bloom detection selected 🟢")
    st.write("Use this view as visual screening only. Real algae detection needs more spectral logic and field validation.")

elif analysis == "Ålgräs / shallow water":
    st.success("Ålgräs / shallow water selected 🌱")
    st.write("Inspect shallow coastal vegetation patterns in clear, shallow bays. GNSS or field checks are recommended.")

elif analysis == "Flood risk":
    st.success("Flood risk selected 🌊")
    st.write("Use SAR + NDWI + terrain data later. SAR is useful because it can work through clouds and at night.")

elif analysis == "Solar potential":
    st.success("Solar potential selected ☀️")
    st.write("Future version: combine terrain, slope, aspect, buildings and shadow analysis.")

else:
    st.info("Use layer controls, analysis mode and opacity sliders to compare imagery.")

report_text = build_report(
    area=area,
    analysis=analysis,
    compare_dates=compare_dates,
    date_range_a=date_range_a,
    date_range_b=date_range_b,
    scene_a_id=scene_a_id,
    scene_b_id=scene_b_id,
    sar_id=sar_id,
    ndvi_stats=ndvi_stats,
    ndwi_stats=ndwi_stats,
    change_stats=change_stats,
)

st.download_button(
    label="📊 Generate Detailed Report",
    data=report_text,
    file_name="geoteka_detailed_report.txt",
    mime="text/plain",
)
