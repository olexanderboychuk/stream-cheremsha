# Cloud account linking + two-way platform auto-connect — design

Date: 2026-09-17. Status: approved (approach 1, all sections + amendments).
Repos: `stream-cheremsha` (desktop) + `cheremsha-cloud` (API).
Related: desktop `src/stream_cheremsha/cloud/*`, `src/stream_cheremsha/ui/account_pill.py`,
`src/stream_cheremsha/ui/main_window.py` (connections tab, `_start_platform_via_cloud`);
cloud `app/api/v1/auth.py`, `app/api/v1/platforms.py`, `app/api/v1/account.py`,
`app/auth/service.py`, `app/auth/providers/factory.py`.

## 1. Goals

1. One Cheremsha account reachable via several login providers: registered via
   Twitch → attach Google → log in with either.
2. App login auto-connects the platform for streaming (no second login).
   Already works for twitch/tiktok/kick via `auto_connect`; extend the same
   guarantee to YouTube.
3. Reverse: connecting a platform while logged out automatically signs the
   user into the Cheremsha account (creates it on first use).

## 2. Non-goals / hard constraints

- No new DB migrations (`AuthIdentity`, `PlatformConnection`, KV state are enough).
- No `login-and-connect` combined endpoint; reuse `login/start`,
  `platforms/{p}/connect`, `desktop/exchange`.
- Loopback callback carries no secrets and decides nothing: it is only a
  trigger for `refreshPlatforms()` / reconcile. Authoritative state is always
  Cloud API (`GET /platforms`, `GET /account/identities`, `GET /auth/me`).
- Local per-platform credentials stay as offline fallback; cloud path takes
  precedence whenever the platform row is cloud-connected.

## 3. Decisions (approved)

- Linking with different emails: attach anyway (OAuth proof = ownership).
  `User.email` stays primary; each identity keeps its own `provider_email`.
  Also heals `no-email.cheremsha.local` placeholder accounts.
- Reverse flow starts immediately, no confirm dialog; a status toast
  (`«Увійшли як X, Twitch під'єднано»`) explains what happened.
- Amendments: one-time TTL link state + replay protection;
  logout-during-pending tests; cloud-unavailable fallback; single loopback
  contract below.

## 4. Backend changes (`cheremsha-cloud`)

### 4.1 Link endpoints (`app/api/v1/auth.py`)

- `GET /auth/{provider}/link-start` (session required). Validates provider ∈
  `LOGIN_PROVIDERS`, stores KV `kind=link {provider, user_id, mode,
  created_at}` with `oauth_state_ttl_seconds` (600s), returns `AuthStartOut`.
  Same rate-limit bucket family as login (`auth:start` scope is fine).
- `GET /auth/{provider}/link-callback?code=&state=`:
  - `store.consume_json` (single-use → replay protection; unknown/expired →
    400, same as login callback).
  - Exchange code, load provider identity.
  - Lookup `AuthIdentity(provider, provider_user_id)`:
    - belongs to another user → **409** `identity belongs to another account`
      (never hijack);
    - belongs to bound user → 200 `already-linked` (idempotent);
    - new → create row on the bound user, email ignored (decision §3).
  - `audit("identity.linked")` on attach (service already emits it).
  - Desktop mode → 303 to `desktop_callback_url` with link query (§6);
    web mode → redirect to `/account?linked=<provider>`; `_wants_json` →
    JSON `{provider, status}`.
- Unlink unchanged: `DELETE /account/identities/{id}` already refuses the
  last identity (400).

### 4.2 No other backend changes

Reverse login path reuses `login/start → callback → desktop/exchange`
(auto-connect covers twitch/tiktok/kick per `LOGIN_PROVIDER_TO_PLATFORM`;
google stays login-only). YouTube uses existing
`POST /platforms/youtube/connect?mode=desktop` after login. `GET /platforms`
and runtime-token stay the single source of truth for reconcile.

## 5. Desktop changes (`stream-cheremsha`)

### 5.1 `cloud/client.py`

- `link_start(provider, access_token)` → `GET /auth/{provider}/link-start`.
- `platform_connect_start(platform, access_token)` →
  `POST /platforms/{platform}/connect?mode=desktop`.
- `get_identities(access_token)` → `GET /account/identities`.
- `unlink_identity(identity_id, access_token)` → `DELETE …`; surface 400
  (last identity) as notice, not a crash.
- No secret logging (existing `_request` rule covers new methods).

### 5.2 Single loopback contract (`cloud/callback.py`, `constants.py`)

One server, `127.0.0.1:8471/callback`, three result kinds, all single-use
futures with `LOGIN_WAIT_TIMEOUT_S`, `access_log=None` unchanged:

- `?code=<grant>&state=<desktop_state>` — login grant; accepted only when
  `state` equals the generated one (existing CSRF guard).
- `?platform=<p>&status=connected|error` — platform-connect finished;
  accepted only while a platform-connect wait is armed for `<p>`, otherwise
  ignored (stray/malicious local hits only trigger nothing).
- `?action=link&provider=<p>&status=ok|conflict|already` — link finished;
  accepted only while a link wait is armed.

Any wait armed → exactly one resolution or timeout/cancel; `stop()` always
runs in `finally` (existing pattern).

### 5.3 `cloud/auth_state.py`

- `linkProvider(provider)` slot: no-op unless `authenticated` (dup-guarded via
  `_launch`). Flow: `link_start` → open browser → wait link future →
  `refreshPlatforms()` + identities refresh signal. `conflict` → notice
  `link-conflict` (footer text, no popup).
- `connectPlatform(platform)` slot:
  - Logged out → `login(mapped_provider)` + store `_pending_platform`.
    Mapping: twitch→twitch, tiktok→tiktok, kick→kick, youtube→google.
    After `authenticated`: twitch/tiktok/kick arrive with `auto_connect`
    (existing); if `_pending_platform == "youtube"` → run authenticated
    platform-connect flow for youtube.
  - Logged in → `platform_connect_start` → open browser → wait platform
    future → `refreshPlatforms()` (reconcile starts the source via broker).
- `logout()` cancels any armed link/connect wait (same convention as login
  cancel) and clears `_pending_platform`; flows converge on logged-out.
- New `identitiesChanged` signal + cached identities list (user-visible
  fields only: provider, provider_email).

### 5.4 UI

- Account pill popover: identities section — rows
  `provider + provider_email + «від'єднати»`, plus `«під'єднати …»` buttons
  for providers in `LOGIN_PROVIDERS` not yet linked. Unlink of the last
  identity shows the backend 400 text in the footer.
- Connections tab: transport/connect buttons route to
  `connectPlatform(platform)` first. On `unreachable` notice → reveal the
  existing local login panel (manual token / keyring OAuth) as fallback.
  Successful cloud connect keeps local panels hidden; explicit cloud
  disconnect returns to them.
- All user strings via `l10n` (`cloud.link_*`, `cloud.*connected*` reuse).

## 6. Loopback query reference (normative)

| cause | query | desktop reaction |
|---|---|---|
| login grant | `?code=&state=` | exchange → session (existing) |
| platform connected | `?platform=<p>&status=connected` | `refreshPlatforms()` → reconcile |
| link done | `?action=link&provider=<p>&status=ok\|conflict\|already` | identities refresh; `conflict` → footer notice |

## 7. Tests

Backend (`cheremsha-cloud/tests`): link attaches second provider with a
different email to the same user; repeat link idempotent; foreign identity →
409 and no row created; expired/replayed link state → 400; desktop link
redirect carries exact query (§6); unlink-last still 400 (exists).
Desktop (`stream-cheremsha/tests`): link flow on scripted client incl.
`conflict` notice; `connectPlatform` logged-out → login called with mapped
provider + pending set; youtube pending → connect_start after auth;
loopback ignores unarmed platform/link hits; logout-during-pending
(link wait, connect wait, login wait) converges on logged-out with no
leaked task; cloud-unavailable connect falls back to local panel trigger.
Full suites + `ruff check` on both repos must stay green.

## 8. Manual QA matrix

Providers {google, twitch, tiktok, kick} × {logged out, logged in} for link;
platforms {twitch, youtube, tiktok, kick} × {logged out, logged in,
cloud-down} for connect; unlink down to one identity; email-mismatch link;
replay of a used link URL.
