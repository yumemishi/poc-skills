# Fulcra Earthquake Annotation

Record earthquakes from USGS as numeric Fulcra annotations, with optional Discord notifications.

This skill is for location-aware earthquake monitoring where the primary Fulcra value is the earthquake magnitude and the note contains the human-readable event details: local time, magnitude/intensity, epicenter, distance from the monitored location, tsunami watch status, and the USGS page.

## What It Does

- Uses the USGS earthquake feed as the event source.
- Records earthquakes as **numeric** Fulcra annotation records.
- Uses the earthquake magnitude as the annotation value.
- Writes event time as the record timestamp, not the time the agent records it.
- Keeps notes plain text for Fulcra mobile rendering.
- Optionally sends concise Discord alerts above a separate notification threshold.
- Avoids exposing raw coordinates in user-facing notes or alerts.
