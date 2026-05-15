import streamlit as st
import leafmap.foliumap as leafmap
import planetary_computer
import numpy as np
from folium.plugins import Draw

from config import AREAS, CENTERS, ANALYSIS_MODES
from utils.logo import create_clean_logo
from utils.sentinel import search_sentinel1, search_sentinel2
from utils.raster_analysis import (
    calculate_area_stats,
    calculate_change,
    calculate_change_stats,
    calculate_ndvi,
    calculate_ndwi,
    build_coastal_contact_zone_mask,
    build_line_buffer_mask,
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
        "polygon": False,
        "rectangle": False,
        "circle": False,
        "marker": True,
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

s2_a_item = None
s2_b_item = None
calculated_ndvi = None
calculated_ndwi = None
calculated_change = None
ndvi_stats = None
ndwi_stats = None
change_stats = None
coastal_contact_zone_mask = None
section_mask = None

# Load Date A if comparison is enabled
if compare_dates:
    try:
        with st.spinner("Loading Sentinel-2 Date A..."):
            s2_a_items = search_sentinel2(bbox, date_range_a, cloud_cover)

        if len(s2_a_items) > 0:
            s2_a_item = s2_a_items[0]
            s2_a_signed = planetary_computer.sign(s2_a_item)
            scene_a_id = s2_a_item.id

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
            coastal_contact_zone_mask = build_coastal_contact_zone_mask(
                ndwi_a,
                transform_a,
                crs_a,
                ndwi_b,
                transform_b,
                crs_b,
                water_threshold=0.2,
                buffer_pixels=3,
            )
            selected_line_coords = st.session_state.get("coastline_section_coords")
            if selected_line_coords is not None:
                section_mask = build_line_buffer_mask(
                    selected_line_coords,
                    coastline_buffer_m,
                    calculated_change.shape,
                    transform_a,
                    crs_a,
                )
            active_mask = section_mask if section_mask is not None else coastal_contact_zone_mask
            masked_change = np.where(active_mask, calculated_change, np.nan)
            add_array_overlay(
                m,
                masked_change,
                bbox,
                "REAL NDWI change Date B minus Date A",
                cmap_name="RdBu",
                opacity=opacity_b / 100,
                vmin=-0.5,
                vmax=0.5,
                visible_mask=active_mask,
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

map_state = m.to_streamlit(height=560, bidirectional=True)

if map_state:
    latest_line = None
    for drawing in (map_state.get("all_drawings") or [])[::-1]:
        geometry = drawing.get("geometry", {})
        coords = geometry.get("coordinates", [])
        if geometry.get("type") == "LineString" and len(coords) >= 2:
            latest_line = [[coords[0][1], coords[0][0]], [coords[-1][1], coords[-1][0]]]
            break

    if latest_line is None:
        marker_points = []
        for drawing in map_state.get("all_drawings") or []:
            geometry = drawing.get("geometry", {})
            coords = geometry.get("coordinates", [])
            if geometry.get("type") == "Point" and len(coords) == 2:
                marker_points.append([coords[1], coords[0]])
        if len(marker_points) >= 2:
            latest_line = [marker_points[-2], marker_points[-1]]

    previous_line = st.session_state.get("coastline_section_coords")
    if latest_line is not None:
        if previous_line != latest_line:
            st.session_state["coastline_section_coords"] = latest_line
            st.rerun()
    elif (map_state.get("all_drawings") == []):
        if previous_line is not None:
            st.session_state["coastline_section_coords"] = None
            st.rerun()

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

    selected_line = st.session_state.get("coastline_section_coords")
    if selected_line is None:
        st.info("Draw or select a coastline section to analyse.")

    active_mask = section_mask if section_mask is not None else coastal_contact_zone_mask
    change_stats = calculate_change_stats(
        calculated_change,
        positive_threshold=positive_threshold,
        negative_threshold=negative_threshold,
        contact_zone_mask=active_mask,
    )

    st.write(f"Positive change area: {change_stats['positive_area_m2']:,.0f} m²")
    st.write(f"Positive change area: {change_stats['positive_area_ha']:,.2f} ha")
    st.write(f"Negative change area: {change_stats['negative_area_m2']:,.0f} m²")
    st.write(f"Negative change area: {change_stats['negative_area_ha']:,.2f} ha")

    st.caption(
        "Debug — valid pixels used: "
        f"{change_stats['valid_pixels']:,} | "
        f"pixel area: {change_stats['pixel_area_m2']:,} m² | "
        f"total analysed mask area: {change_stats['analysed_mask_area_ha']:,.2f} ha"
    )
    st.caption(
        "Debug — selected line coordinates: "
        f"{selected_line} | buffer distance: {coastline_buffer_m} m | "
        f"valid analysed pixels: {change_stats['valid_pixels']:,} | "
        f"analysed area: {change_stats['analysed_mask_area_ha']:,.2f} ha"
    )

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
