#!/usr/bin/env python3
"""Classify official zonal parking places by their live municipal tariff.

The municipal catalog has coordinates/addresses, while the detail endpoint
(`/parking/place/{id}`) provides `freeParking` and hourly `parkingPrices`.
This exporter joins those two official responses and writes separate files for
free and hourly places. It deliberately does *not* invent a "subscription-only"
category: the official response has no such per-place field.
"""
from __future__ import annotations

import asyncio
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "exports"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.client import API_BASE, ParkingClient
from scripts.export_zonal_parking import centroid, polygon_coordinates

CONCURRENCY = 8
RETRIES = 3


async def fetch_detail(
    client: httpx.AsyncClient,
    place: dict[str, Any],
    semaphore: asyncio.Semaphore,
) -> dict[str, Any]:
    async with semaphore:
        for attempt in range(RETRIES):
            try:
                response = await client.get(f"{API_BASE}/parking/place/{place['id']}")
                response.raise_for_status()
                detail = response.json()["result"]["data"]
                return {**place, "detail": detail}
            except (httpx.HTTPError, KeyError, TypeError) as exc:
                if attempt == RETRIES - 1:
                    raise RuntimeError(f"Place {place['id']}: {exc}") from exc
                await asyncio.sleep(1 + attempt)
    raise AssertionError("unreachable")


def make_record(item: dict[str, Any], exported_at: str) -> dict[str, Any]:
    detail = item["detail"]
    ring = polygon_coordinates(item["polygon"])
    lat, lon = centroid(ring)
    prices = detail.get("parkingPrices") or []
    is_free = bool(detail.get("freeParking")) or not any(float(p.get("price", 0)) > 0 for p in prices)
    hourly_prices = sorted({float(p["price"]) for p in prices if float(p.get("price", 0)) > 0})
    return {
        "municipal_place_id": item["id"],
        "place_no": item["uniqueNumber"],
        "address": detail.get("address") or item["address"],
        "tariff_category": "free" if is_free else "hourly",
        "free_parking": is_free,
        "hourly_tariff_gel": ",".join(f"{price:g}" for price in hourly_prices),
        "parking_price_periods": json.dumps(prices, ensure_ascii=False, separators=(",", ":")),
        "lat": round(lat, 8),
        "lon": round(lon, 8),
        "source": "tbilisi_municipal",
        "source_url": "https://parking.tbilisi.gov.ge",
        "exported_at_utc": exported_at,
    }


async def main() -> None:
    token = dotenv_values(ROOT / ".env").get("PARKING_TOKEN") or os.getenv("PARKING_TOKEN")
    if not token:
        raise SystemExit("PARKING_TOKEN is not configured")

    places = [place.model_dump() for place in ParkingClient(token).get_all_places()]
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    semaphore = asyncio.Semaphore(CONCURRENCY)
    timeout = httpx.Timeout(30.0, connect=10.0)
    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        details = await asyncio.gather(*(fetch_detail(client, place, semaphore) for place in places))

    exported_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    records = [make_record(item, exported_at) for item in details]
    free = [record for record in records if record["tariff_category"] == "free"]
    hourly = [record for record in records if record["tariff_category"] == "hourly"]

    OUTPUT.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    fields = list(records[0])
    for label, collection in (("free", free), ("hourly", hourly), ("all-classified", records)):
        path = OUTPUT / f"tbilisi-municipal-zonal-{label}-{stamp}.csv"
        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            writer.writerows(collection)
        print(f"{label}={len(collection)}\t{path}")

    # The category is a per-place price classification. Zone subscriptions are
    # a separate product (`forZoneParking=1`) and the municipal API exposes no
    # per-place subscription-only flag.
    print(f"total={len(records)}")


if __name__ == "__main__":
    asyncio.run(main())
