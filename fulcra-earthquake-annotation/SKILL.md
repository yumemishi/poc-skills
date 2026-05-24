---
name: fulcra-earthquake-annotation
description: Use when setting up or running a Fulcra earthquake annotation workflow from USGS, including location-aware monitor setup, numeric magnitude records, the approved note format, duplicate suppression, and optional Discord notifications.
version: 1.0.0
author: Yumemishi/Hermemishi/DianaKusunoki
license: MIT
---

# Fulcra Earthquake Annotation

## Overview

This skill defines how to record earthquakes as Fulcra numeric annotation records and optionally sending Discord notifications.

The primary value of each annotation record is the earthquake magnitude. Note attached to the record includes timestamp, magnitude/max intensity, epicenter, my distance from epicenter, tsunami watch, and USGS page.

Canonical example:

- **Annotation/data type:** `BI Earthquakes`
- **Numeric value:** `5.96`
- **Tags:** `earthquake`, `bi`, `hawaii`, `agent-recorded`, `yumemishi`
- **Note:** local time, magnitude/intensity, epicenter, user/monitor distance, tsunami watch, and USGS page.

Use this skill with Fulcra read/write access and a scheduler or cron-style polling mechanism when automation is requested.

## When to Use

Use this skill when the user wants to:

- Create or configure a Fulcra earthquake annotation.
- Monitor USGS earthquakes around their Fulcra location or another place.
- Record earthquakes into Fulcra as numeric magnitude values.
- Use defaults of recording M4.0+ and notifying on M5.0+.
- Preview the exact note that will be attached to each recorded annotation.
- Build or maintain a recurring earthquake polling/notification watchdog.

Do not use this skill for generic disaster alerts, weather alerts, or non-Fulcra logging unless the user explicitly asks to adapt the pattern.

## External References

Keep implementation details in their own skills/repos instead of embedding them here. Reference only the external capabilities needed by this workflow:

- [`fulcra-context`](https://github.com/arc-claw-bot/fulcra-context) — current user location, local timezone, and place labels.
- [`fulcra-annotations`](https://github.com/arc-claw-bot/fulcra-annotations-skill) — create annotation definitions and write verified records.
- [`scheduled-alert-watchdogs`](https://github.com/schr3b3r/poc-skills) — recurring polling, duplicate suppression, and delivery-target pattern. Use the concrete scheduler/watchdog implementation from the consuming agent runtime.

## Core Record Shape

Create a **numeric** Fulcra annotation definition.

| Field | Rule |
| --- | --- |
| Annotation name | User-approved label, e.g. `BI Earthquakes`, `Big Island Earthquakes`, `Southern California Earthquakes`, or `Nearby Earthquakes` |
| Numeric value | Earthquake magnitude, e.g. `5.96` |
| Recorded time | The USGS event time, not the time the agent writes the record |
| Tags | Short lowercase tags such as `earthquake`, region tags, `agent-recorded`, and optionally `yumemishi` |
| Duplicate guard | Stable USGS event ID / event page URL |
| Note | The canonical plain-text note format below |

## Canonical Fulcra Record Preview

Preserve this shape exactly. Do not replace it with a title/body article, a generic summary, or `Fulcra fields:` metadata.

```text
Example Fulcra record:

BI Earthquakes: 5.96

Tags:
earthquake, bi, hawaii, agent-recorded, yumemishi

Note:
Time: Friday, May 22, 9:46 PM HST
Magnitude: 5.96, 7.2 max intensity
Epicenter: 8.1 mi S of Honaunau-Napoopoo, Hawaii
My distance from epicenter: ~17.8 mi, Honalo
Tsunami watch: no

USGS page: https://earthquake.usgs.gov/earthquakes/eventpage/hv74966427
```

## General Note Template

```text
Time: {weekday, month day, h:mm AM/PM timezone}
Magnitude: {magnitude}{, {max_intensity} max intensity if available}
Epicenter: {distance mi} {direction} of {nearest_town_or_place}
My distance from epicenter: ~{distance_from_user_or_monitor_center} mi, {monitor_location_label}
Tsunami watch: {yes/no/unknown}

USGS page: {usgs_event_url}
```

If the monitor center is not the user's Fulcra location, use this distance label instead:

```text
Distance from monitored area: ~{distance_from_monitor_center} mi, {monitor_location_label}
```

## Note Rules

- Use miles.
- Use local time for the user or selected monitoring area.
- Use nearest town/place and distance/direction.
- Include maximum intensity when the source provides it; omit that phrase when unavailable.
- Use `Tsunami watch: no`, `yes`, or `unknown` based on source confidence.
- Include the USGS event page URL.
- Keep the note plain text because Fulcra mobile renders notes as plain text.

## Setup Flow

Keep setup concise. Every numbered choice must allow free-form write-in text.

### 1. Intro

```text
🌎 I’ll set up Fulcra earthquake annotations using the USGS earthquake feed.

I’ll use your Fulcra location context to suggest a monitoring area.
```

### 2. Monitoring Area

Infer the current town/city and a sensible wider region from Fulcra context. Keep the list narrow:

```text
Based on your current Fulcra location, what area should I monitor?

1. Nearby — 100 mi around {town/city}
2. Wider region — 250 mi around {region}
3. Use a different address or place
4. Write in my own area/radius

Reply with a number, or write your own.
```

Examples:

```text
1. Nearby — 100 mi around Honalo, Hawaiʻi
2. Wider region — 250 mi around Hawaiʻi Island
```

```text
1. Nearby — 100 mi around Los Angeles, CA
2. Wider region — 250 mi around Southern California
```

If the user chooses a different address/place, geocode it, propose a radius, and ask for confirmation or a write-in radius.

### 3. Annotation/Data Type Name

```text
Suggested annotation name:

{Region} Earthquakes

Reply yes to use this, or write your own.
```

Examples: `BI Earthquakes`, `Big Island Earthquakes`, `Southern California Earthquakes`, `Nearby Earthquakes`.

### 4. Fulcra Recording Threshold

```text
Do you want me to record earthquakes of 4.0 and above in your Fulcra datastore?

Reply yes, no, or write a different minimum magnitude.
```

Interpretation:

- `yes` → record `M4.0+`.
- `no` → disable Fulcra recording.
- `4.5`, `M4.5+`, `only 5+`, etc. → enable recording with that threshold.
- Unclear response → ask one concise clarification.

### 5. Discord Notification Threshold

```text
Do you want Discord notifications for earthquakes of 5.0 and above?

Reply yes, no, or write a different minimum magnitude.
```

Interpretation:

- `yes` → notify for `M5.0+`.
- `no` → disable Discord notifications.
- Custom magnitude → notify with that threshold.

### 6. Polling Frequency

```text
How often should I check USGS?

1. Every 30 minutes
2. Hourly — default
3. Every 3 hours
4. Every day

Reply with a number, or write your own. You can always ask your agent to check USGS manually anytime if you need it sooner.
```

Default: hourly.

### 7. Discord Destination

Ask only if Discord notifications are enabled.

```text
Where should I send Discord notifications?

1. This Discord thread/channel
2. A different Discord channel
3. A Discord DM
4. Write in another destination

Reply with a number, or write your own.
```

Resolve named Discord destinations with available messaging target tools where possible. Do not guess opaque channel IDs.

### 8. Example Populated Fulcra Record

Before final confirmation, show a populated Fulcra record preview using the selected settings and either a recent USGS event or clearly labeled synthetic/example data.

```text
Here’s an example of what I’d record:

{Annotation name}: {magnitude}

Tags:
{tags}

Note:
Time: {local time}
Magnitude: {magnitude}{, {max intensity} max intensity}
Epicenter: {distance + direction} of {nearest town/place}
My distance from epicenter: ~{distance} mi, {monitor location}
Tsunami watch: {yes/no/unknown}

USGS page: {event URL}
```

### 9. Final Confirmation

```text
Setup summary:
- Area: {area label}, {radius} mi
- Fulcra annotation: {name}
- Record to Fulcra: {record threshold or disabled}
- Discord notifications: {notify threshold or disabled}
- Check frequency: {poll interval}
- Notification destination: {destination or disabled}

Reply yes to create this, or tell me what to change.
```

Do not create the annotation definition, cron job, or Discord delivery until the user confirms this summary.

## USGS Event Data Requirements

Use USGS as the default source. Required data for each candidate event:

- Stable `id` and event page URL.
- Event timestamp.
- Magnitude.
- Place string or nearest-town description.
- Maximum intensity when available, such as `mmi` or `cdi`.
- Tsunami/watch status when available; otherwise `unknown`.

## Privacy and Location Handling

Follow these privacy-preserving actions.

- Use Fulcra location only with user consent.
- Use coordinates internally only for distance/radius calculations and geocoding.
- Do not expose raw user coordinates in annotation notes, setup previews, or Discord alerts.
- Use derived values instead: miles, direction, nearest town/place, monitor-area label, and broad region labels.
- If location samples are stale or uncertain, say so and use the selected monitor center rather than pretending it is the user's exact current location.

## Recurring Watchdog Pattern

For recurring monitoring, prefer a deterministic script-only cron job. This skill includes `scripts/usgs_earthquake_watch.py` for the repeatable parts: USGS querying, radius filtering, distance math, canonical note rendering, and duplicate suppression.

Use the script in one of three modes:

| Mode | Use for | Stdout behavior |
| --- | --- | --- |
| `discord` | Script-only cron notifications | Empty unless a new event meets the notification threshold |
| `jsonl` | Fulcra write pipeline | One Fulcra-ready JSON object per new recordable event |
| `both` | Manual testing/debugging | JSON records and Discord alerts |

Example notification watchdog:

```bash
python3 fulcra-earthquake-annotation/scripts/usgs_earthquake_watch.py \
  --center-lat "$MONITOR_LAT" \
  --center-lon "$MONITOR_LON" \
  --radius-mi 100 \
  --monitor-label "Honalo" \
  --annotation-name "BI Earthquakes" \
  --tags earthquake,bi,hawaii,agent-recorded,yumemishi \
  --record-min 4.0 \
  --notify-min 5.0 \
  --timezone Pacific/Honolulu \
  --mode discord
```

For a first run, the script silently seeds seen USGS IDs unless `--backfill` is provided. Use `--dry-run` while testing.

Operational rules:

1. Query USGS for events matching the chosen area and time window.
2. Filter separately for Fulcra recording threshold and Discord notification threshold.
3. Store seen USGS IDs in the agent state directory, not in the skill source directory. The script defaults to `~/.hermes/state/fulcra-earthquake-annotation/seen-usgs-events.json`.
4. Seed seen IDs silently on the first run unless the user explicitly wants historical backfill.
5. For new events above the Fulcra threshold, record the numeric annotation with the event timestamp and canonical note.
6. For new events above the Discord threshold, print/send one concise alert message.
7. Empty stdout means no notification.
8. Verify Fulcra writes by readback before claiming success.

## Fulcra Write Pattern

Before creating a definition, list existing definitions and reuse a matching one if present.

Create the definition as numeric:

```bash
python3 skills/fulcra-annotations/scripts/fulcra_annotations.py create \
  --type numeric \
  --name "BI Earthquakes" \
  --description "Earthquake magnitude records for the selected monitoring area" \
  --tag earthquake \
  --tag bi \
  --tag hawaii \
  --tag agent-recorded \
  --tag yumemishi
```

Record an event using magnitude as `--value` and the event time as `--recorded-at`:

```bash
python3 skills/fulcra-annotations/scripts/fulcra_annotations.py record \
  --name "BI Earthquakes" \
  --value 5.96 \
  --recorded-at "2026-05-23T07:46:00Z" \
  --note "Time: Friday, May 22, 9:46 PM HST
Magnitude: 5.96, 7.2 max intensity
Epicenter: 8.1 mi S of Honaunau-Napoopoo, Hawaii
My distance from epicenter: ~17.8 mi, Honalo
Tsunami watch: no

USGS page: https://earthquake.usgs.gov/earthquakes/eventpage/hv74966427" \
  --tag earthquake \
  --tag bi \
  --tag hawaii \
  --tag agent-recorded \
  --tag yumemishi
```

Use dry-run first when developing, then verify readback after real writes.

## Discord Notification Style

Keep Discord notifications concise and aligned with the Fulcra note:

```text
🌎 Magnitude 5.2 earthquake near Pāhala, Hawaiʻi
Time: Friday, May 22, 9:46 PM HST
Epicenter: 8.1 mi S of Pāhala, Hawaiʻi
My distance from epicenter: ~42 mi, Honalo
Tsunami watch: no
USGS: https://earthquake.usgs.gov/earthquakes/eventpage/...
```

If Discord-specific APIs are unavailable, use only the delivery targets actually exposed by the current runtime.

## UI Schema Hints

Future runtimes may render setup choices as buttons/select menus. Text fallback is mandatory.

```yaml
setup_options:
  monitoring_area:
    type: choice_with_write_in
    render_as: buttons_or_select
    options: [nearby, wider_region, different_address_or_place, write_in]
  record_threshold:
    type: yes_no_or_magnitude
    default: M4.0+
  notification_threshold:
    type: yes_no_or_magnitude
    default: M5.0+
  poll_frequency:
    type: choice_with_write_in
    options: [30m, 1h_default, 3h, daily]
  notification_destination:
    type: choice_with_write_in
    ask_if: notifications_enabled
```

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
