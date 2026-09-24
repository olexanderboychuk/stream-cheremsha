# AI Agent Knowledge Architecture

This directory houses the **Layered Knowledge System** designed to minimize reconnaissance token consumption (~5–15k target) and provide targeted, hierarchical context retrieval.

---

## Knowledge Layers

- **L0 — Project Identity**: [PROJECT_MAP.md](file:///home/oleksandrboichuk/Dev/Self/stream-cheremsha/PROJECT_MAP.md) (Tech stack, constraints, entry points).
- **L1 — Architecture Map**: [PROJECT_MAP.md](file:///home/oleksandrboichuk/Dev/Self/stream-cheremsha/PROJECT_MAP.md) (Subsystems, locations, interfaces, dependencies).
- **L2 — Domain Knowledge**: [.agent/domains/](file:///home/oleksandrboichuk/Dev/Self/stream-cheremsha/.agent/domains/) (Focused domain specifications, extension recipes, symbols).
  - `ui_desktop.md`
  - `overlays_widgets.md`
  - `chat_aggregation.md`
  - `tts_pipeline.md`
  - `music_player.md`
  - `donations.md`
  - `actions_engine.md`
  - `battle_games.md`
  - `config_keyring.md`
  - `obs_integration.md`
- **L3 — Architectural Decisions & Invariants**: [.agent/decisions/](file:///home/oleksandrboichuk/Dev/Self/stream-cheremsha/.agent/decisions/) (Decisions that are expensive to rediscover from code).
  - `ui_lazy_loading.md`
  - `widget_instances_pubsub.md`
  - `keyring_and_secrets.md`
  - `tts_audio_pipeline.md`
- **L4 — Symbol & Pattern Index**: [.agent/index.md](file:///home/oleksandrboichuk/Dev/Self/stream-cheremsha/.agent/index.md) (Searchable index of core classes, tab indices, topics, and models).

---

## Workflow Protocol
See [AGENTS.md](file:///home/oleksandrboichuk/Dev/Self/stream-cheremsha/AGENTS.md) for the reconnaissance lifecycle:
**DISCOVER → ROUTE → TARGET → INSPECT → STOP**
