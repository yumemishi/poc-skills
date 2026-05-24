# Output Contract

Use this when wiring `scripts/usgs_earthquake_watch.py` into a Fulcra writer, scheduler, or notification target.

## Recommended Command

```bash
python3 fulcra-earthquake-annotation/scripts/usgs_earthquake_watch.py \
  --config fulcra-earthquake-annotation/examples/hawaii-island.config.json
```

## Fulcra Record Envelope

Stdout is always typed JSONL. Select envelope types with the config `outputs` array or the CLI `--outputs fulcra_record,discord_alert`.

```json
{
  "type": "fulcra_record",
  "usgs_id": "hv74966427",
  "usgs_url": "https://earthquake.usgs.gov/earthquakes/eventpage/hv74966427",
  "annotation_name": "BI Earthquakes",
  "value": 5.96,
  "recorded_at": "2026-05-23T07:46:00Z",
  "tags": ["earthquake", "bi", "hawaii", "agent-recorded", "yumemishi"],
  "note": "Time: Friday, May 22, 9:46 PM HST\nMagnitude: 5.96, 7.2 max intensity\nEpicenter: 8.1 mi S of Honaunau-Napoopoo, Hawaii\nMy distance from epicenter: ~17.8 mi, Honalo\nTsunami watch: no\n\nUSGS page: https://earthquake.usgs.gov/earthquakes/eventpage/hv74966427",
  "duplicate_guard": "https://earthquake.usgs.gov/earthquakes/eventpage/hv74966427"
}
```

The Fulcra writer should create a numeric annotation record using:

- `annotation_name` as the annotation/data type.
- `value` as the numeric value.
- `recorded_at` as the event timestamp.
- `tags` as record tags.
- `note` as the plain-text note.
- `duplicate_guard` or `usgs_id` for idempotency.

## Discord Alert Envelope

```json
{
  "type": "discord_alert",
  "usgs_id": "hv74966427",
  "usgs_url": "https://earthquake.usgs.gov/earthquakes/eventpage/hv74966427",
  "text": "Magnitude 5.96 earthquake near 8.1 mi S of Honaunau-Napoopoo, Hawaii\nTime: Friday, May 22, 9:46 PM HST\nEpicenter: 8.1 mi S of Honaunau-Napoopoo, Hawaii\nMy distance from epicenter: ~17.8 mi, Honalo\nTsunami watch: no\nUSGS: https://earthquake.usgs.gov/earthquakes/eventpage/hv74966427"
}
```

Send only `text` to the selected Discord destination. Do not invent or guess channel IDs; resolve them through the available Discord/messaging tools.

## State And Duplicate Suppression

The script stores seen USGS event IDs and first-seen timestamps in `state_file`. On first run, it silently seeds the state file unless `--backfill` is set. Entries older than `state_retention_days` are pruned during normal runs. Use a lookback window larger than the polling interval so late scheduler runs do not miss events.

## Fixture Runs

Use `--from-file` or `--fixture` to validate scheduler wiring without calling USGS:

```bash
python3 fulcra-earthquake-annotation/scripts/usgs_earthquake_watch.py \
  --config fulcra-earthquake-annotation/examples/hawaii-island.config.json \
  --from-file tests/fixtures/usgs_sample.geojson \
  --dry-run \
  --backfill
```
