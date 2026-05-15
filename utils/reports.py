from datetime import datetime


def build_report(
    area,
    analysis,
    compare_dates,
    date_range_a,
    date_range_b,
    scene_a_id,
    scene_b_id,
    sar_id,
    ndvi_stats=None,
    ndwi_stats=None,
    change_stats=None,
):
    ndvi_text = "Not calculated"
    if ndvi_stats:
        ndvi_text = f"""
Detected vegetation pixels: {ndvi_stats['pixels']}
Approximate vegetation area: {ndvi_stats['area_m2']:,.0f} m²
Approximate vegetation area: {ndvi_stats['area_ha']:,.2f} ha
Threshold: {ndvi_stats['threshold']}
"""

    ndwi_text = "Not calculated"
    if ndwi_stats:
        ndwi_text = f"""
Detected water/wet pixels: {ndwi_stats['pixels']}
Approximate water/wet area: {ndwi_stats['area_m2']:,.0f} m²
Approximate water/wet area: {ndwi_stats['area_ha']:,.2f} ha
Threshold: {ndwi_stats['threshold']}
"""

    change_text = "Not calculated"
    if change_stats:
        change_text = f"""
Positive change pixels: {change_stats['positive_pixels']}
Positive change area: {change_stats['positive_area_m2']:,.0f} m² / {change_stats['positive_area_ha']:,.2f} ha
Negative change pixels: {change_stats['negative_pixels']}
Negative change area: {change_stats['negative_area_m2']:,.0f} m² / {change_stats['negative_area_ha']:,.2f} ha
"""

    return f"""
GeoTeka Baltic Dashboard Report

Generated:
{datetime.now().strftime('%Y-%m-%d %H:%M')}

Area:
{area}

Selected analysis:
{analysis}

Comparison mode:
{compare_dates}

Date A / older baseline:
{date_range_a}

Date B / newer comparison:
{date_range_b}

Loaded satellite scenes:

Sentinel-2 Date A:
{scene_a_id}

Sentinel-2 Date B:
{scene_b_id}

Sentinel-1 SAR:
{sar_id}

NDVI vegetation health:

Formula:
NDVI = (NIR - Red) / (NIR + Red)

For Sentinel-2:
NIR = B08
Red = B04

NDVI statistics:
{ndvi_text}

NDWI water detection:

Formula:
NDWI = (Green - NIR) / (Green + NIR)

For Sentinel-2:
Green = B03
NIR = B08

NDWI statistics:
{ndwi_text}

Change detection:
{change_text}

Important limitations:
- Sentinel-2 main bands have 10 meter resolution.
- Cloud, haze, shallow water, bottom reflection and waves can affect results.
- This is an indicative GIS/remote sensing analysis, not legal boundary evidence.
- Field checks with GNSS are recommended for validation.

Recommended next step:
1. Validate one Gotland bay with GNSS points.
2. Compare satellite-derived water/shoreline zones with field observations.
3. Export maps and statistics into a PDF report.
4. Add weather and sea-level context.
"""
