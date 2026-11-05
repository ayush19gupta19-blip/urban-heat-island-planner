"""Download public ADM2 boundaries and OSM cooling layers for the pilot cities."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.synthetic_data import CITY_PROFILES

RAW = ROOT / "data" / "raw"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
GEOBOUNDARIES_SIMPLIFIED = (
    "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/IND/ADM2/"
    "geoBoundaries-IND-ADM2_simplified.geojson"
)
HEADERS = {"User-Agent": "urban-heat-island-planner/1.0"}


def fetch_geoboundaries() -> None:
    dest_dir = RAW / "boundaries"
    dest_dir.mkdir(parents=True, exist_ok=True)
    full_path = dest_dir / "geoBoundaries-IND-ADM2_simplified.geojson"
    if not full_path.exists() or full_path.stat().st_size == 0:
        response = requests.get(GEOBOUNDARIES_SIMPLIFIED, headers=HEADERS, timeout=180)
        response.raise_for_status()
        full_path.write_bytes(response.content)
    payload = json.loads(full_path.read_text(encoding="utf-8"))
    for city, profile in CITY_PROFILES.items():
        min_lon, min_lat, max_lon, max_lat = profile["bbox"]
        kept = []
        for feature in payload.get("features", []):
            geometry = feature.get("geometry") or {}
            coords = geometry.get("coordinates")
            if not coords:
                continue
            flat = []
            stack = [coords]
            while stack:
                item = stack.pop()
                if item and isinstance(item[0], (int, float)):
                    flat.append(item)
                else:
                    stack.extend(item)
            xs = [pt[0] for pt in flat]
            ys = [pt[1] for pt in flat]
            if max(xs) < min_lon or min(xs) > max_lon or max(ys) < min_lat or min(ys) > max_lat:
                continue
            kept.append(feature)
        out = dest_dir / f"{profile['code'].lower()}_adm2.geojson"
        out.write_text(json.dumps({"type": "FeatureCollection", "features": kept}), encoding="utf-8")
        print(f"{city}: {len(kept)} ADM2 polygons -> {out}")


def fetch_osm_cooling_features(city: str) -> None:
    min_lon, min_lat, max_lon, max_lat = CITY_PROFILES[city]["bbox"]
    query = f"""
    [out:json][timeout:90];
    (
      way["leisure"="park"]({min_lat},{min_lon},{max_lat},{max_lon});
      way["natural"="water"]({min_lat},{min_lon},{max_lat},{max_lon});
      way["landuse"="reservoir"]({min_lat},{min_lon},{max_lat},{max_lon});
      node["amenity"~"hospital|clinic|community_centre"]({min_lat},{min_lon},{max_lat},{max_lon});
    );
    out geom;
    """
    response = requests.post(OVERPASS_URL, data={"data": query}, headers=HEADERS, timeout=120)
    response.raise_for_status()
    features = []
    for element in response.json().get("elements", []):
        tags = element.get("tags", {})
        kind = tags.get("leisure") or tags.get("natural") or tags.get("landuse") or tags.get("amenity") or "unknown"
        if element["type"] == "node":
            geometry = {"type": "Point", "coordinates": [element["lon"], element["lat"]]}
        elif element.get("geometry"):
            coords = [(pt["lon"], pt["lat"]) for pt in element["geometry"]]
            if len(coords) < 3:
                continue
            if coords[0] != coords[-1]:
                coords.append(coords[0])
            geometry = {"type": "Polygon", "coordinates": [coords]}
        else:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {"city": city, "osm_id": element["id"], "kind": kind, "name": tags.get("name")},
            }
        )
    dest = RAW / "osm"
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / f"{CITY_PROFILES[city]['code'].lower()}_parks_water_amenities.geojson"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")
    print(f"{city}: {len(features)} OSM features -> {path}")


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    print("== geoBoundaries ==")
    fetch_geoboundaries()
    print("== OSM parks / water / amenities ==")
    for city in CITY_PROFILES:
        try:
            fetch_osm_cooling_features(city)
        except Exception as exc:
            print(f"{city}: OSM fetch failed ({exc.__class__.__name__}: {exc})")


if __name__ == "__main__":
    main()
