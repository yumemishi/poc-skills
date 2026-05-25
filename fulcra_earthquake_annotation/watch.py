from __future__ import annotations

import argparse
import json
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

USGS_QUERY_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
EARTH_RADIUS_MI = 3958.7613
EXIT_RUNTIME_ERROR = 3
OUTPUT_TYPES = {"fulcra_record", "discord_alert"}
DEFAULT_OUTPUTS = ["fulcra_record", "discord_alert"]
DEFAULT_STATE_RETENTION_DAYS = 90


class WatchdogError(Exception):
    """Expected runtime failure that should be readable in scheduler logs."""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Poll USGS earthquakes and emit typed Fulcra/Discord JSONL envelopes.")
    p.add_argument("--config", help="Optional JSON config file. CLI arguments override config values.")
    p.add_argument("--from-file", "--fixture", dest="from_file",
                   help="Read a USGS GeoJSON payload from a file instead of calling USGS.")
    p.add_argument("--center-lat", type=float, help="Monitor center latitude; used internally only.")
    p.add_argument("--center-lon", type=float, help="Monitor center longitude; used internally only.")
    p.add_argument("--radius-mi", type=float, help="Monitor radius in miles.")
    p.add_argument("--monitor-label", help="User-facing label, e.g. Honalo or Hawaii Island.")
    p.add_argument("--annotation-name", default="Nearby Earthquakes", help="Fulcra annotation name for JSONL output.")
    p.add_argument("--tags", default="earthquake,agent-recorded",
                   help="Comma-separated tags. JSON config may provide an array of strings.")
    p.add_argument("--record-min", type=float, default=4.0, help="Minimum magnitude to emit a fulcra_record envelope.")
    p.add_argument("--notify-min", type=float, default=5.0, help="Minimum magnitude to emit a discord_alert envelope.")
    p.add_argument("--since-hours", type=float, default=2.0, help="USGS lookback window. Use > poll interval.")
    p.add_argument("--timezone", default="UTC", help="IANA timezone for note timestamps, e.g. Pacific/Honolulu.")
    p.add_argument("--state-file", default="~/.hermes/state/fulcra-earthquake-annotation/seen-usgs-events.json")
    p.add_argument("--state-retention-days", type=float, default=DEFAULT_STATE_RETENTION_DAYS,
                   help="Days to keep seen USGS event IDs before pruning them from state.")
    p.add_argument("--outputs", default=",".join(DEFAULT_OUTPUTS),
                   help="Comma-separated envelope types: fulcra_record,discord_alert. JSON config may provide an array.")
    p.add_argument("--backfill", action="store_true", help="Process existing events on first run instead of silent seeding.")
    p.add_argument("--dry-run", action="store_true", help="Do not update the seen-ID state file.")
    return p


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)
    cli_values = {
        action.dest
        for action in parser._actions
        if action.dest != "help" and getattr(args, action.dest, None) != action.default
    }
    if args.config:
        args = apply_config(args, cli_values)
    validate_args(args, parser)
    return args


def apply_config(args: argparse.Namespace, cli_values: set[str]) -> argparse.Namespace:
    path = Path(os.path.expanduser(args.config))
    try:
        data = json.loads(path.read_text())
    except OSError as exc:
        raise WatchdogError(f"could not read config file {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise WatchdogError(f"could not parse config file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise WatchdogError(f"config file {path} must contain a JSON object")

    valid_keys = set(vars(args))
    for key, value in data.items():
        dest = key.replace("-", "_")
        if dest not in valid_keys:
            raise WatchdogError(f"unknown config key: {key}")
        if dest not in cli_values and dest != "config":
            setattr(args, dest, value)
    return args


def validate_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    missing = [name for name in ("center_lat", "center_lon", "radius_mi", "monitor_label") if getattr(args, name) is None]
    if missing:
        parser.error("missing required monitor setting(s): " + ", ".join("--" + name.replace("_", "-") for name in missing))
    if args.radius_mi <= 0:
        parser.error("--radius-mi must be greater than 0")
    if args.record_min < 0 or args.notify_min < 0:
        parser.error("--record-min and --notify-min must be non-negative")
    if args.since_hours <= 0:
        parser.error("--since-hours must be greater than 0")
    if args.state_retention_days <= 0:
        parser.error("--state-retention-days must be greater than 0")
    try:
        ZoneInfo(args.timezone)
    except Exception as exc:
        raise WatchdogError(f"unknown timezone {args.timezone!r}") from exc
    args.tags = normalize_tags(args.tags)
    args.outputs = normalize_outputs(args.outputs)


def normalize_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [t.strip() for t in value.split(",") if t.strip()]
    if isinstance(value, list) and all(isinstance(t, str) for t in value):
        return [t.strip() for t in value if t.strip()]
    raise WatchdogError("tags must be a comma-separated string or an array of strings")


def normalize_outputs(value: Any) -> list[str]:
    if value is None:
        outputs = DEFAULT_OUTPUTS.copy()
    elif isinstance(value, str):
        outputs = [o.strip() for o in value.split(",") if o.strip()]
    elif isinstance(value, list) and all(isinstance(o, str) for o in value):
        outputs = [o.strip() for o in value if o.strip()]
    else:
        raise WatchdogError("outputs must be a comma-separated string or an array of strings")
    if not outputs:
        raise WatchdogError("outputs must include at least one envelope type")
    unknown = sorted(set(outputs) - OUTPUT_TYPES)
    if unknown:
        raise WatchdogError(f"unknown output type(s): {', '.join(unknown)}")
    return list(dict.fromkeys(outputs))


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


def load_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.from_file:
        return load_usgs_file(Path(os.path.expanduser(args.from_file)))
    return fetch_usgs(args)


def load_usgs_file(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except OSError as exc:
        raise WatchdogError(f"could not read USGS fixture {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise WatchdogError(f"USGS fixture was not valid JSON: {path}: {exc}") from exc


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
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise WatchdogError(f"USGS request failed: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise WatchdogError(f"USGS response was not valid JSON: {exc}") from exc


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


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_iso_z(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError as exc:
        raise WatchdogError(f"state file contains invalid timestamp {value!r}") from exc


def load_seen(path: Path, now: datetime | None = None) -> tuple[dict[str, datetime], bool]:
    now = now or utc_now()
    if not path.exists():
        return {}, True
    try:
        data = json.loads(path.read_text())
        if isinstance(data.get("seen"), dict):
            return {str(event_id): parse_iso_z(str(seen_at)) for event_id, seen_at in data["seen"].items()}, False
        if isinstance(data.get("seen_ids"), list):
            return {str(event_id): now for event_id in data["seen_ids"]}, False
        return {}, False
    except json.JSONDecodeError as exc:
        raise WatchdogError(f"state file is not valid JSON: {path}: {exc}") from exc
    except OSError as exc:
        raise WatchdogError(f"could not read state file {path}: {exc}") from exc


def prune_seen(seen: dict[str, datetime], now: datetime, retention_days: float) -> dict[str, datetime]:
    cutoff = now - timedelta(days=retention_days)
    return {event_id: seen_at for event_id, seen_at in seen.items() if seen_at >= cutoff}


def save_seen(path: Path, seen: dict[str, datetime]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        payload = {"seen": {event_id: iso_z(seen[event_id]) for event_id in sorted(seen)}}
        tmp.write_text(json.dumps(payload, indent=2) + "\n")
        tmp.replace(path)
    except OSError as exc:
        raise WatchdogError(f"could not write state file {path}: {exc}") from exc


def local_time(ms: int, tz_name: str) -> str:
    tz = ZoneInfo(tz_name)
    dt = datetime.fromtimestamp(ms / 1000, timezone.utc).astimezone(tz)
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
    """Convert common USGS place strings to the user-facing miles style."""
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
    return {
        "usgs_id": e.event_id,
        "annotation_name": args.annotation_name,
        "value": e.mag,
        "recorded_at": event_dt,
        "tags": list(args.tags),
        "note": note_for(e, args),
        "duplicate_guard": e.url or e.event_id,
    }


def discord_alert(e: Event, args: argparse.Namespace) -> str:
    user_place = place_text(e.place)
    return "\n".join([
        f"Magnitude {magnitude_text(e.mag)} earthquake near {user_place}",
        f"Time: {local_time(e.time_ms, args.timezone)}",
        f"Epicenter: {user_place}",
        f"My distance from epicenter: ~{e.distance_mi:.1f} mi, {args.monitor_label}",
        f"Tsunami watch: {tsunami_text(e)}",
        f"USGS: {e.url}",
    ])


def envelope(kind: str, payload: dict[str, Any] | str, e: Event) -> str:
    data: dict[str, Any] = {
        "type": kind,
        "usgs_id": e.event_id,
        "usgs_url": e.url,
    }
    if isinstance(payload, dict):
        data.update(payload)
    else:
        data["text"] = payload
    return json.dumps(data, ensure_ascii=False)


def render_outputs(new_events: list[Event], args: argparse.Namespace) -> list[str]:
    outputs: list[str] = []
    for e in new_events:
        if "fulcra_record" in args.outputs and e.mag >= args.record_min:
            outputs.append(envelope("fulcra_record", record_json(e, args), e))
        if "discord_alert" in args.outputs and e.mag >= args.notify_min:
            outputs.append(envelope("discord_alert", discord_alert(e, args), e))
    return outputs


def run(args: argparse.Namespace) -> list[str]:
    now = utc_now()
    state_path = Path(os.path.expanduser(args.state_file))
    seen, first_run = load_seen(state_path, now)
    seen = prune_seen(seen, now, args.state_retention_days)
    payload = load_payload(args)
    events = list(iter_events(payload, args))
    new_events = [e for e in events if e.event_id not in seen]

    if first_run and not args.backfill:
        for e in events:
            seen[e.event_id] = now
        if not args.dry_run:
            save_seen(state_path, seen)
        return []

    outputs = render_outputs(new_events, args)
    for e in new_events:
        seen[e.event_id] = now

    if not args.dry_run:
        save_seen(state_path, seen)
    return outputs


def main(argv: list[str] | None = None) -> int:
    try:
        outputs = run(parse_args(argv))
        if outputs:
            print("\n".join(outputs))
        return 0
    except WatchdogError as exc:
        print(f"fulcra-earthquake-annotation: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR
