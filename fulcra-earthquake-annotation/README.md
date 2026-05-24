# fulcra-earthquake-annotation

Proof-of-concept AgentSkill for recording earthquake events as Fulcra moment annotations.

## Contents

- `SKILL.md` — agent instructions for when and how to record earthquake events.
- `annotation/earthquake.annotation.json` — reusable Fulcra annotation definition metadata.
- `fulcra-earthquake-annotation.skill` — packaged skill archive generated from this folder.

## Annotation

The skill creates or reuses a Fulcra moment annotation named `Earthquake` with tags for earthquake/environment/event context. It is intended for compact event breadcrumbs such as magnitude, origin time, location, depth, tsunami status, felt reports, and source links.

## Use

Load this skill when a user asks to log, annotate, save, or remember an earthquake in Fulcra. It depends on the `fulcra-annotations` skill for all Fulcra writes.
