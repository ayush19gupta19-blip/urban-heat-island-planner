# Public Dataset Inventory

Status checked: 2026-10-19

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

### 6. WorldPop 2020 population counts — population exposure

- **Coverage:** Global; therefore includes all three cities.
- **Use:** Population-density and exposure estimates when city-level census rasters are unavailable.
- **Access:** GeoTIFF download from the WorldPop data hub.
- **Source:** <https://www.worldpop.org/geodata/summary?id=24777>
- **Resolution:** The confirmed page is a 1 km population-count product. It is suitable for a first exposure estimate, not for fine-grained household-level analysis.
- **License:** CC BY 4.0 with attribution.
- **Caveat:** The 1 km product can smooth neighborhood differences. We should use a finer WorldPop product or census ward data if the final intervention recommendations require street-level precision.

## City-by-city availability

| Dataset | Ahmedabad | Delhi | Kolkata | MVP decision |
|---|---:|---:|---:|---|
| NASA POWER weather | Confirmed | Confirmed | Confirmed | Core |
| Landsat archive | Global coverage | Global coverage | Global coverage | Core |
| Sentinel-2 archive | Global coverage | Global coverage | Global coverage | Core |
| OSM/Geofabrik India | Covered | Covered | Covered | Core |
| geoBoundaries India | District reference | District reference | District reference | Core boundary QA |
| WorldPop 2020 | Covered | Covered | Covered | Core exposure baseline |
| Official census/ward demographics | Candidate | Candidate | Candidate | Optional until acquisition is verified |

## First real-data ingestion order

1. Download or query the city boundary and create the common analysis grid.
2. Pull NASA POWER daily weather for each city and cache it in `data/raw/weather/`.
3. Add one cloud-filtered Landsat seasonal composite for land-surface temperature.
4. Add Sentinel-2 NDVI/vegetation coverage.
5. Clip OSM features and aggregate building, road, park, and water indicators to the grid.
6. Add WorldPop population counts and calculate exposed population.
7. Validate missingness, spatial alignment, units, and licenses before training the model.

## Important data-quality rule

We will not call a city-level heat-risk estimate “validated” until it is compared with independent observations or a documented reference product. The current synthetic baseline remains a software and workflow test fixture only.
