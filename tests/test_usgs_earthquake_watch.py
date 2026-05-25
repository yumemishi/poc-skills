from __future__ import annotations

import json
import sys
import tempfile
import unittest
from argparse import Namespace
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fulcra_earthquake_annotation import watch


FIXTURES = ROOT / "tests" / "fixtures"


def args(**overrides):
    base = {
        "center_lat": 19.64,
        "center_lon": -155.99,
        "radius_mi": 250.0,
        "monitor_label": "Hawaii Island",
        "annotation_name": "BI Earthquakes",
        "tags": ["earthquake", "bi", "hawaii", "agent-recorded", "yumemishi"],
        "record_min": 4.0,
        "notify_min": 5.0,
        "since_hours": 2.0,
        "timezone": "Pacific/Honolulu",
        "state_file": "/tmp/seen.json",
        "state_retention_days": 90,
        "outputs": ["fulcra_record", "discord_alert"],
        "backfill": True,
        "dry_run": True,
        "config": None,
        "from_file": None,
    }
    base.update(overrides)
    return Namespace(**base)


def event(**overrides):
    base = {
        "event_id": "hv74966427",
        "url": "https://earthquake.usgs.gov/earthquakes/eventpage/hv74966427",
        "time_ms": 1779522360000,
        "mag": 5.96,
        "place": "13 km S of Honaunau-Napoopoo, Hawaii",
        "lat": 19.382,
        "lon": -155.99,
        "mmi": 7.2,
        "cdi": None,
        "tsunami": 0,
        "distance_mi": 17.8,
    }
    base.update(overrides)
    return watch.Event(**base)


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


class EarthquakeWatchTests(unittest.TestCase):
    def test_place_text_converts_km_to_miles(self):
        self.assertEqual(
            watch.place_text("13 km S of Honaunau-Napoopoo, Hawaii"),
            "8.1 mi S of Honaunau-Napoopoo, Hawaii",
        )

    def test_note_for_preserves_canonical_shape(self):
        note = watch.note_for(event(), args())

        self.assertIn("Time: Friday, May 22, 9:46 PM HST", note)
        self.assertIn("Magnitude: 5.96, 7.2 max intensity", note)
        self.assertIn("Epicenter: 8.1 mi S of Honaunau-Napoopoo, Hawaii", note)
        self.assertIn("My distance from epicenter: ~17.8 mi, Hawaii Island", note)
        self.assertIn("Tsunami watch: no", note)
        self.assertIn("USGS page: https://earthquake.usgs.gov/earthquakes/eventpage/hv74966427", note)

    def test_render_outputs_emits_selected_envelopes(self):
        outputs = watch.render_outputs([event()], args(outputs=["discord_alert"]))

        self.assertEqual(len(outputs), 1)
        record = json.loads(outputs[0])
        self.assertEqual(record["type"], "discord_alert")
        self.assertIn("Magnitude 5.96 earthquake", record["text"])

    def test_parse_args_loads_config_and_allows_cli_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.json"
            config.write_text(json.dumps({
                "center_lat": 19.64,
                "center_lon": -155.99,
                "radius_mi": 250,
                "monitor_label": "Hawaii Island",
                "record_min": 4.0,
                "timezone": "Pacific/Honolulu",
                "state_retention_days": 90,
                "tags": ["earthquake", "hawaii"],
                "outputs": ["fulcra_record", "discord_alert"],
            }))

            parsed = watch.parse_args([
                "--config", str(config),
                "--record-min", "4.5",
                "--outputs", "discord_alert",
            ])

        self.assertEqual(parsed.center_lat, 19.64)
        self.assertEqual(parsed.radius_mi, 250)
        self.assertEqual(parsed.record_min, 4.5)
        self.assertEqual(parsed.tags, ["earthquake", "hawaii"])
        self.assertEqual(parsed.outputs, ["discord_alert"])

    def test_outputs_are_deduplicated_preserving_order(self):
        parsed = watch.parse_args([
            "--center-lat", "19.64",
            "--center-lon", "-155.99",
            "--radius-mi", "250",
            "--monitor-label", "Hawaii Island",
            "--outputs", "discord_alert,fulcra_record,discord_alert",
        ])

        self.assertEqual(parsed.outputs, ["discord_alert", "fulcra_record"])

    def test_seen_state_round_trips(self):
        now = datetime(2026, 5, 24, 12, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state" / "seen.json"
            seen, first_run = watch.load_seen(path, now)
            self.assertEqual(seen, {})
            self.assertTrue(first_run)

            watch.save_seen(path, {"b": now, "a": now - timedelta(days=1)})
            seen, first_run = watch.load_seen(path, now)

        self.assertEqual(set(seen), {"a", "b"})
        self.assertEqual(seen["b"], now)
        self.assertFalse(first_run)

    def test_legacy_seen_ids_load_with_current_timestamp(self):
        now = datetime(2026, 5, 24, 12, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "seen.json"
            path.write_text(json.dumps({"seen_ids": ["a", "b"]}))

            seen, first_run = watch.load_seen(path, now)

        self.assertEqual(seen, {"a": now, "b": now})
        self.assertFalse(first_run)

    def test_seen_state_prunes_old_entries(self):
        now = datetime(2026, 5, 24, 12, 0, tzinfo=timezone.utc)
        seen = {
            "old": now - timedelta(days=91),
            "new": now - timedelta(days=1),
        }

        self.assertEqual(set(watch.prune_seen(seen, now, 90)), {"new"})

    def test_iter_events_filters_outside_radius(self):
        payload = {
            "features": [
                {
                    "id": "near",
                    "properties": {
                        "url": "https://example.test/near",
                        "time": 1779522360000,
                        "mag": 4.2,
                        "place": "1 km S of Test",
                    },
                    "geometry": {"coordinates": [-155.99, 19.65, 0]},
                },
                {
                    "id": "far",
                    "properties": {
                        "url": "https://example.test/far",
                        "time": 1779522360000,
                        "mag": 4.2,
                        "place": "500 km S of Test",
                    },
                    "geometry": {"coordinates": [-120.0, 35.0, 0]},
                },
            ]
        }

        events = list(watch.iter_events(payload, args(radius_mi=50)))

        self.assertEqual([e.event_id for e in events], ["near"])

    def test_fixture_payload_matches_golden_envelopes(self):
        with tempfile.TemporaryDirectory() as tmp:
            parsed = watch.parse_args([
                "--config", str(ROOT / "fulcra-earthquake-annotation" / "examples" / "hawaii-island.config.json"),
                "--from-file", str(FIXTURES / "usgs_sample.geojson"),
                "--state-file", str(Path(tmp) / "seen.json"),
                "--dry-run",
                "--backfill",
            ])
            actual = [json.loads(line) for line in watch.run(parsed)]

        expected = read_jsonl(FIXTURES / "expected_envelopes.jsonl")
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
