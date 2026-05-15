# GeoTeka Baltic Environmental Intelligence Dashboard

## Project goal

This project is a Streamlit-based GIS and remote sensing dashboard for environmental monitoring in the Baltic Sea region, especially Gotland, Öland and coastal areas.

The long-term goal is to develop GeoTeka into a Baltic Environmental Intelligence Platform for:
- coastal change detection
- NDWI water and wetness monitoring
- NDVI vegetation health monitoring
- flood/wet surface analysis
- Sentinel-1 SAR support
- environmental reports
- future GeoAI anomaly alerts

## Current project status

The app already has:
- Streamlit dashboard
- GeoTeka branding
- sidebar controls
- area selection
- Sentinel-2 search using Microsoft Planetary Computer STAC
- Sentinel-2 visual layers
- real NDWI raster calculation
- real NDVI raster calculation
- basic change detection
- area statistics in pixels, square meters and hectares
- TXT report generation

## Current folder structure

app.py
config.py
requirements.txt

utils/
    __init__.py
    logo.py
    sentinel.py
    raster_analysis.py
    map_layers.py
    reports.py

## Important scientific formulas

NDVI:
NDVI = (NIR - Red) / (NIR + Red)

For Sentinel-2:
NIR = B08
Red = B04

NDWI:
NDWI = (Green - NIR) / (Green + NIR)

For Sentinel-2:
Green = B03
NIR = B08

## Current technical issue

Single-date NDWI works.

However, change detection is not yet scientifically reliable because rasters from Date A and Date B may not be perfectly aligned.

The current priority is to improve raster alignment before interpreting change statistics.

## Next technical task

Fix change detection by ensuring Date A and Date B rasters are aligned to the same:
- CRS
- transform
- pixel grid
- shape
- resolution

Use rasterio.warp.reproject to reproject/resample Date B to match Date A before calculating:

change = NDWI_B_aligned - NDWI_A

## Important warning

Do not interpret change detection statistics as real coastline change yet.

Possible false-change sources:
- raster misalignment
- scene edge/no-data
- cloud
- haze
- waves
- shallow water bottom reflection
- different water level
- different sun angle
- different atmospheric conditions

## Recommended immediate steps

1. Fix raster alignment in utils/raster_analysis.py
2. Update app.py to pass transform and CRS into calculate_change
3. Add no-data masking
4. Add cloud masking if possible
5. Test on small pilot areas, not full Gotland
6. Use Gotland pilot - Fårösund as first validation area
7. Export improved statistics into report
8. Later add PDF report generation

## Pilot areas

The dashboard should focus on smaller analysis areas for serious testing, for example:

- Gotland pilot - Fårösund
- Gotland pilot - Slite
- Gotland pilot - Visby coast
- Gotland pilot - Burgsvik

Avoid interpreting full-Gotland change detection as reliable.

## Thesis direction

Possible thesis title:

Satellite-Based Coastal Change Detection with Sentinel-1/2 and GNSS Validation

This combines:
- surveying
- GNSS field validation
- GIS
- Sentinel satellite data
- remote sensing
- coastal monitoring

## Product direction

GeoTeka can eventually become a service for:
- municipalities
- county administrative boards
- environmental consultants
- coastal planners
- harbours
- climate adaptation projects
- EU environmental monitoring projects

## Current best development priority

Do not add many new features yet.

First make the core analysis reliable:

1. NDWI single-date
2. NDVI single-date
3. aligned NDWI change detection
4. quality warnings
5. report export

Only after that:
- weather data
- sea level data
- SAR flood logic
- AI anomaly detection
- automated alerts