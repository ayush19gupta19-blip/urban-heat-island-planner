import numpy as np
import rasterio
from rasterio.transform import from_origin

from src.ingestion.worldpop import _reproject_sum, worldpop_raster_url


def test_worldpop_urls_target_official_india_2020_rasters():
    population = worldpop_raster_url("population")
    age_65 = worldpop_raster_url("age", 65)
    assert population.startswith("https://data.worldpop.org/GIS/Population/")
    assert "ind_pop_2020_CN_1km_R2025A_UA_v1.tif" in population
    assert "ind_t_65_2020_CN_1km_R2025A_UA_v1.tif" in age_65


def test_reproject_sum_preserves_counts_when_aggregating_grid_cells(tmp_path):
    source_path = tmp_path / "counts.tif"
    values = np.array([[1, 2], [3, 4]], dtype="float32")
    with rasterio.open(
        source_path,
        "w",
        driver="GTiff",
        height=2,
        width=2,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=from_origin(0, 2, 1, 1),
        nodata=-9999,
    ) as raster:
        raster.write(values, 1)

    counts, coverage = _reproject_sum(source_path, [0, 0, 2, 2], rows=1, cols=1)

    assert counts.shape == (1, 1)
    assert np.isclose(counts[0, 0], values.sum())
    assert np.isclose(coverage[0, 0], 1)
