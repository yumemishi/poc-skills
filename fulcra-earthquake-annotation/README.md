# fulcra-earthquake-annotation

Proof-of-concept skill for recording earthquake magnitude as a Fulcra number annotation.

## Contents

- `SKILL.md` — agent instructions for when and how to record earthquake events.
- `scripts/earthquake.annotation.json` — reusable Fulcra number annotation definition metadata.
- `fulcra-earthquake-annotation.skill` — packaged skill archive generated from this folder.

## Annotation

The skill creates or uses a Fulcra number/numeric annotation named `Earthquake`; the recorded value is the earthquake magnitude. The note uses a fixed structured field order: timestamp, magnitude, max intensity, depth, epicenter, distance from the relevant location, tsunami status, source, and notes.

## Use

Load this skill when a user asks to log, annotate, save, or remember an earthquake in Fulcra. It depends on the `fulcra-annotations` skill for all Fulcra writes.
