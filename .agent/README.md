# .agent/README.md

## Purpose
This directory contains the **Persistent AI Context Layer** for Cheremsha. It is designed to help AI coding agents navigate the repository efficiently, reduce token consumption by preventing redundant exploration, and ensure consistent adherence to architectural rules.

## How to Use
1.  **Startup**: Agents should read `AGENTS.md` first to understand the operational protocol.
2.  **Navigation**: Use `PROJECT_MAP.md` to find where specific features are implemented.
3.  **Deep Dive**: When working on a specific subsystem (e.g., Chat, TTS), load the corresponding module context from `.agent/modules/`.
4.  **Flow Analysis**: For end-to-end tasks (e.g., "How does a music request work?"), read the relevant flow file in `.agent/flows/`.

## Context Types
- **Modules (`.agent/modules/*.md`)**: Subsystem-specific details, canonical locations, and change guides.
- **Flows (`.agent/flows/*.md`)**: Step-by-step sequences of runtime operations.
- **Decisions (`.agent/decisions/*.md`)**: Records of important architectural choices (ADRs).

## Update Strategy
- If you make a significant architectural change, update the relevant `.agent/` documentation.
- Documentation is derived from code; if they disagree, **CODE WINS**.
