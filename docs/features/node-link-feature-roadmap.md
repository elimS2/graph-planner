### Node Link (URL) Feature Roadmap

Status: Draft
Owner: Team
Last Updated: 2025-08-31

---

### Initial Prompt (translated to English)

I want a node to have a property "Link". In the task panel, you can provide a URL in a field. Then, on the board, the node text will be displayed as a link, and when clicking the node while holding the Ctrl key, the link will open in a new window.

=== Analyse the Task and project ===

Deeply analyze our task and our project and decide how best to implement this.

=== Create Roadmap ===

Create a detailed, step-by-step implementation plan for this task in a separate document file. We have a folder docs/features for this. If there is no such folder, create it. Capture in the document all discovered and tried problems, nuances, and solutions as much as possible. As you progress, you will use this file as a todo checklist, updating it and documenting what has been done, how it was done, what problems arose, and what decisions were made. For history, do not delete items; only update their status and comment. If during implementation it becomes clear that something needs to be added, add it to this document. This will help us preserve context, remember what was done, and not forget what was planned. Remember that only the English language is allowed in the code, comments, and project labels. When you write the plan, stop and ask me if I agree to start implementing it or if something needs to be adjusted.

Also include steps for manual testing, i.e., what to click through in the interface.

=== SOLID, DRY, KISS, UI/UX, etc ===

Follow the principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.
Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design.
Use Best Practices.

---

### 1) Current State Analysis

- Backend
  - Models: `app/models/__init__.py` defines `Node` without a link field. Marshmallow `NodeSchema` also lacks a link field.
  - API: `app/blueprints/graph/routes.py` exposes CRUD for nodes; `GET /projects/{id}/nodes` returns nodes; `PATCH /nodes/{id}` updates arbitrary node fields via schema validation.
  - Migrations exist (Alembic), e.g., `migrations/versions/*`. Adding a new optional column is straightforward.

- Frontend (project board UI)
  - Template: `app/templates/project.html` uses Cytoscape.js. Nodes are created from `toElements(graph)` using server-provided node payload.
  - Task Panel: shows node title with inline edit, status, priority, comments/time/cost blocks. There is currently no URL field.
  - Interaction: `cy.on('tap','node', ...)` selects nodes. Keyboard shortcuts present. No special behavior for Ctrl+click.

- Constraints/Notes
  - Cytoscape labels are not HTML elements; we cannot render an actual `<a>` tag inside the graph label. We can:
    - Open a URL on Ctrl+click if a node has a link.
    - Visually indicate link presence (e.g., blue label color, optional small ↗ marker) to mimic a hyperlink.
  - We must sanitize/validate URLs; forbid `javascript:` and other unsafe schemes. Use `rel="noopener noreferrer"` when opening.

Conclusion: Add an optional `link_url` field to `Node` and `NodeSchema`, handle it in create/update and list, expose to client. In UI, add a "Link URL" input in Task Panel; when present, show the node label in blue and open in new tab on Ctrl+click.

---

### 2) Data Model Changes

- Add column `Node.link_url: Optional[str]` (nullable, length not strictly limited by SQLite; logically cap at ~1024).
- Alembic migration to add the column with `nullable=True` and no default.
- Backfill: none needed.

---

### 3) API and Serialization Changes

- Update `NodeSchema` to include `link_url = fields.String(allow_none=True)`.
- `POST /api/v1/projects/{id}/nodes` should accept `link_url` (optional).
- `PATCH /api/v1/nodes/{id}` should allow updating `link_url`.
- `GET /api/v1/projects/{id}/nodes` and `GET /api/v1/nodes/{id}` should include `link_url` in payload.
- Validation:
  - Server-side: simple URL validation (scheme whitelist: http, https, mailto, ftp). Reject unsafe schemes and overly long values.
  - Trim whitespace; empty string treated as null.

---

### 4) Frontend/UI Changes (Cytoscape + Task Panel)

- Task Panel (`app/templates/project.html`):
  - Add a new input field under Title: label "Link URL" and an input box.
  - On node select: populate the field with `link_url`.
  - On blur or Enter: `PATCH /api/v1/nodes/{id}` with `{ link_url }` (empty => null).
  - Add a small helper text: "Ctrl+Click node to open in new tab" when a link is set.

- Graph behavior:
  - Include `link_url` in `toElements(graph)` as `data.link_url` for each node.
  - Enhance `cy.on('tap', 'node', ...)`: if `evt.originalEvent?.ctrlKey` and a non-empty, valid `link_url` exists, call `window.open(url, '_blank', 'noopener,noreferrer')` and return early to avoid interfering with selection.
  - Visual cue: style nodes with `data.link_url` by changing label color to blue (`color: '#1d4ed8'`). Underline is not natively supported, so color cue + optional label suffix `↗` is sufficient. Optionally add a class, e.g., `node[link_url]` selector, to keep styling declarative.

- Help/Onboarding:
  - Update Help alert text to mention: "Ctrl+Click a node with Link URL opens it in a new tab."

Accessibility/UX:
  - Keep primary activation as Ctrl+click to avoid accidental navigation.
  - Cursor remains default; selection works on normal click. Provide feedback via color.

---

### 5) Import/Export and JSON

- Update Export JSON to include `link_url` for nodes.
- Update Import JSON to read `link_url` when present.

---

### 6) Security and Validation

- Sanitize/validate URL server-side:
  - Normalize empty string to `None`.
  - Allow schemes: `http`, `https`, `mailto`, `ftp`.
  - Reject strings starting with `javascript:` or containing control characters.
- Client-side: lightly validate and show a small red border on obvious invalid entries (non-blocking, authoritative check is server-side).
- Use `noopener,noreferrer` when opening to prevent tab-napping.

---

### 7) Step-by-Step Implementation Plan (Checklist)

- [x] Backend: Add `link_url` column to `Node` model. (Done in app/models/__init__.py)
- [x] Backend: Create Alembic migration: add nullable `link_url` to `node` table. (Done in migrations/versions/a1f2c3d4e5b6_add_link_url_to_node.py)
- [x] Backend: Extend `NodeSchema` with `link_url`. (Done in app/schemas/__init__.py)
- [x] Backend: Update node create/update flows to accept and validate `link_url`. (Done in app/blueprints/graph/routes.py)
- [ ] Backend: Unit tests for schema validation and CRUD covering `link_url`.
- [x] Frontend: In `project.html`, add "Link URL" input in Task Panel with blur/Enter save. (Done)
- [x] Frontend: Include `link_url` in `toElements(graph)` and initial load. (Done)
- [x] Frontend: Add Ctrl+click handler to open `link_url` in new tab. (Done)
- [x] Frontend: Styling cue for nodes with links (blue label), update Help text. (Done; per-node hint under Link URL)
- [x] Frontend: Update Export/Import to include `link_url`. (Done; import passes link_url to create API)
- [x] Frontend: Add toggle (Open in new tab) stored in localStorage; Ctrl+Click respects it. (Done)
 - [x] Backend/Frontend: Persist per-node link target (`link_open_in_new_tab`) in DB; checkbox updates via PATCH; Ctrl+Click uses node-level flag. (Done)
- [ ] E2E/manual test pass.

Notes:
- Keep code in English; reuse existing helper methods (`patchJSON`, selection handlers) to stay DRY.
- Small, focused edits to avoid regressions.

Update 2025-08-31:
- Added `link_url` field to `Node` model. Until the migration is applied, existing databases will not have this column — next step is to create and apply Alembic migration before running the server.
- Created Alembic migration to add `link_url`. Apply migrations before running to avoid runtime errors when accessing `link_url`.
- Extended `NodeSchema` to serialize/accept `link_url`.
- API now normalizes and validates `link_url` on create/update (schemes: http/https/mailto/ftp). Returns 400 for invalid inputs.
- UI: Task Panel includes Link URL input; saves on blur/Enter. Graph data includes `link_url`; nodes with `link_url` are blue; Ctrl+click opens link safely. A hint appears under the input when a link is set.
- Export/Import: export already includes schema fields; import now forwards `link_url` when creating nodes.
- Added a checkbox in Task Panel to choose whether links open in a new tab. Preference persisted in localStorage.
 - Per-node preference `link_open_in_new_tab` added to DB, schema, API and UI; overrides localStorage for that node.

---

### 8) Detailed Engineering Notes

- Model/Schema
  - Column definition: `link_url = mapped_column(db.String, nullable=True)`.
  - In `NodeSchema`: `link_url = fields.String(allow_none=True)`.
  - Validation helper in the patch route (or `schemas` level via `validate`):
    - Strip whitespace; if `''` => None.
    - Check scheme via `urllib.parse.urlparse`.

- Routes adjustments
  - `create_node`: accept `link_url` transparently through schema.
  - `update_node`: after `NodeSchema(partial=True).load(payload)`, perform URL normalization and validation prior to setting.
  - `list_nodes`: `NodeSchema` dump will include `link_url` by default; no extra work.

- Frontend integration
  - Selection handler already updates Task Panel fields; add similar logic for link input.
  - Save on blur/Enter using existing `patchJSON`.
  - Ctrl+click open snippet:
    - Guard on `evt.originalEvent && evt.originalEvent.ctrlKey`.
    - Read `evt.target.data('link_url')`.
    - If present and valid, `window.open(url, '_blank', 'noopener,noreferrer'); return;`.
  - Style: add style selector `{ selector: 'node[link_url]', style: { 'color': '#1d4ed8' } }` alongside existing styles.

- Import/Export
  - Export button currently fetches nodes via API and emits JSON; ensure `link_url` is included (it will be if schema dumps it).
  - Import path: when reading nodes from a file, send `link_url` if present in JSON when creating nodes.

---

### 9) Manual Testing Scenarios (What to click)

1) Add link to an existing node
- Open a project with nodes → Click a node → In Task Panel, enter `https://example.com` into "Link URL".
- Press Enter or blur the field. Expect: server accepts, no error shown.
- Node label turns blue. Help text about Ctrl+click appears below the field.

2) Open link via Ctrl+click
- Hold Ctrl and click the same node in the canvas.
- Expect: new browser tab opens `https://example.com`.

3) Clear link
- Select the node → clear the "Link URL" field → blur or Enter.
- Expect: node label returns to default color; Ctrl+click no longer opens anything.

4) Invalid URL rejection
- Enter `javascript:alert(1)` and Save.
- Expect: server responds 400; client displays an alert (using existing error handling) and reverts value.

5) Import/Export
- Export JSON. Verify nodes include `"link_url": "https://..."` when set.
- Import a JSON file containing nodes with `link_url`. Verify links appear and Ctrl+click works.

6) Regression checks
- Create node, edit title/status/priority, group/ungroup, collapse/expand groups.
- Verify no errors and positions/filters still work.

---

### 10) Risks and Mitigations

- Cytoscape label cannot be a real HTML anchor → Use Ctrl+click + blue label as affordance; document in Help.
- URL safety → Strict scheme whitelist, normalize empty to null, noopener/noreferrer on open.
- UX confusion → Show helper text in Task Panel when a link exists; keep normal click as selection.

---

### 11) Acceptance Criteria

- Node supports an optional `link_url` stored in DB and exposed via API.
- Task Panel allows adding, editing, and clearing the URL.
- Nodes with a link are visually indicated (blue label).
- Ctrl+click on such a node opens the link in a new tab with safe window features.
- Export/Import preserves `link_url`.
- Unit tests for schema/validation pass; smoke tests for UI pass.

---

### 12) Change Log (append-only)

- [ ] 2025-08-31 — Document created. Draft plan for Node Link feature.

---

### 13) Open Questions

- Should we support additional schemes like `tel:` and `sms:`? (Default: not now.)
- Do we need per-language links (localized)? (Default: single link per node.)

---

### 14) Implementation Notes (when executing)

- Commit messages in English (conventional style):
  - feat(node): add link_url field and migration
  - feat(ui): task panel link input and ctrl+click open
  - test(api): cover node link_url validation
  - chore(export): include link_url in export/import


