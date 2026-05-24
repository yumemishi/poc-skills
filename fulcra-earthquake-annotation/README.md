# fulcra-earthquake-annotation

Proof-of-concept skill for recording earthquake events as Fulcra number annotations.

## Contents

- `SKILL.md` — agent instructions for when and how to record earthquake events.
- `scripts/earthquake.annotation.json` — reusable Fulcra annotation definition metadata.
- `fulcra-earthquake-annotation.skill` — packaged skill archive generated from this folder.

## Annotation

The skill creates or uses a Fulcra number annotation named `Earthquake` with tags for earthquake/environment/event context. It is intended for compact event breadcrumbs such as timestamp, magnitude, max intensity, depth, epicenter location, distance from epicenter, tsunami status, and USGS links.

## Use

Load this skill when a user asks to log, annotate, save, or remember an earthquake in Fulcra. It depends on the `fulcra-annotations` skill for all Fulcra writes.
