"""WorldPop Global2 population and age-65+ raster ingestion."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
import requests
from pyproj import Geod
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.warp import reproject


YEAR = 2020
RELEASE = "R2025A"
VERSION = "v1"
RESOLUTION = "1km"
ELDERLY_AGE_BANDS = (65, 70, 75, 80, 85, 90)
POPULATION_DOI = "10.5258/SOTON/WP00840"
AGE_SEX_DOI = "10.5258/SOTON/WP00842"
WORLDPOP_BASE = "https://data.worldpop.org/GIS"


def worldpop_raster_url(kind: str, age_band: int | None = None) -> str:
    """Return an official WorldPop Global2 raster URL for India."""
    if kind == "population":
        filename = f"ind_pop_{YEAR}_CN_{RESOLUTION}_{RELEASE}_UA_{VERSION}.tif"
    elif kind == "age" and age_band in ELDERLY_AGE_BANDS:
        filename = f"ind_t_{age_band}_{YEAR}_CN_{RESOLUTION}_{RELEASE}_UA_{VERSION}.tif"
    else:
        raise ValueError("kind must be 'population' or an age band in the 65+ dataset")
    category = "Population" if kind == "population" else "AgeSex_structures"
    return (
        f"{WORLDPOP_BASE}/{category}/Global_2015_2030/{RELEASE}/{YEAR}/IND/"
        f"{VERSION}/{RESOLUTION}_ua/constrained/{filename}"
    )


def _download_if_needed(url: str, path: Path, session: requests.Session) -> Path:
    """Download a public raster once, using an incomplete temporary file."""
    if path.exists() and path.stat().st_size > 0:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".download")
    try:
        with session.get(url, stream=True, timeout=180) as response:
            response.raise_for_status()
            with temporary.open("wb") as output:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        output.write(chunk)
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return path


def _reproject_sum(path: Path, bbox: list[float], rows: int, cols: int) -> tuple[np.ndarray, np.ndarray]:
    """Aggregate source pixel counts into the project grid and return coverage."""
    west, south, east, north = bbox
    target_transform = from_origin(west, north, (east - west) / cols, (north - south) / rows)
    counts = np.zeros((rows, cols), dtype="float64")
    coverage = np.zeros((rows, cols), dtype="float32")
    with rasterio.open(path) as source:
        if source.crs is None:
            raise ValueError(f"WorldPop raster has no coordinate reference system: {path}")
        source_values = source.read(1)
        reproject(
            source=source_values,
            destination=counts,
            src_transform=source.transform,
            src_crs=source.crs,
            src_nodata=source.nodata,
            dst_transform=target_transform,
            dst_crs="EPSG:4326",
            dst_nodata=0,
            resampling=Resampling.sum,
        )
        valid = (source.read_masks(1) > 0).astype("float32")
        reproject(
            source=valid,
            destination=coverage,
            src_transform=source.transform,
            src_crs=source.crs,
            dst_transform=target_transform,
            dst_crs="EPSG:4326",
            dst_nodata=0,
            resampling=Resampling.average,
        )
    # Raster row zero is north; the planner's grid row zero is south.
    return np.flipud(counts), np.flipud(np.clip(coverage, 0, 1))


def _cell_areas_km2(bbox: list[float], rows: int, cols: int) -> np.ndarray:
    west, south, east, north = bbox
    geod = Geod(ellps="WGS84")
    areas = np.empty((rows, cols), dtype="float64")
    for row in range(rows):
        cell_south = south + row * (north - south) / rows
        cell_north = south + (row + 1) * (north - south) / rows
        area_m2, _ = geod.polygon_area_perimeter(
            [west, east, east, west],
            [cell_south, cell_south, cell_north, cell_north],
        )
        areas[row, :] = abs(area_m2) / 1_000_000
    return areas


def fetch_city_population(
    city: str,
    bbox: list[float],
    rows: int,
    cols: int,
    output_dir: Path,
    session: requests.Session | None = None,
) -> dict[str, np.ndarray | str | int]:
    """Fetch and aggregate WorldPop population and age 65+ counts for a city grid.

    Source rasters are cached locally under ``output_dir`` and are not written
    into the repository. Population and age estimates represent 2020.
    """
    if rows < 1 or cols < 1:
        raise ValueError("rows and cols must both be positive")
    if len(bbox) != 4 or bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
        raise ValueError("bbox must be [west, south, east, north]")
    client = session or requests.Session()
    cache_dir = output_dir / "worldpop" / "india"
    cache_dir.mkdir(parents=True, exist_ok=True)

    population_path = _download_if_needed(
        worldpop_raster_url("population"),
        cache_dir / f"population_{YEAR}_{RESOLUTION}_{RELEASE}.tif",
        client,
    )
    population_count, population_coverage = _reproject_sum(population_path, bbox, rows, cols)

    elderly_count = np.zeros((rows, cols), dtype="float64")
    age_coverages = []
    for age_band in ELDERLY_AGE_BANDS:
        age_path = _download_if_needed(
            worldpop_raster_url("age", age_band),
            cache_dir / f"age_{age_band}_{YEAR}_{RESOLUTION}_{RELEASE}.tif",
            client,
        )
        age_count, age_coverage = _reproject_sum(age_path, bbox, rows, cols)
        elderly_count += age_count
        age_coverages.append(age_coverage)

    area = _cell_areas_km2(bbox, rows, cols)
    elderly_share = np.divide(
        elderly_count,
        population_count,
        out=np.zeros_like(elderly_count),
        where=population_count > 0,
    )
    return {
        "population_count": population_count,
        "population_density": population_count / area,
        "elderly_population_65_plus": elderly_count,
        "elderly_share": np.clip(elderly_share, 0, 1),
        "population_data_coverage": population_coverage,
        "elderly_data_coverage": np.minimum.reduce(age_coverages),
        "population_data_year": YEAR,
        "population_data_source": f"WorldPop Global2 R2025A v1, {YEAR}, 1 km, DOI {POPULATION_DOI}",
        "elderly_data_source": f"WorldPop age/sex structures, age 65+, {YEAR}, 1 km, DOI {AGE_SEX_DOI}",
    }
