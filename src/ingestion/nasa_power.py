"""NASA POWER daily weather ingestion."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import requests

from src.synthetic_data import CITY_PROFILES


POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
POWER_PARAMETERS = "T2M,RH2M,WS10M,PRECTOTCORR,ALLSKY_SFC_SW_DWN"


def parse_power_payload(payload: dict[str, Any], city: str) -> pd.DataFrame:
    """Convert a NASA POWER JSON response to a tidy daily table."""
    try:
        parameters = payload["properties"]["parameter"]
    except (KeyError, TypeError) as exc:
        raise ValueError("NASA POWER response has no properties.parameter object") from exc

    dates = sorted(set().union(*(values.keys() for values in parameters.values())))
    frame = pd.DataFrame({"date": pd.to_datetime(dates, format="%Y%m%d")})
    for name, values in parameters.items():
        frame[name.lower()] = [values.get(date) for date in dates]
    frame.insert(0, "city", city)
    frame["date"] = frame["date"].dt.strftime("%Y-%m-%d")
    return frame


def fetch_daily_weather(
    city: str,
    start_date: str,
    end_date: str,
    output_dir: Path | None = None,
    session: requests.Session | None = None,
) -> pd.DataFrame:
    """Fetch and optionally cache daily weather for one pilot city."""
    if city not in CITY_PROFILES:
        raise ValueError(f"Unsupported city: {city}. Choose from {sorted(CITY_PROFILES)}")
    if start_date > end_date:
        raise ValueError("start_date must be on or before end_date")

    profile = CITY_PROFILES[city]
    params = {
        "parameters": POWER_PARAMETERS,
        "community": "SB",
        "longitude": profile["lon"],
        "latitude": profile["lat"],
        "start": start_date.replace("-", ""),
        "end": end_date.replace("-", ""),
        "format": "JSON",
        "time-standard": "LST",
    }
    client = session or requests.Session()
    response = client.get(POWER_URL, params=params, timeout=60)
    response.raise_for_status()
    frame = parse_power_payload(response.json(), city)

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"{profile['code'].lower()}_power_{start_date}_{end_date}.csv"
        frame.to_csv(path, index=False)
    return frame


def fetch_all_weather(
    cities: list[str],
    start_date: str,
    end_date: str,
    output_dir: Path | None = None,
) -> pd.DataFrame:
    """Fetch weather for multiple cities and combine it into one table."""
    frames = [fetch_daily_weather(city, start_date, end_date, output_dir) for city in cities]
    return pd.concat(frames, ignore_index=True)
