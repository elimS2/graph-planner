## Graph Planner — Translation Feature Roadmap (Node Title Localization)

Status: In Progress
Owner: Team
Last Updated: 2025-08-30T18:19:37Z

---

### 1) Initial Prompt (translated to English)

Analyse the task and project deeply and decide how best to implement it.

Create a detailed, step-by-step implementation roadmap in a separate document file. We have the folder `docs/features`. If it does not exist, create it. Capture in the document all discovered and tried problems, nuances, and solutions as much as possible. During the implementation of this task, you will use this file as a todo checklist; you will update this file and document what has been done, how it was done, what problems arose, and what decisions were made. For history, do not delete items; you can only update their status and add comments. If during implementation it becomes clear that something needs to be added as tasks – add it to this document. This will help us preserve the context window, remember what has already been done, and not forget to do what was planned. Remember that only the English language is allowed in the code, comments, and project labels. When you write the plan, stop and ask me if I agree to start implementing it or if something needs to be adjusted.

Include this very prompt I wrote in the plan, but translate it into English. You can call it something like "Initial Prompt" in the plan document. This is necessary to preserve the context of the task setting in our roadmap file as accurately as possible without the "broken telephone" effect.

Also include steps for manual testing: what needs to be clicked through in the interface.

Follow the principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.
Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design.
Use Best Practices.

---

### 2) Goal and Scope

Enable high-quality machine translation of node titles into a chosen language (initially English), with:
- High quality provider preference (DeepL API first; optional Google/Azure later)
- Caching of translations in our DB (no repeated calls)
- Server-side translation (keeps API keys secret)
- UI toggle to display translated titles on the graph
- Manual per-project bulk translate flow and background job safety

Out of Scope (for this iteration):
- Full description/comments translation (future)
- Auto-detection of user locale with per-user preferences (future)

---

### 3) Architecture Decisions

- Provider: DeepL API (`deepl`) first. Add `libre` provider (LibreTranslate) for no-card testing; keep `mock` for dev only. Interface open for Google/Azure in future.
- Translation cache model: normalized table `NodeTranslation(node_id, lang, text, provider, detected_source_lang, created_at)`.
- API keys in `.env` (e.g., `DEEPL_API_KEY`). Optional `TRANSLATION_PROVIDER=deepl|google|azure|libre`.
- Server-side batching: translate in batches (<= 50 items) to respect rate limits; exponential backoff.
- Idempotency: if translation exists for `(node_id, lang)`, reuse.
- UI: toolbar language switch (e.g., "Show titles in: [Original|English]") with immediate re-render.
- Fallback strategy: if translation missing -> show original; trigger background fetch (MVP can be sync request with loading state).

---

### 4) Data Model Changes

Add a new table and (optional) per-project preference field.

```sql
CREATE TABLE node_translation (
  node_id TEXT NOT NULL REFERENCES node(id) ON DELETE CASCADE,
  lang TEXT NOT NULL,
  text TEXT NOT NULL,
  provider TEXT NOT NULL,
  detected_source_lang TEXT,
  created_at TEXT NOT NULL,
  PRIMARY KEY (node_id, lang)
);
```

Optional later:
- `project.preferred_display_lang TEXT NULL` (for default UI choice per board)

---

### 5) API Surface

Base: `/api/v1`

- POST `/projects/{id}/translate` (JSON: `{ lang: "en", provider?: "deepl", dry_run?: false }`)
  - Translates titles of nodes missing a cached translation for `lang`.
  - Returns `{ data: { translated: number, skipped: number } }`.

- GET `/nodes/{id}/translations?lang=en`
  - Returns `{ data: { node_id, lang, text, provider, detected_source_lang } | null }`.

- GET `/projects/{id}/nodes?lang=en` (optional extension)
  - If `lang` set, includes `title_translated` per node when available.

Errors: unified JSON errors, 4xx for user errors, 5xx for provider/network.

---

### 6) Services and Providers

`app/services/translation.py`:
- `translate_texts(texts: list[str], target_lang: str, provider: str) -> list[TranslatedItem]`
- Batching, provider selection, basic retry/backoff
- Provider adapters:
  - `DeepLProvider` (HTTP to api.deepl.com)
  - `LibreProvider` (LibreTranslate REST API)
  - `MockProvider` (local, prefixes text for testing)
  - `MyMemoryProvider` (public REST; heuristic src; guarded)
  - `GeminiProvider` (LLM translation via Vertex/Generative API) [planned]
  - `GoogleProvider` (future)
  - `AzureProvider` (future)

`app/repositories/translations.py`:
- CRUD for `NodeTranslation`
- `get_cached(node_ids, lang)`, `upsert_many(records)`

---

### 7) UI/UX

- Toolbar: select `Language: [Original, English]` (MVP: English only toggle `Show English`)
- When toggled on: labels use `title_translated` (or cached translation); else `title`.
- If not translated yet: show spinner toast "Translating…" and perform POST translate; then re-fetch nodes and re-render.
- Respect accessibility: clear label of toggle, keyboard focus, ARIA.

---

### 8) Configuration

`.env`:
- `TRANSLATION_PROVIDER=deepl|libre|mymemory|gemini|mock`
- `DEEPL_API_KEY=...` (deepl)
- `LT_API_URL` and `LT_API_KEY` (libre)
- `GEMINI_API_KEY` (Generative Language API) or Vertex SA creds
- Timeouts: `TRANSLATION_TIMEOUT_MS=60000`
- Rate: `TRANSLATION_BATCH_SIZE=50`
- Async workers: `ASYNC_WORKERS=2` (MVP ThreadPool)
- For local testing without keys set `TRANSLATION_PROVIDER=mock`

`requirements.txt`:
- `deepl==1.*` (official client) or `requests`-based minimal client

---

### 9) Error Handling & Resilience

- Provider timeouts → retry with backoff (3 attempts)
- Rate limit 429 → wait `Retry-After` or 1–2s, continue
- Partial failures: cache successful ones, report counts
- Logging: provider, lang, count, duration, failures

---

### 10) Security & Cost Control

- API key only server-side; never exposed to browser
- Cache aggressively; never translate same `(node_id, lang)` twice
- Optional per-request `dry_run` to estimate cost

---

### 11) Performance

- Translate only new/changed titles (compare hashes)
- Batch calls
- Lazy request per board on demand

---

### 12) Testing Plan

Unit:
- Provider adapter happy-path and 4xx/5xx
- Repository upsert and get_cached

Integration:
- POST `/projects/{id}/translate` with mocked provider
- GET `/nodes/{id}/translations` returns cached record

UI (manual + Playwright later):
- Toggle language → triggers translate (if needed) → titles update

---

### 13) Manual Testing Steps

1) Open a board with non-English titles
2) Click `Show English` (or Language=English)
3) Observe toast "Translating…" then titles change to English
4) Refresh page → translations persist; no new network translate calls
5) Create a new node with non-English title → toggle on → only the new node gets translated
6) Network fault simulation → show error toast; original titles remain

---

### 14) Step-by-Step Implementation Checklist

1. Data & Repo [pending]
   - Create `NodeTranslation` model and migration / dev-upgrader
   - Implement repo functions `get_cached`, `upsert_many`

2. Provider layer [completed]
   - Add `app/services/translation.py` with DeepL client (env key)
   - Batch translate with retry/backoff

3. API [completed]
   - POST `/projects/{id}/translate` (server-only translate, cache)
   - GET `/nodes/{id}/translations`
   - Optional: extend `GET /projects/{id}/nodes?lang=en` to include `title_translated`

4. UI [completed]
   - Toolbar toggle `Show English`
   - When on: fetch nodes with translations via `?lang=en` (ensuring cache via POST /translate)
   - Persist choice in localStorage; re-render labels

5. Tests [pending]
   - Unit for services/repo; integration for API; manual flow

6. Docs [pending]
   - Update README/env sample; add provider notes

---

### 15) Risks & Mitigation

- Provider cost/limits → caching and batch, optional dry-run
- Quality variance → allow provider switch later
- PII concerns → we only send titles; document policy

---

### 16) Definition of Done

- DeepL integration with env-configured key
- Translations cached in `node_translation`
- UI toggle switches labels without refresh; bulk translate path works
- Tests green; docs updated

---

### 17) Change Log (append-only)

- 2025-08-30T11:11:54Z — Draft roadmap created with DeepL-first approach; caching strategy; UI toggle; API outline; manual tests.

---

### 18) Extended Requirements: Triggers, Staleness, Comments, and Batch Maintenance

This section captures additional design requirements to ensure high quality and maintainable translations across nodes and comments.

1) What initiates translation?
- On-demand (manual): a button per project to translate missing/outdated items
- Automatic hooks: after node/comment create or update, enqueue translation refresh for already-used languages
- UI view toggle (e.g., English): if cache missing → trigger background job (or sync MVP) then refresh view

2) Coverage
- Existing nodes: translate all titles into selected languages (e.g., `en`, `uk`) [completed]
- Existing comments: translate all comment bodies as well [completed]

3) Data model enhancements
- `node_translation(node_id, lang, text, provider, detected_source_lang, source_hash, created_at)`
- `comment_translation(comment_id, lang, text, provider, detected_source_lang, source_hash, created_at)`
- Ensure source records have `updated_at` (or `content_hash`) to detect staleness
  - If missing in current schema: add `updated_at` to `node` and `comment`
  - Alternatively introduce an immutable `content_hash` for quick comparison

4) Staleness detection
- A translation is stale if:
  - `source.updated_at > translation.created_at`, or
  - `hash(title_or_body) != translation.source_hash`
- Queries:
  - Find all nodes/comments with missing translation for a language
  - Find all nodes/comments with stale translation for a language

5) Events (optional but recommended)
- Table `content_event(id, entity_type, entity_id, event_type, created_at, payload_json)`
  - Examples: `node.title_updated`, `comment.body_updated`, `translation.updated`
  - Benefits: audit/history, ability to rebuild translation backlog

6) APIs & CLI
- GET `/projects/{id}/translation/stats?lang=en` → `{missing_nodes, stale_nodes, missing_comments, stale_comments}`
- POST `/projects/{id}/translate` `{ lang, include: ["nodes","comments"], stale: true }`
  - Translates missing; if `stale=true`, also refreshes stale
- CLI `flask translate-project --project <id> --lang en --stale` for batch maintenance
 - Node-level:
   - GET `/nodes/{id}/translation?lang=en` → `{text}|null` [completed]
   - POST `/nodes/{id}/translate` `{lang, provider?}` → caches translation and returns `{text}` [completed]

7) Background execution
7) Background execution [updated]
- MVP: lightweight in-process ThreadPool executor with job registry [completed]
- Persistent status: DB model `BackgroundJob` with API status backed by DB [completed]
- API:
  - POST `/projects/{id}/translate/async` → returns `{ job_id }` [completed]
  - GET `/jobs/{job_id}` → returns `{status, total, done, translated, skipped, error}` [completed]
- Next: replace with robust queue (RQ/Celery) [pending]

8) UI [updated]
- Toggle: `Show English` [completed]
- Diagnostics button: shows missing/stale counts [completed]
- Async translate button: starts job and polls status; refreshes graph on finish [completed]

9) Best practices
- Hash-based staleness check avoids time drift
- Batching limits; exponential backoff on provider errors
- Provider-agnostic service + per-provider adapters
 - LLM pass: optional “polish” step for style/context (Gemini) after NMT

---

### 19) Additional Prompt (translated from Russian as-is)

Discuss how we will translate. What will initiate the translation? We already have many nodes created; we need to translate their titles and comments. Most likely, we need a separate translation table convenient for queries. For example, request all titles that do not have a translation into Ukrainian or English. Then iterate through them and store the translation.

When creating or editing a node, automatically update translations for the languages that already exist in translations.

Same for comments.

We also need a script or a button that launches a database sweep to find missing or outdated translations. We can consider a translation outdated if it was created before the title or comment was edited.

If the database does not store the time when the title or comment was edited, then we need to create these fields.

Alternatively, make a separate table that stores events, including editing the title of a particular node, or editing a particular comment; updating the translation of a particular comment or title. Then we have a history for rollback, for example to a previous version, and we can understand by query what needs to be translated, what contains an outdated translation.

Add this to our translation roadmap as well. It is important that you translate this prompt and add it to the roadmap as it is so that the context of the idea is not lost. And think about how to implement it.

Follow principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices. Follow UI/UX: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design. Use Best Practices.

---

### 20) Updated Checklist (incremental)

1. Models [completed]
   - `NodeTranslation`, `CommentTranslation` with `source_hash`
   - `updated_at` added to `node` and `comment`
   - Optional `content_event` for audit/history [pending]

2. Repositories [pending]
   - Fetch missing/stale for (nodes, comments, lang)
   - Upsert many translations

3. Services [updated]
   - DeepL adapter; batch translate [completed]
   - Libre/MyMemory adapters with guards [completed]
   - Gemini adapter (LLM): prompt, batching, cost-safety [planned]
   - Hooks: on create/update node/comment → enqueue refresh for known langs

4. API/CLI [updated]
   - Stats endpoint [completed]
   - Translate endpoint [completed]
   - CLI command `flask translate-project --project <id> --lang en --stale` [completed]

5. UI [completed]
   - Toggle implemented for nodes/comments (display); diagnostics/panel [pending]
   - Diagnostics button added: GET `/projects/{id}/translation/stats`

6. Tests [pending]
   - Staleness logic; hooks; endpoint behavior



