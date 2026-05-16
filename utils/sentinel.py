import streamlit as st
from pystac_client import Client


@st.cache_data(show_spinner=False, ttl=900)
def search_sentinel2(bbox, date_range, cloud_cover, limit=10):
    catalog = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")

    search = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=bbox,
        datetime=date_range,
        query={"eo:cloud_cover": {"lt": cloud_cover}},
        limit=limit,
    )

    items = list(search.items())

    if date_range and "/" in str(date_range):
        start_raw, end_raw = str(date_range).split("/", 1)
        start_dt = start_raw.strip()
        end_dt = end_raw.strip()

        def _in_range(item):
            dt = str(item.properties.get("datetime", ""))[:10]
            return bool(dt) and start_dt <= dt <= end_dt

        items = [item for item in items if _in_range(item)]

    items.sort(key=lambda i: i.properties.get("datetime", ""), reverse=True)
    return items


@st.cache_data(show_spinner=False)
def search_sentinel1(bbox, date_range, limit=10):
    catalog = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")

    search = catalog.search(
        collections=["sentinel-1-rtc"],
        bbox=bbox,
        datetime=date_range,
        limit=limit,
    )

    items = list(search.items())
    items.sort(key=lambda i: i.properties.get("datetime", ""), reverse=True)
    return items
