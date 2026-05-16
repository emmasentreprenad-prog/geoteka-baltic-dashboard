import streamlit as st
from pystac_client import Client


@st.cache_data(show_spinner=False)
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
