## Graph Planner — Translation Feature Roadmap (Node Title Localization)

Status: Draft
Owner: Team
Last Updated: 2025-08-30T11:11:54Z

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

- Provider: DeepL API (`deepl`), because quality > cost. Keep interface open for Google/Azure.
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
  - `GoogleProvider` (future)
  - `AzureProvider` (future)
  - `LibreProvider` (optional self-hosted)

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
- `TRANSLATION_PROVIDER=deepl`
- `DEEPL_API_KEY=...`
- Timeouts: `TRANSLATION_TIMEOUT_MS=60000`
- Rate: `TRANSLATION_BATCH_SIZE=50`

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

2. Provider layer [pending]
   - Add `app/services/translation.py` with DeepL client (env key)
   - Batch translate with retry/backoff

3. API [pending]
   - POST `/projects/{id}/translate` (server-only translate, cache)
   - GET `/nodes/{id}/translations`
   - Optional: extend `GET /projects/{id}/nodes?lang=en` to include `title_translated`

4. UI [pending]
   - Toolbar toggle `Show English`
   - When on: fetch nodes with translations (or fetch translations and map client-side)
   - Loading/error toasts; re-render labels

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


