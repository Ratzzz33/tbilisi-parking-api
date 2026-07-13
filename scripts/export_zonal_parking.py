#!/usr/bin/env python3
"""Export official Tbilisi municipal zonal-parking places for GeoDrive CRM.

Writes three artifacts to exports/:
- CSV: addresses and centroid coordinates for spreadsheets/imports;
- GeoJSON: official parking polygons for map layers;
- JSON: records shaped for CRM's map_parking table/API.

The source is the authenticated official municipal API. PARKING_TOKEN is read
from the local .env and is never written to an export.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.client import ParkingClient

OUTPUT = ROOT / "exports"
WKT_POLYGON = re.compile(r"^POLYGON\s*\(\((.+)\)\)$", re.IGNORECASE)


def polygon_coordinates(wkt: str) -> list[list[float]]:
    """Convert POLYGON WKT (longitude latitude) to GeoJSON coordinates."""
    match = WKT_POLYGON.match(wkt.strip())
    if not match:
        raise ValueError("Unsupported or invalid WKT polygon")
    points: list[list[float]] = []
    for pair in match.group(1).split(","):
        lon, lat = pair.strip().split()
        points.append([float(lon), float(lat)])
    if len(points) < 4 or points[0] != points[-1]:
        raise ValueError("Polygon is not a closed ring")
    return points


def centroid(ring: list[list[float]]) -> tuple[float, float]:
    """Return the arithmetic centroid for a small parking-space polygon."""
    unique = ring[:-1]
    return (
        sum(point[1] for point in unique) / len(unique),  # latitude
        sum(point[0] for point in unique) / len(unique),  # longitude
    )


def main() -> None:
    config = dotenv_values(ROOT / ".env")
    token = config.get("PARKING_TOKEN") or os.getenv("PARKING_TOKEN")
    if not token:
        raise SystemExit("PARKING_TOKEN is not configured")

    places = ParkingClient(token).get_all_places()
    exported_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    records: list[dict[str, Any]] = []
    features: list[dict[str, Any]] = []

    for place in places:
        if not place.uniqueNumber or not place.address or not place.polygon:
            raise ValueError(f"Place {place.id} is missing required data")
        ring = polygon_coordinates(place.polygon)
        lat, lon = centroid(ring)
        record = {
            "municipal_place_id": place.id,
            "place_no": place.uniqueNumber,
            "name_ge": f"ზონალური პარკინგი {place.uniqueNumber}",
            "name_en": f"Tbilisi zonal parking {place.uniqueNumber}",
            "type": "zonal",
            "fee": "Municipal zonal tariff",
            "hours": "See municipal parking rules",
            "street": place.address,
            "city": "Tbilisi",
            "lat": round(lat, 8),
            "lon": round(lon, 8),
            "source": "tbilisi_municipal",
            "source_url": "https://parking.tbilisi.gov.ge",
            "exported_at_utc": exported_at,
        }
        records.append(record)
        features.append({
            "type": "Feature",
            "id": f"tbilisi-municipal-{place.id}",
            "geometry": {"type": "Polygon", "coordinates": [ring]},
            "properties": record,
        })

    OUTPUT.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    stem = OUTPUT / f"tbilisi-municipal-zonal-parking-{stamp}"
    csv_path = stem.with_suffix(".csv")
    geojson_path = stem.with_suffix(".geojson")
    crm_path = stem.with_name(f"{stem.name}-crm.json")

    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)

    geojson_path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "name": "Tbilisi municipal zonal parking",
                "source": "https://parking.tbilisi.gov.ge",
                "exported_at_utc": exported_at,
                "features": features,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    crm_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"exported={len(records)}")
    for path in (csv_path, geojson_path, crm_path):
        print(f"{path.name}\t{path.stat().st_size}\t{path}")


if __name__ == "__main__":
    main()
