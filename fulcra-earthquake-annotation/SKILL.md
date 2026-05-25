---
name: fulcra-earthquake-annotation
description: Use when setting up or running a Fulcra earthquake annotation workflow from USGS, including location-aware monitor setup, numeric magnitude records, the approved note format, duplicate suppression, and optional Discord notifications.
version: 1.0.0
author: Yumemishi/Hermemishi/DianaKusunoki
license: MIT
---

# Fulcra Earthquake Annotation

## Overview

Use this skill to set up or run a USGS earthquake monitor that produces Fulcra-ready numeric annotation records and optional Discord notifications.

The primary Fulcra value is the earthquake magnitude. The note contains local event time, magnitude/intensity, epicenter, distance from the monitor area, tsunami watch status, and the USGS event page.

## When to Use

Use this skill when the user wants to:

- Create or configure a Fulcra earthquake annotation.
- Monitor USGS earthquakes around their Fulcra location or another place.
- Record earthquakes into Fulcra as numeric magnitude values.
- Use defaults of recording M4.0+ and notifying on M5.0+.
- Preview the exact note that will be attached to each recorded annotation.
- Build or maintain a recurring earthquake polling/notification watchdog.

Do not use this skill for generic disaster alerts, weather alerts, or non-Fulcra logging unless the user explicitly asks to adapt the pattern.

## Bundled Resources

- `scripts/usgs_earthquake_watch.py` - deterministic USGS query, radius filtering, duplicate suppression, note rendering, and JSONL output.
- `examples/hawaii-island.config.json` - editable monitor config example.
- `examples/config.schema.json` - config contract for schedulers or setup tooling.
- `references/setup-flow.md` - setup prompts and confirmation flow. Read this when creating or changing a monitor.
- `references/output-contract.md` - Fulcra record, envelope JSONL, and notification delivery contract. Read this when wiring the helper to Fulcra or Discord.

## Workflow

1. Get user consent to use their Fulcra location or ask for a monitor place/radius.
2. Follow `references/setup-flow.md` for area, annotation name, polling frequency, thresholds, and notification destination.
3. Create or update a JSON config matching `examples/config.schema.json`.
4. Use `scripts/usgs_earthquake_watch.py --config <config>` for scheduled runs.
5. Pipe `fulcra_record` envelopes to the local Fulcra annotation writer and `discord_alert` envelopes to the selected delivery target.
6. Do not create the annotation definition, scheduler, or Discord delivery until the user confirms the final setup summary.

## Core Record Rules

Create a **numeric** Fulcra annotation definition.

| Field | Rule |
| --- | --- |
| Annotation name | User-approved label, e.g. `BI Earthquakes`, `Big Island Earthquakes`, `Southern California Earthquakes`, or `Nearby Earthquakes` |
| Numeric value | Earthquake magnitude, e.g. `5.96` |
| Recorded time | The USGS event time, not the time the agent writes the record |
| Tags | Short lowercase tags such as `earthquake`, region tags, `agent-recorded`, and optionally `yumemishi` |
| Duplicate guard | Stable USGS event ID / event page URL |
| Note | The canonical plain-text note format below |

Preserve this note shape. Do not replace it with a title/body article, a generic summary, or `Fulcra fields:` metadata.

```text
Time: Friday, May 22, 9:46 PM HST
Magnitude: 5.96, 7.2 max intensity
Epicenter: 8.1 mi S of Honaunau-Napoopoo, Hawaii
My distance from epicenter: ~17.8 mi, Honalo
Tsunami watch: no

USGS page: https://earthquake.usgs.gov/earthquakes/eventpage/hv74966427
```

## Note Rules

- Use miles.
- Use local time for the user or selected monitoring area.
- Use nearest town/place and distance/direction.
- Include maximum intensity when the source provides it; omit that phrase when unavailable.
- Use `Tsunami watch: no`, `yes`, or `unknown` based on source confidence.
- Include the USGS event page URL.
- Keep the note plain text because Fulcra mobile renders notes as plain text.

## USGS Event Data Requirements

Use USGS as the default source. Required data for each candidate event:

- Stable `id` and event page URL.
- Event timestamp.
- Magnitude.
- Place string or nearest-town description.
- Maximum intensity when available, such as `mmi` or `cdi`.
- Tsunami/watch status when available; otherwise `unknown`.

## Privacy and Location Handling

- Use Fulcra location only with user consent.
- Use coordinates internally only for distance/radius calculations and geocoding.
- Do not expose raw user coordinates in annotation notes, setup previews, or Discord alerts.
- Use derived values instead: miles, direction, nearest town/place, monitor-area label, and broad region labels.
- If location samples are stale or uncertain, say so and use the selected monitor center rather than pretending it is the user's exact current location.

## Common Pitfalls

1. **Drifting into generic note text.** The record uses a numeric value plus the exact note fields above.
2. **Asking too many monitor-area choices.** Keep it to nearby, wider region, different place, or write-in.
3. **Recording at write time.** External events must use the USGS event timestamp.
4. **Claiming writes from HTTP status only.** Verify readback.
5. **Assuming buttons are available.** Buttons are optional; text must always work.

## Verification Checklist

Before reporting the setup as complete:

- [ ] User confirmed the final setup summary.
- [ ] Annotation definition exists or was created as numeric.
- [ ] Tags are short, lowercase, and stable.
- [ ] Populated preview matches the canonical Fulcra record shape.
- [ ] Fulcra threshold and Discord threshold are separate.
- [ ] Event timestamps come from USGS.
- [ ] Privacy and location handling rules are satisfied.
- [ ] Duplicate suppression uses stable USGS IDs.
- [ ] Initial cron run behavior is silent seed or user-approved backfill.
- [ ] Fulcra writes are verified by readback.
- [ ] Discord destination is explicit when notifications are enabled.
