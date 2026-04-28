## Goal

Add a **local overlay server** to the app, exposing **overlay pages by URL** so users can add them to OBS as **Browser Source**.

This document defines the **foundation** (server + overlay type registry + live updates) so future overlay types can be added incrementally (chat overlay, alerts, info widgets, etc.).

## Non-goals (v1 foundation)

- Cloud hosting / public internet exposure
- Multi-machine overlays
- Tight coupling to Qt WebEngine (OBS renders the overlay in its own browser)
- A full UI for managing overlay presets (we may add basic “copy URL” later)

## Key principles

- **Local-only by default**: bind to `127.0.0.1` (localhost) unless explicitly changed later.
- **Extensible overlay types**: new overlays are added by registering a new type, not by rewriting the server.
- **Live updates**: overlays update without browser refresh via a streaming channel (WebSocket preferred; SSE acceptable).
- **Nuitka-friendly**: static assets and templates must work in standalone builds.

## User experience (baseline)

Users will be able to copy a URL such as:

- `http://127.0.0.1:<port>/overlay/chat?instance=main`

and add it in OBS as a Browser Source.

Multiple overlays of the same type are supported by specifying an **instance identifier** (see “Instances”).

## HTTP API

### Pages

- `GET /overlay/<type>` → returns HTML for the overlay page

Examples (future):

- `/overlay/chat`
- `/overlay/alerts`
- `/overlay/widget`

### Static assets

- `GET /assets/<path>` → CSS/JS/fonts/images used by overlay pages

### Health

- `GET /health` → 200 response, body: `ok`

Used for quick diagnostics and to detect whether the overlay server is up.

## Instances and parameters

Overlay pages may exist multiple times simultaneously, with different configuration (styles, filters, selected platforms, etc.). The **foundation** supports this via a required or recommended `instance` parameter:

- `GET /overlay/<type>?instance=<instance_id>`

Where:

- `instance_id` is a short string, e.g. `main`, `left`, `alerts1`
- if missing, the server may treat it as `default`

In the future, additional query parameters can configure an instance. The server will parse them and pass them to overlay render/state functions as a normalized `params` object.

## Live updates (streaming channel)

The overlay server provides a streaming channel so overlays can receive updates without refresh.

### Preferred: WebSocket

- `WS /ws`

Client must identify what it wants to receive (overlay type + instance + params) as the first message, for example:

```json
{
  "op": "subscribe",
  "type": "chat",
  "instance": "main",
  "params": { }
}
```

Server replies with:

- `initial_state` (full state snapshot)
- subsequent `patch` messages (incremental updates)

### Alternative: SSE (server-sent events)

If WebSocket is undesirable on some platforms, an SSE endpoint can be used:

- `GET /events?type=<type>&instance=<instance>&...`

SSE messages should use the same payloads as WebSocket messages.

## Overlay type registry

Overlays are defined as **types** registered in a central registry.

Each overlay type provides:

- `type: str` — unique identifier, e.g. `"chat"`
- `render_html(params) -> str` — returns the HTML for the page (includes a small bootstrap script that connects to WS/SSE)
- `initial_state(params) -> dict` — the initial state snapshot for this overlay instance
- `subscribe(params) -> async iterator of patches` OR a callback-based subscription that emits patches

### State and patch format

The foundation standardizes a small message envelope:

- `initial_state` message:

```json
{ "op": "initial_state", "state": { } }
```

- `patch` message:

```json
{ "op": "patch", "patch": { } }
```

Patch format is intentionally unspecified at this layer (it can be a full state replacement, a shallow merge, or an explicit operation list). For v1 foundation, prefer **full replace** or **shallow merge** for simplicity.

## Data sources and internal wiring

Overlays are fed by data already present in the app:

- Chat events (`ChatMessage`) from existing sources/coordinator
- Future “platform actions” events (Event → Actions) can emit overlay events later

The foundation introduces a minimal in-process **pubsub/event bus**:

- internal publishers push normalized events (chat message, gift, donation, etc.)
- overlay instances subscribe to relevant topics

This keeps overlay rendering independent from UI and platform specifics.

## Security and configuration

### Defaults

- Bind address: `127.0.0.1`
- Port: a configurable port, with an **auto-fallback** if the port is already in use

### Optional token

Optionally, a `token` query parameter can be required for overlay pages and streaming endpoints:

- `/overlay/chat?instance=main&token=<token>`

This is primarily a defense-in-depth mechanism against accidental local exposure or local untrusted processes; it is not meant as strong authentication.

## Reliability and lifecycle

The overlay server must:

- start/stop cleanly with the app lifecycle
- not hang the UI thread
- survive temporary errors; WebSocket/SSE clients should be able to reconnect

## Testing strategy (foundation)

- Unit tests:
  - URL/params parsing into normalized `params`
  - overlay registry behavior (type lookup, missing type errors)
  - message envelopes (`initial_state`, `patch`)
- Integration tests:
  - start server, `GET /overlay/debug` returns HTML
  - connect streaming channel, receive `initial_state` then at least one `patch`

