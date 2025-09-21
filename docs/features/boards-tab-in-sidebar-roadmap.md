## Boards Tab in Sidebar — Roadmap

Timestamp (UTC): 2025-09-21T01:02:41.350218+00:00

### Initial Prompt (translated)

We have a sidebar with tabs: Task Panel, Settings, Actions. Add another tab there called "Boards"; it will display boards from the page at `http://127.0.0.1:5050/`.

— Analyze the task and the project in depth and decide how to implement it best.

— Create a detailed, step-by-step roadmap in a separate document under `docs/features`. If such a folder does not exist, create it. Document all identified and tried issues, nuances, and solutions. During implementation, use this file as a todo checklist, update it, and record what was done, how it was done, problems encountered, and decisions taken. For history, do not delete items; only update their status and comment. If new subtasks emerge, add them to this document. This will help us keep context. Remember that in the code and comments, only English is allowed.

— After writing the plan, stop and ask me whether I agree to start implementing it or if something needs adjustment.

— Also include manual testing steps (what to click in the UI).

— Follow SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices. Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design. Use Best Practices.

---

### Context & Current State

- Primary graph workspace template: `app/templates/project.html`.
- Sidebar exists with tab buttons: `Task`, `Actions`, `Settings`.
  - Buttons: `#tabTask`, `#tabActions`, `#tabSettings`.
  - Panels: `#taskPanel`, `#actionsPanel`, `#settingsPanel`.
  - Tab logic implemented inline in `project.html` with functions: `showTask()`, `showActions()`, `showSettings()`, `resetTabStyles()`, `hideAllPanels()`; active tab stored in `localStorage` under key `sidebarTab`.
- Homepage at `/` (template `app/templates/index.html`) lists boards (projects) with API calls:
  - `GET /api/v1/projects` → array of boards.
  - `POST /api/v1/projects` → create board.
  - `PATCH /api/v1/projects/:id` → rename board.
  - Links to open a board: `/projects/:id` (renders `project.html`).
- Goal: add a new tab `Boards` to the sidebar in `project.html` to display boards similarly to the homepage.

### Goals

- Add a fourth tab button `Boards` next to existing tabs.
- Add `#boardsPanel` section that displays a concise list of boards fetched from `/api/v1/projects`.
- Keep UI consistent with existing Tailwind styling and sidebar patterns (collapsible sections, scrollable area, localStorage for active tab).
- Handle loading/empty/error states gracefully, with minimal but clear feedback.

### Non-Goals (for MVP)

- Creating/renaming/deleting boards within the sidebar (can be future scope).
- Complex filtering, sorting, or pagination (simple list is sufficient for now).
- Cross-page shared state management; logic remains local to `project.html`.

### UX Design

- Add tab button:
  - Label: `Boards`.
  - Visual state styling mirrors other tabs (active: dark, inactive: light).
- Panel content (`#boardsPanel`):
  - Header: "Boards" (small, consistent with panel headings).
  - Body: list of boards with each item showing:
    - Board name as a link to `/projects/{id}` (opens the selected board).
    - Optional subtle timestamp (created_at) if available.
    - Optional small "Open →" link mirroring `index.html` for familiarity.
  - States:
    - Loading: small text "Loading…".
    - Empty: "No boards yet." with a link to `/` for creating.
    - Error: small red text with retry button.
- Accessibility:
  - Buttons as `<button>`; links as `<a>`.
  - Focus styles preserved (Tailwind defaults) and logical tab order.
  - ARIA labels for the panel header if necessary.

### Technical Design

- HTML (in `app/templates/project.html`):
  - Add `<button id="tabBoards">Boards</button>` alongside existing tab buttons.
  - Insert `<div id="boardsPanel" class="hidden">…</div>` in the sidebar after `#taskPanel` and before/after others per structure, matching spacing classes.
- JavaScript (inline in `project.html` near other tab functions):
  - Declare refs: `const tabBoards = document.getElementById('tabBoards');` and `const boardsPanel = document.getElementById('boardsPanel');`.
  - Extend helpers:
    - `resetTabStyles()` sets `tabBoards` to inactive style.
    - `hideAllPanels()` hides `boardsPanel`.
  - Add `function showBoards(){ … }` that:
    - Calls `hideAllPanels()`; shows `boardsPanel`.
    - Updates button styles (active state) and saves `localStorage.setItem('sidebarTab', 'boards')`.
    - Lazy-loads boards once: if not loaded, fetch `/api/v1/projects` and render list into `#boardsList`.
    - Handles `401/403` by showing a login hint (link to `/`).
  - Wire tab click listeners: `tabBoards?.addEventListener('click', showBoards)`.
  - On initial load, extend the existing logic that restores the last tab from `localStorage` to recognize `boards`.
- Rendering strategy:
  - Build simple DOM nodes via `innerHTML` or small helper—stay consistent with existing code style in `project.html` (which uses plain JS DOM + Tailwind classes).
- State & performance:
  - Cache fetched boards in a local variable to avoid refetch on each tab switch; provide a small "Refresh" button to re-fetch on demand.
  - Limit list rendering to first N (e.g., 100) if many boards; show count.

### API & Data Contracts

- `GET /api/v1/projects`
  - Response: `{ data: Array<{ id: number|string, name: string, created_at?: string }> }`.
  - Error handling: display a small error banner inside `#boardsPanel` and a retry button.

### Error Handling & Edge Cases

- Network error or non-OK status: show compact error with retry.
- Unauthorized (401): show hint "Login to view boards" with link to `/`.
- Empty array: display "No boards yet. Create on Home" with link to `/`.
- Very long names: use `truncate` classes and `title` attribute for full name.

### Security & Privacy

- No elevated permissions; data is same as homepage.
- Avoid leaking sensitive info; display only `name`, `id`, and optional `created_at`.

### Accessibility (A11y)

- Provide clear focus styles for tab and links.
- Use semantic elements: `<button>` for tab, `<a>` for navigation.
- Ensure color contrast by reusing existing palette.

### Performance Considerations

- Fetch boards only once per page session or on explicit refresh.
- Avoid heavy DOM operations; use document fragments if list is large.

### Implementation Steps (Checklist)

Status legend: [ ] pending, [x] done, [~] in progress

1. [x] Add `Boards` tab button in `project.html` sidebar header.
2. [x] Add `#boardsPanel` container with basic layout (header, content area).
3. [x] Extend tab controller JS: refs, `resetTabStyles`, `hideAllPanels`, add `showBoards`.
4. [x] Implement lazy data loading from `/api/v1/projects` with loading/empty/error states.
5. [x] Render list items with name link and add "Refresh" button. Decision: removed `created_at` and `Open` control per stakeholder request.
6. [x] Integrate localStorage restore to include `boards`.
7. [ ] A11y sweep (focusable controls, titles, aria where needed).
8. [ ] Visual pass for consistent spacing/typography with other panels.
9. [x] Manual test: verified by stakeholder; behavior confirmed working.
10. [ ] Code review and minor refactors to keep KISS/DRY.

### Manual Test Plan (UI click-through)

Preconditions: Have at least one board in the system. Also test with zero boards.

- Sidebar Tab Switching
  - Open `/projects/{someId}`.
  - Click `Boards` tab → `boardsPanel` becomes visible, others hidden.
  - Switch between `Task`, `Actions`, `Settings`, `Boards` and ensure styles and visibility are correct.
  - Reload page; last selected tab persists (including `Boards`).

- Data Loading
  - First time opening `Boards`: shows "Loading…" then boards list.
  - Simulate error (temporarily disconnect or mock): shows error text and `Retry` triggers reload.

- Content Rendering
  - Each board shows name as link to `/projects/{id}`; click navigates successfully.
  - Long names are truncated visually but full name available via tooltip (`title`).
  - Empty state: shows "No boards yet" and link to `/` for creation.

- Auth States
  - Logged out: `Boards` shows login hint or link to `/`; no crash.
  - Logged in: boards list loads.

- Refresh
  - Click `Refresh`: re-fetches and updates list without duplicate items.

### Risks & Mitigations

- Large number of boards causing slow render
  - Mitigation: cap render count or virtualize later if needed.
- API 401/403 in project view
  - Mitigation: friendly message with navigation to `/` login/creation.
- UI inconsistency across tabs
  - Mitigation: reuse existing Tailwind classes and patterns from current tabs.

### Open Questions for Stakeholder

- Should the `Boards` panel allow creating/renaming/deleting boards, or remain read-only for MVP?
- Should we display only recent boards (e.g., last 20) or the full list?
- Do we need search/filter inside the `Boards` panel now, or later?

### Rollout & Future Enhancements

- Phase 1 (MVP): read-only list + open links + refresh.
- Phase 2: quick actions (create, rename) and search.
- Phase 3: recent boards, favorites, and per-user pinning.

### Acceptance Criteria (MVP)

- A `Boards` tab is visible and styled consistently in the sidebar of `project.html`.
- Clicking `Boards` shows a list of boards loaded from `/api/v1/projects`.
- Loading, empty, and error states are handled.
- LocalStorage remembers the `Boards` tab when reloading.
- No regression in existing `Task`, `Actions`, and `Settings` tabs.

### References

- Templates: `app/templates/project.html`, `app/templates/index.html`.
- API: `GET /api/v1/projects`.
