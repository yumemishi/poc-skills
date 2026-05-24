#!/usr/bin/env python3
"""USGS earthquake watchdog helper for Fulcra earthquake annotations.

This script is intentionally dependency-free. It handles the deterministic pieces
that are easy to get wrong in an LLM loop: USGS querying, radius filtering,
distance math, canonical note rendering, and duplicate suppression.

It does not write to Fulcra directly; consumers should pipe/use the JSONL records
with their local Fulcra annotation writer. In --mode discord, stdout stays empty
unless a new event meets the notification threshold, making it suitable for
script-only cron watchdogs.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

USGS_QUERY_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
EARTH_RADIUS_MI = 3958.7613


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Poll USGS earthquakes and render Fulcra-ready records/Discord alerts.")
    p.add_argument("--center-lat", type=float, required=True, help="Monitor center latitude; used internally only.")
    p.add_argument("--center-lon", type=float, required=True, help="Monitor center longitude; used internally only.")
    p.add_argument("--radius-mi", type=float, required=True, help="Monitor radius in miles.")
    p.add_argument("--monitor-label", required=True, help="User-facing label, e.g. Honalo or Hawaiʻi Island.")
    p.add_argument("--annotation-name", default="Nearby Earthquakes", help="Fulcra annotation name for JSONL output.")
    p.add_argument("--tags", default="earthquake,agent-recorded", help="Comma-separated tags for JSONL output.")
    p.add_argument("--record-min", type=float, default=4.0, help="Minimum magnitude to record to Fulcra.")
    p.add_argument("--notify-min", type=float, default=5.0, help="Minimum magnitude to print Discord alerts.")
    p.add_argument("--since-hours", type=float, default=2.0, help="USGS lookback window. Use > poll interval.")
    p.add_argument("--timezone", default="UTC", help="IANA timezone for note timestamps, e.g. Pacific/Honolulu.")
    p.add_argument("--state-file", default="~/.hermes/state/fulcra-earthquake-annotation/seen-usgs-events.json")
    p.add_argument("--mode", choices=["discord", "jsonl", "both"], default="discord",
                   help="discord: only alert text for notify-min events; jsonl: Fulcra-ready records; both: both sections.")
    p.add_argument("--backfill", action="store_true", help="Process existing events on first run instead of silent seeding.")
    p.add_argument("--dry-run", action="store_true", help="Do not update the seen-ID state file.")
    return p.parse_args()


@dataclass(frozen=True)
class Event:
    event_id: str
    url: str
    time_ms: int
    mag: float
    place: str
    lat: float
    lon: float
    mmi: float | None
    cdi: float | None
    tsunami: int | None
    distance_mi: float


def haversine_mi(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_MI * math.asin(math.sqrt(a))


def fetch_usgs(args: argparse.Namespace) -> dict[str, Any]:
    start = datetime.now(timezone.utc) - timedelta(hours=args.since_hours)
    params = {
        "format": "geojson",
        "starttime": start.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "minmagnitude": min(args.record_min, args.notify_min),
        "latitude": args.center_lat,
        "longitude": args.center_lon,
        "maxradiuskm": args.radius_mi * 1.609344,
        "orderby": "time-asc",
    }
    url = f"{USGS_QUERY_URL}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def iter_events(payload: dict[str, Any], args: argparse.Namespace) -> Iterable[Event]:
    for f in payload.get("features", []):
        props = f.get("properties") or {}
        geom = f.get("geometry") or {}
        coords = geom.get("coordinates") or []
        if len(coords) < 2 or props.get("mag") is None or props.get("time") is None:
            continue
        lon, lat = float(coords[0]), float(coords[1])
        distance = haversine_mi(args.center_lat, args.center_lon, lat, lon)
        if distance > args.radius_mi:
            continue
        yield Event(
            event_id=str(f.get("id") or props.get("code") or props.get("url")),
            url=str(props.get("url") or ""),
            time_ms=int(props["time"]),
            mag=float(props["mag"]),
            place=str(props.get("place") or "unknown location"),
            lat=lat,
            lon=lon,
            mmi=float(props["mmi"]) if props.get("mmi") is not None else None,
            cdi=float(props["cdi"]) if props.get("cdi") is not None else None,
            tsunami=int(props["tsunami"]) if props.get("tsunami") is not None else None,
            distance_mi=distance,
        )


def load_seen(path: Path) -> tuple[set[str], bool]:
    if not path.exists():
        return set(), True
    try:
        data = json.loads(path.read_text())
        return set(data.get("seen_ids", [])), False
    except Exception:
        return set(), False


def save_seen(path: Path, seen: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps({"seen_ids": sorted(seen)}, indent=2) + "\n")
    tmp.replace(path)


def local_time(ms: int, tz_name: str) -> str:
    tz = ZoneInfo(tz_name)
    dt = datetime.fromtimestamp(ms / 1000, timezone.utc).astimezone(tz)
    # Example: Friday, May 22, 9:46 PM HST. %-I is POSIX; fallback keeps leading zero if unsupported.
    try:
        return dt.strftime("%A, %B %-d, %-I:%M %p %Z")
    except ValueError:
        return dt.strftime("%A, %B %d, %I:%M %p %Z")


def intensity(e: Event) -> float | None:
    vals = [v for v in (e.mmi, e.cdi) if v is not None]
    return max(vals) if vals else None


def tsunami_text(e: Event) -> str:
    if e.tsunami is None:
        return "unknown"
    return "yes" if e.tsunami else "no"


def magnitude_text(mag: float) -> str:
    return f"{mag:.2f}".rstrip("0").rstrip(".")


def place_text(place: str) -> str:
    """Convert common USGS place strings to the user-facing miles style.

    USGS often returns strings like "13 km S of Honaunau-Napoopoo, Hawaii".
    The skill's note rules require miles and no raw coordinates, so normalize the
    distance unit while preserving the direction and town/place label.
    """
    parts = place.split(" ", 3)
    if len(parts) == 4:
        amount, unit, direction, rest = parts
        try:
            n = float(amount)
        except ValueError:
            return place
        if unit.lower() == "km":
            return f"{n * 0.621371:.1f} mi {direction} {rest}"
        if unit.lower() in {"mi", "mile", "miles"}:
            return f"{n:.1f} mi {direction} {rest}"
    return place


def note_for(e: Event, args: argparse.Namespace) -> str:
    mag = magnitude_text(e.mag)
    inten = intensity(e)
    magnitude_line = f"Magnitude: {mag}" + (f", {inten:.1f} max intensity" if inten is not None else "")
    return "\n".join([
        f"Time: {local_time(e.time_ms, args.timezone)}",
        magnitude_line,
        f"Epicenter: {place_text(e.place)}",
        f"My distance from epicenter: ~{e.distance_mi:.1f} mi, {args.monitor_label}",
        f"Tsunami watch: {tsunami_text(e)}",
        "",
        f"USGS page: {e.url}",
    ])


def record_json(e: Event, args: argparse.Namespace) -> dict[str, Any]:
    event_dt = datetime.fromtimestamp(e.time_ms / 1000, timezone.utc).isoformat().replace("+00:00", "Z")
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    return {
        "usgs_id": e.event_id,
        "annotation_name": args.annotation_name,
        "value": e.mag,
        "recorded_at": event_dt,
        "tags": tags,
        "note": note_for(e, args),
        "duplicate_guard": e.url or e.event_id,
    }


def discord_alert(e: Event, args: argparse.Namespace) -> str:
    user_place = place_text(e.place)
    return "\n".join([
        f"🌎 Magnitude {magnitude_text(e.mag)} earthquake near {user_place}",
        f"Time: {local_time(e.time_ms, args.timezone)}",
        f"Epicenter: {user_place}",
        f"My distance from epicenter: ~{e.distance_mi:.1f} mi, {args.monitor_label}",
        f"Tsunami watch: {tsunami_text(e)}",
        f"USGS: {e.url}",
    ])


def main() -> int:
    args = parse_args()
    state_path = Path(os.path.expanduser(args.state_file))
    seen, first_run = load_seen(state_path)
    payload = fetch_usgs(args)
    events = list(iter_events(payload, args))
    new_events = [e for e in events if e.event_id not in seen]

    if first_run and not args.backfill:
        seen.update(e.event_id for e in events)
        if not args.dry_run:
            save_seen(state_path, seen)
        return 0

    outputs: list[str] = []
    for e in new_events:
        if e.mag >= args.record_min and args.mode in {"jsonl", "both"}:
            outputs.append(json.dumps(record_json(e, args), ensure_ascii=False))
        if e.mag >= args.notify_min and args.mode in {"discord", "both"}:
            outputs.append(discord_alert(e, args))
        seen.add(e.event_id)

    if not args.dry_run:
        save_seen(state_path, seen)
    if outputs:
        print("\n\n".join(outputs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
