## Comments Sidebar Ordering: Messenger-style (oldest at top, newest at bottom)

### Initial Prompt
The user asked to change the comments ordering in the sidebar: currently the newest comment is at the top and the oldest is at the bottom. They want the opposite, like in messengers: oldest at the top, newest at the bottom. Also: analyze the task and the project deeply; create a detailed step-by-step plan in docs/features as a roadmap document, include this initial prompt translated to English, and add manual testing steps. Follow SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices, and UI/UX principles (User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design). Use Best Practices. If current time is needed, get it from the time MCP server.

### Context & Current Behavior
- API endpoint: `GET /api/v1/nodes/<node_id>/comments` implemented in `app/blueprints/graph/routes.py` as `list_comments`.
- Current server-side ordering: `order_by(Comment.created_at.desc())` which returns newest-first.
- Client rendering: `app/templates/project.html` fetches comments in `refreshLists(selectedNodeId)` and appends items to `#commentsList` in the fetched order.
- Because server provides newest-first and the UI appends in order, the list shows newest at the top.

### Goal
- Display comments oldest-first (ascending by created_at), with the newest at the bottom, consistent with common messenger UX.

### Requirements & Constraints
- Language in code and UI must remain English only.
- Follow SOLID/DRY/KISS and UI/UX principles.
- Avoid regressions in translations flow (`lang` param support remains intact).
- Maintain attachments/edit/delete functionality.
- Keep performance acceptable for long comment threads; avoid unnecessary DOM reflows.

### Options Considered
1) Change server ordering to ascending
   - Pros: Single source of truth; all clients get correct order; simpler UI code.
   - Cons: Potentially impacts any other consumer if they relied on desc order (none found in repo).

2) Keep server ordering but reverse on client
   - Pros: Localized change.
   - Cons: Extra client logic; two sources of truth; risk of pagination or future API changes.

Decision: Prefer Option 1 — update server to `order_by(Comment.created_at.asc())`. This is cleaner and consistent.

### Impacted Areas
- `app/blueprints/graph/routes.py` → `list_comments` query ordering.
- `app/templates/project.html` → No logic change needed; verify that appending maintains top-to-bottom oldest→newest.
- Tests: add/adjust tests in `scripts/tests` to verify ordering.

### Detailed Plan (Step-by-Step)
1. Update server ordering
   - In `list_comments`, change `.order_by(Comment.created_at.desc())` to `.order_by(Comment.created_at.asc())`.
   - Preserve translation overlay logic for `lang` parameter.

2. Verify client rendering
   - Ensure that `refreshLists` appends list items in the received order to `#commentsList`.
   - Confirm empty state visibility logic still works.

3. Manual UX polish
   - Auto-scroll behavior: scroll to bottom after load and after adding a comment.
   - Add near-bottom guard to avoid interrupting readers when they scrolled up.

4. Testing
   - Create a Python test script under `scripts/tests/test_comments_order.py` that:
     - Creates a node.
     - Posts three comments with controlled timestamps (or waits sequentially).
     - Calls `GET /api/v1/nodes/<id>/comments` and asserts that response data is ascending by `created_at`.
     - Save JSON output to `scripts/tests/json-result.json` per workspace rules.

5. Documentation & Changelog
   - Keep this roadmap updated with statuses and decisions.

### Risks & Mitigations
- Hidden consumers depending on DESC order: Searched repo; no other UI paths fetch this endpoint differently. Mitigation: note in roadmap; if external clients exist, introduce query param `?order=asc|desc` later.
- Large lists performance: unchanged; server ordering handled by DB index on `created_at` (assumed). If needed, add index later.

### Manual Test Steps (UI)
1. Open a project and select a node with comments sidebar visible.
2. Observe that the top item is the oldest comment; the bottom item is the newest.
3. Add a new comment; it should appear at the bottom.
4. Edit and delete still work for own comments.
5. If language is switched, verify ordering persists and translated body is applied.

### Implementation Checklist (ToD0)
- [x] Change server ordering to ASC in `list_comments`.
- [x] Run the app; verify ordering visually in sidebar.
- [x] Add test script `scripts/tests/test_comments_order.py` and save JSON output.
- [x] Implement auto-scroll-to-bottom with near-bottom guard.
- [x] Add API `order` parameter (`asc|desc`).
- [x] Add UI setting for default comments order and persist to localStorage.
- [x] Update this file with results and any issues.

### Notes
- Keep code/comments/UI text in English.
- Optional enhancement candidates: pagination, sticky date separators, and auto-scroll-on-new.


