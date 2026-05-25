# poc-skills

Proof-of-concept Fulcra skills packaged for Codex-style agent use.

## Skills

- [`fulcra-earthquake-annotation`](fulcra-earthquake-annotation/SKILL.md) - Monitor USGS earthquakes and produce Fulcra-ready numeric annotation records.

## Quick Start

Copy or link the skill folder into your Codex skills directory, then invoke it by name:

```text
Use $fulcra-earthquake-annotation to set up Big Island earthquake monitoring.
```

The bundled helper script can also be run directly:

```bash
python3 fulcra-earthquake-annotation/scripts/usgs_earthquake_watch.py \
  --config fulcra-earthquake-annotation/examples/hawaii-island.config.json \
  --dry-run \
  --backfill
```

## Repository Layout

```text
fulcra-earthquake-annotation/
  SKILL.md                         Agent-facing skill instructions
  agents/openai.yaml               UI metadata for Codex skill lists
  examples/hawaii-island.config.json
  examples/config.schema.json
  references/setup-flow.md         User-facing setup prompts
  references/output-contract.md    Fulcra writer and notification contract
  scripts/usgs_earthquake_watch.py Deterministic USGS polling helper
src/
  fulcra_earthquake_annotation/
    watch.py                       Importable watchdog implementation
tests/
  fixtures/
  test_usgs_earthquake_watch.py
```

## Development

This repo intentionally keeps runtime dependencies at zero. Tests use the Python standard library.

```bash
python3 -m unittest discover -s tests
```

## Data And Permissions

The earthquake helper uses monitor coordinates only for USGS radius queries and distance math. User-facing notes and alerts use derived place labels, distances, and event URLs rather than raw user coordinates.
