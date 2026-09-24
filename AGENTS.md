# AGENTS.md

## Core Principle
**DISCOVER → ROUTE → TARGET → INSPECT → STOP**

Do NOT attempt to construct a complete mental model of the entire repository before working on a feature. You only need the minimum sufficient model required for the requested change.

---

## Targeted Reconnaissance Flow

### STEP 1 — Parse the Feature
Extract:
- Requested behavior and user-facing change.
- Likely domain (e.g. `OverlaysWidgets`, `DesktopUI`, `TTSPipeline`).
- Likely entities, widgets, or components.
- Explicit constraints and out-of-scope items.

### STEP 2 — Route
1. Look at [PROJECT_MAP.md](file:///home/oleksandrboichuk/Dev/Self/stream-cheremsha/PROJECT_MAP.md) L1 Architecture Map or [.agent/index.md](file:///home/oleksandrboichuk/Dev/Self/stream-cheremsha/.agent/index.md) Symbol Index to identify the **1 or 2 relevant domains**.
2. **DO NOT** inspect or read unrelated domains.

### STEP 3 — Read Domain Knowledge
Read **ONLY** the relevant domain document in `.agent/domains/<domain>.md` and its associated decision document in `.agent/decisions/` if referenced.
Identify:
- Candidate implementation files.
- Candidate symbols and methods.
- Relevant invariants constraining the change.

### STEP 4 — Targeted Source Inspection
Inspect **ONLY** the exact source files and symbols required:
1. Where does the current behavior live?
2. What abstraction owns it?
3. Where should the new behavior integrate?
4. What existing pattern should be reused?

**CRITICAL**: Use line-range slices (e.g. `StartLine`/`EndLine`). **NEVER** read multi-thousand line files (e.g. `main_window.py`) in their entirety.

### STEP 5 — Follow Dependencies Only When Necessary
Follow a dependency only if:
- Its behavior directly affects the feature.
- Ownership is unclear.
- An invariant depends on it.
- The integration point cannot otherwise be determined.
Avoid "just in case" exploration.

---

## Exploration Stop Condition

**STOP exploration immediately** once you can answer all 8 questions:
1. Which subsystem owns the feature?
2. Which existing abstraction should be extended or reused?
3. Which files and symbols implement the current behavior?
4. What exact code path will change?
5. What integration points are required?
6. Which invariants or architectural decisions constrain the change?
7. Which existing tests establish the expected pattern?
8. Which exact files will be modified or created?

You do NOT need complete knowledge of the repository. You only need sufficient knowledge to produce an airtight implementation plan.

---

## Exploration Token Budget

- **Project Knowledge (L1/L2/L3)**: $\le 3\text{k}$ tokens
- **Targeted Source Slices (L4/Source)**: $\le 8\text{k}$ tokens
- **Tests & Examples**: $\le 4\text{k}$ tokens
- **Target Total**: **~5–15k tokens** (Complex multi-system features: ~15–25k tokens).

If exploration reaches this budget: **STOP**. Re-evaluate whether remaining missing information is truly essential or if you are over-exploring.

---

## Anti-Loop Rules

You must **NOT**:
- Read every file in a directory "for context".
- Read entire large files when only one method or constant is needed.
- Grep broadly when [.agent/index.md](file:///home/oleksandrboichuk/Dev/Self/stream-cheremsha/.agent/index.md) lists the exact symbol location.
- Inspect unrelated domains (e.g., loading `music/` when working on an overlay widget).
- Recursively inspect dependencies that are behind established public interfaces.
- Continue exploring merely to eliminate theoretical uncertainty.

---

## Knowledge Freshness

When completing a feature, check if your change introduced:
- A new subsystem or widget type.
- A new public interface or major abstraction.
- A new architectural invariant or state boundary.
- A new decision that was expensive to determine.

If yes, update the corresponding `.agent/domains/<domain>.md` or `.agent/decisions/<topic>.md`. Do **NOT** document trivial implementation details.

---

## Plan Generation Standard

Once the Stop Condition is reached, generate the implementation plan with:
1. **Feature Boundary**: What is changing and what is explicitly OUT of scope.
2. **Existing Architecture**: Relevant systems and existing patterns being extended.
3. **Implementation Points**: Exact files, classes, methods, and line regions to modify.
4. **Data & Control Flow**: Step-by-step lifecycle from input event to final output.
5. **Edge Cases & Error Handling**: Failure paths, fallbacks, and boundary conditions.
6. **Testing**: Concrete test files and assertions to execute.

---

## Developer Commands

- **Run Application**: `.venv/bin/python -m stream_cheremsha`
- **Run Unit Tests**: `PYTHONPATH=. .venv/bin/pytest tests/test_<target>.py`
- **Linting**: `.venv/bin/ruff check src tests`
- **Formatting**: `.venv/bin/ruff format src tests`
- **Build**: `pip install -e ".[build]" && cheremsha-build`
