"""Cloud-filtered Landsat and Sentinel-2 grid extraction via public STAC."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import planetary_computer
import rasterio
import requests
from rasterio.enums import Resampling
from rasterio.windows import Window, from_bounds
from rasterio.warp import transform_bounds

from src.synthetic_data import CITY_PROFILES


STAC_SEARCH_URL = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
BAD_SCL_CLASSES = {0, 1, 3, 8, 9, 10, 11}
LANDSAT_ST_SCALE = 0.00341802
LANDSAT_ST_OFFSET_K = 149.0


def search_best_item(
    collection: str,
    bbox: tuple[float, float, float, float],
    start_date: str,
    end_date: str,
    max_cloud_cover: float = 30.0,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    """Return the least-cloudy item intersecting the requested city bbox."""
    payload = {
        "collections": [collection],
        "bbox": list(bbox),
        "datetime": f"{start_date}T00:00:00Z/{end_date}T23:59:59Z",
        "limit": 100,
        "query": {"eo:cloud_cover": {"lt": max_cloud_cover}},
    }
    client = session or requests.Session()
    response = client.post(STAC_SEARCH_URL, json=payload, timeout=90)
    response.raise_for_status()
    features = response.json().get("features", [])
    if not features:
        raise RuntimeError(
            f"No {collection} item found for bbox={bbox}, dates={start_date}:{end_date}, "
            f"cloud limit={max_cloud_cover}%"
        )
    return min(features, key=lambda item: item.get("properties", {}).get("eo:cloud_cover", 999.0))


def _read_asset_grid(
    href: str,
    bbox: tuple[float, float, float, float],
    rows: int,
    cols: int,
    resampling: Resampling = Resampling.average,
) -> np.ndarray:
    """Read a city window from a remote COG and downsample it to the grid."""
    signed_href = planetary_computer.sign(href)
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
        with rasterio.open(signed_href) as dataset:
            if dataset.crs is None:
                raise ValueError(f"Raster asset has no CRS: {href}")
            left, bottom, right, top = transform_bounds("EPSG:4326", dataset.crs, *bbox, densify_pts=21)
            window = from_bounds(left, bottom, right, top, transform=dataset.transform)
            dataset_window = Window.from_slices((0, dataset.height), (0, dataset.width))
            window = window.intersection(dataset_window)
            if window.width <= 0 or window.height <= 0:
                raise ValueError(f"City bbox does not overlap raster asset: {href}")
            return dataset.read(
                1,
                window=window,
                out_shape=(rows, cols),
                resampling=resampling,
                masked=False,
            ).astype("float32")


def _asset_href(item: dict[str, Any], key: str) -> str:
    try:
        return item["assets"][key]["href"]
    except KeyError as exc:
        raise ValueError(f"STAC item {item.get('id')} has no {key!r} asset") from exc


def extract_landsat_grids(
    item: dict[str, Any],
    bbox: tuple[float, float, float, float],
    rows: int,
    cols: int,
) -> dict[str, np.ndarray]:
    """Extract Celsius land-surface temperature and NDBI proxy grids."""
    raw_st = _read_asset_grid(_asset_href(item, "lwir11"), bbox, rows, cols)
    qa = _read_asset_grid(_asset_href(item, "qa_pixel"), bbox, rows, cols, Resampling.nearest).astype("uint16")
    nir = _read_asset_grid(_asset_href(item, "nir08"), bbox, rows, cols)
    swir = _read_asset_grid(_asset_href(item, "swir16"), bbox, rows, cols)

    clear = (qa & 0b111111) == 0
    land_surface_temp_c = raw_st * LANDSAT_ST_SCALE + LANDSAT_ST_OFFSET_K - 273.15
    land_surface_temp_c[~clear | (raw_st <= 0)] = np.nan

    with np.errstate(divide="ignore", invalid="ignore"):
        ndbi = (swir - nir) / (swir + nir)
    ndbi[~clear | (nir <= 0) | (swir <= 0)] = np.nan
    built_up_fraction = np.clip((ndbi + 0.2) / 0.6, 0, 1)
    return {
        "land_surface_temp_c": land_surface_temp_c,
        "ndbi": ndbi,
        "built_up_fraction": built_up_fraction,
        "landsat_valid": clear & (raw_st > 0) & np.isfinite(land_surface_temp_c),
    }


def extract_sentinel_grids(
    item: dict[str, Any],
    bbox: tuple[float, float, float, float],
    rows: int,
    cols: int,
) -> dict[str, np.ndarray]:
    """Extract cloud-masked Sentinel-2 NDVI and water-surface proxy grids."""
    red = _read_asset_grid(_asset_href(item, "B04"), bbox, rows, cols) / 10000.0
    nir = _read_asset_grid(_asset_href(item, "B08"), bbox, rows, cols) / 10000.0
    scl = _read_asset_grid(_asset_href(item, "SCL"), bbox, rows, cols, Resampling.nearest).astype("uint8")
    valid = ~np.isin(scl, list(BAD_SCL_CLASSES))
    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = (nir - red) / (nir + red)
    ndvi[~valid | ((nir + red) <= 0)] = np.nan
    water_surface_fraction = (scl == 6).astype("float32")
    return {
        "vegetation_index": np.clip(ndvi, -1, 1),
        "water_surface_fraction": water_surface_fraction,
        "sentinel_valid": valid & np.isfinite(ndvi),
    }


def extract_city_satellite_features(
    city: str,
    start_date: str,
    end_date: str,
    rows: int = 20,
    cols: int = 20,
    max_cloud_cover: float = 30.0,
    metadata_dir: Path | None = None,
) -> dict[str, Any]:
    """Find and process the best Landsat and Sentinel scenes for one city."""
    if city not in CITY_PROFILES:
        raise ValueError(f"Unsupported city: {city}. Choose from {sorted(CITY_PROFILES)}")
    bbox = tuple(CITY_PROFILES[city]["bbox"])
    landsat_item = search_best_item("landsat-c2-l2", bbox, start_date, end_date, max_cloud_cover)
    sentinel_item = search_best_item("sentinel-2-l2a", bbox, start_date, end_date, max_cloud_cover)
    result = {
        **extract_landsat_grids(landsat_item, bbox, rows, cols),
        **extract_sentinel_grids(sentinel_item, bbox, rows, cols),
        "metadata": {
            "city": city,
            "bbox": bbox,
            "start_date": start_date,
            "end_date": end_date,
            "landsat_item": landsat_item["id"],
            "landsat_cloud_cover": landsat_item["properties"].get("eo:cloud_cover"),
            "sentinel_item": sentinel_item["id"],
            "sentinel_cloud_cover": sentinel_item["properties"].get("eo:cloud_cover"),
        },
    }
    if metadata_dir is not None:
        import json

        metadata_dir.mkdir(parents=True, exist_ok=True)
        path = metadata_dir / f"{CITY_PROFILES[city]['code'].lower()}_satellite.json"
        path.write_text(json.dumps(result["metadata"], indent=2), encoding="utf-8")
    return result
