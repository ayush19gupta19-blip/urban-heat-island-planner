# Public Dataset Inventory

Status checked: 2026-11-03

The three pilot cities are Ahmedabad, Delhi, and Kolkata. The inventory below separates **confirmed usable sources** from optional sources that still need an acquisition check. No private credentials are required for the core MVP.

## Confirmed core sources

### 1. NASA POWER Daily API — weather and climate

- **Coverage:** Ahmedabad, Delhi, and Kolkata; global point and regional service.
- **Variables for MVP:** 2 m temperature (`T2M`), relative humidity (`RH2M`), and 10 m wind speed (`WS10M`).
- **History:** Daily UTC/LST data from 1981 to near real time according to the API documentation.
- **Access:** HTTPS API; no API key required for the planned low-volume extraction.
- **Source:** <https://power.larc.nasa.gov/docs/services/api/temporal/daily/>
- **License/citation:** Follow NASA POWER terms and cite POWER/MERRA-2 as requested by the service.
- **Verification:** Point requests returned data for all three pilot-city coordinates on 2024-01-01 to 2024-01-03.

Pilot coordinates used for the connectivity check:

```text
Ahmedabad 23.02, 72.50
Delhi      28.61, 77.20
Kolkata    22.57, 88.36
```

### 2. Landsat Collection 2 — land-surface temperature and vegetation

- **Coverage:** All three cities are within Landsat's global archive.
- **Use:** Thermal infrared land-surface temperature and multispectral bands for NDVI, built-up indicators, and seasonal composites.
- **Access:** USGS EarthExplorer, LandsatLook, or cloud-hosted Landsat catalogues.
- **Source:** <https://www.usgs.gov/landsat-missions/landsat-data-access>
- **Resolution:** Use the relevant Landsat product resolution and QA bands; exact product selection will be recorded in the ingestion script.
- **Caveat:** Cloud masking and acquisition-date selection are essential. Land-surface temperature is not the same as 2 m air temperature.

### 3. Copernicus Sentinel-2 — vegetation and land cover

- **Coverage:** All three cities are within Sentinel-2's global archive.
- **Use:** NDVI/EVI, vegetation coverage, water and impervious-surface proxies, and cloud-filtered seasonal imagery.
- **Access:** Copernicus Data Space Ecosystem or EO Browser.
- **Source:** <https://dataspace.copernicus.eu/> and <https://www.sentinel-hub.com/explore/eobrowser/>
- **Resolution:** Multi-band imagery includes 10 m bands suitable for neighborhood-scale vegetation features.
- **Caveat:** Sentinel-2 does not provide thermal land-surface temperature; pair it with Landsat or weather data.

### 4. OpenStreetMap India extract — buildings, roads, parks, and water

- **Coverage:** All three cities are covered by the India extract.
- **Use:** Building density, road density, parks, water bodies, public facilities, and candidate cooling-centre locations.
- **Access:** Download India `.osm.pbf` or a regional GeoPackage and clip it to each city boundary.
- **Source:** <https://download.geofabrik.de/asia/india.html>
- **License:** OpenStreetMap data is provided under ODbL 1.0; preserve attribution and review share-alike obligations for derived database distributions.
- **Verification:** Geofabrik lists a current India `.osm.pbf` and regional extracts.
- **Caveat:** Completeness differs by feature and neighborhood. We must calculate coverage indicators instead of treating missing OSM objects as absence.

### 5. geoBoundaries India ADM2 — district-level boundary reference

- **Coverage:** India-wide; contains the administrative district layer that includes Ahmedabad, Delhi-area districts, and Kolkata-area districts.
- **Use:** Reproducible regional clipping and a reference layer for checking city-area boundaries.
- **Access:** GeoJSON or ZIP download from the geoBoundaries API.
- **Source:** <https://www.geoboundaries.org/api/current/gbOpen/IND/ADM2/>
- **License:** Open Database License 1.0 as reported by the API.
- **Verification:** The API returned the India ADM2 metadata and download links, including a GeoJSON endpoint.
- **Caveat:** ADM2 is a district layer, not a perfect municipal boundary. City boundaries must be validated separately using municipal or OSM boundary relations.

### 6. WorldPop Global2 population and age structure

- **Coverage:** India, including the three pilot cities.
- **Use:** 2020 population count and density, plus gridded age-65+ population count and share for an age-based vulnerability feature.
- **Source:** [2020 population counts, India](https://hub.worldpop.org/geodata/summary?id=77674) and [2020 age/sex structures, India](https://hub.worldpop.org/geodata/summary?id=97050).
- **Resolution:** 1 km GeoTIFFs in WGS84. Age-65+ is summed from the 65, 70, 75, 80, 85, and 90+ bands.
- **Release and citation:** Global2 R2025A v1; population DOI [10.5258/SOTON/WP00840](https://doi.org/10.5258/SOTON/WP00840), age/sex DOI [10.5258/SOTON/WP00842](https://doi.org/10.5258/SOTON/WP00842).
- **License:** CC BY 4.0; retain attribution and assess responsible-use constraints.
- **Pipeline behavior:** The real pipeline caches the India-wide rasters under `data/raw/worldpop/india/` and aggregates counts to the analysis grid. The cached rasters are ignored by Git.
- **Caveat:** These are modeled 2020 estimates, not current census counts or ward-level observations. One-kilometre cells smooth local differences and should not support individual-level decisions.

### 7. Census of India Primary Census Abstract (ward tables)

- **Coverage:** The official Population Finder provides 85 indicators at ward, town, sub-district, and district levels for Census 2011, including age-group population and demographic indicators.
- **Source:** [Population Finder 2011](https://censusindia.mha.gov.in/census.website/data/population-finder).
- **Potential use:** Ward-level vulnerability attributes after matching town/ward codes to compatible municipal ward boundaries.
- **Status:** Source confirmed; the ward table and boundary join are not yet integrated. Census 2011 is old and ward boundaries may have changed, so this layer must show its year and matching coverage.

## City-by-city availability

| Dataset | Ahmedabad | Delhi | Kolkata | MVP decision |
|---|---:|---:|---:|---|
| NASA POWER weather | Confirmed | Confirmed | Confirmed | Core |
| Landsat archive | Global coverage | Global coverage | Global coverage | Core |
| Sentinel-2 archive | Global coverage | Global coverage | Global coverage | Core |
| OSM/Geofabrik India | Covered | Covered | Covered | Core |
| geoBoundaries India | District reference | District reference | District reference | Core boundary QA |
| WorldPop Global2 2020 count and age 65+ | Covered | Covered | Covered | Core gridded exposure and vulnerability |
| Census 2011 ward demographics and matching boundaries | Candidate | Candidate | Candidate | Pending ward-code and boundary alignment |

## First real-data ingestion order

1. Download or query the city boundary and create the common analysis grid.
2. Pull NASA POWER daily weather for each city and cache it in `data/raw/weather/`.
3. Add one cloud-filtered Landsat seasonal composite for land-surface temperature.
4. Add Sentinel-2 NDVI/vegetation coverage.
5. Clip OSM features and aggregate building, road, park, and water indicators to the grid.
6. Aggregate WorldPop 2020 population and age-65+ rasters to the analysis grid.
7. Match Census 2011 ward indicators to compatible municipal boundaries before adding ward-level attributes.
8. Validate missingness, spatial alignment, units, age definitions, and licenses before training the model.

## Important data-quality rule

We will not call a city-level heat-risk estimate “validated” until it is compared with independent observations or a documented reference product. The current synthetic baseline remains a software and workflow test fixture only.
