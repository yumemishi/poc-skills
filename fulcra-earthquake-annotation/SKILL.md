---
name: fulcra-earthquake-annotation
description: Record earthquake events as Fulcra moment annotations. Use when a user wants to log an earthquake they felt, saw reported, or researched, including USGS-style details such as magnitude, event time, location, depth, tsunami status, felt reports, and source links. Depends on the `fulcra-annotations` skill for Fulcra writes.
---

# Fulcra Earthquake Annotation

Record an earthquake as a Fulcra **Moment** annotation. This skill is for event breadcrumbs, not long-form disaster reports.

Load `fulcra-annotations` before writing. Use its bundled script rather than direct API calls.

Bundled definition metadata is in `annotation/earthquake.annotation.json`; use it as the canonical field list when creating or reviewing the annotation definition.

## Annotation definition

Create or reuse this definition:

- **Name:** `Earthquake`
- **Type:** `moment`
- **Description:** `An earthquake event relevant to the user, recorded with key seismic details and source links.`
- **Definition tags:** `earthquake`, `environment`, `event`

Create if missing:

```bash
python3 skills/fulcra-annotations/scripts/fulcra_annotations.py create \
  --type moment \
  --name "Earthquake" \
  --description "An earthquake event relevant to the user, recorded with key seismic details and source links." \
  --tag earthquake \
  --tag environment \
  --tag event
```

## When to record

Record when the user explicitly asks to log, annotate, save, or remember an earthquake in Fulcra.

Do not record just because the agent summarizes earthquake news. Ask first unless the user already requested logging.

## Required fields before writing

Gather or infer from reliable sources:

- event time with timezone, preferably the earthquake origin time
- magnitude
- location/epicenter
- source link or source name

If any required field is unknown, ask or record only after clearly marking it unknown in the note.

## Optional fields

Include when available:

- depth
- coordinates
- tsunami status
- felt intensity / felt reports
- aftershock note
- related volcano or hazard note
- USGS event ID
- one or more source URLs

## Note format

Keep notes compact and structured. Do not paste whole articles.

Suggested note:

```text
M6.0 earthquake; origin 2026-05-22T21:46:00-10:00; location ~7 mi / 12 km S of Hōnaunau-Nāpōʻopoʻo, Hawaiʻi Island; depth ~14 mi / 22 km; no tsunami threat; widely felt across Hawaiʻi; source: USGS <url>.
```

## Write workflow

1. Verify the annotation definition exists:

```bash
python3 skills/fulcra-annotations/scripts/fulcra_annotations.py list
```

2. Create it if missing using the command above.
3. Record with the earthquake origin time as `--recorded-at`.
4. Add record tags that describe the specific event. Prefer short tags such as:
   - `usgs`
   - `felt`
   - `hawaii`
   - `tsunami-none`
   - `backfill`
5. Confirm `verified_matches >= 1` before reporting success.

Example record:

```bash
python3 skills/fulcra-annotations/scripts/fulcra_annotations.py record \
  --name "Earthquake" \
  --recorded-at "2026-05-22T21:46:00-10:00" \
  --note "M6.0 earthquake; location ~7 mi / 12 km S of Hōnaunau-Nāpōʻopoʻo, Hawaiʻi Island; depth ~14 mi / 22 km; no tsunami threat; widely felt across Hawaiʻi; source: USGS https://www.usgs.gov/observatories/hvo/news/earthquake-information-statement" \
  --tag earthquake \
  --tag usgs \
  --tag hawaii \
  --tag tsunami-none
```

## Safety and privacy

- Do not include private third-party details from felt reports.
- Prefer public source links and summarized facts.
- If logging a personally felt event, include only what the user approved.
- Never expose Fulcra tokens, credential paths, or raw private Fulcra records.
