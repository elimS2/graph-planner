## Graph Planner Roadmap (Flask + Light SQL)

Status: Draft
Owner: Team
Last Updated: 2025-08-30T01:28:11Z

---

### Initial Prompt (translated to English)

Please analyze our task and project deeply and decide how best to implement it.

Create a detailed, step-by-step implementation roadmap in a separate document file. We have a folder docs/features for this. If there is no such folder, create it. Capture in the document all discovered and tried problems, nuances, and solutions as much as possible. During the implementation of this task, you will use this file as a todo checklist; you will update this file and document what has been done, how it was done, what problems arose, and what decisions were made. For history, do not delete items; you can only update their status and add comments. If during implementation it becomes clear that something needs to be added as tasks – add it to this document. This will help us preserve the context window, remember what has already been done, and not forget to do what was planned. Remember that only the English language is allowed in the code, comments, and project labels. When you write the plan, stop and ask me if I agree to start implementing it or if something needs to be adjusted.

Include this very prompt I wrote in the plan, but translate it into English. You can call it something like "Initial Prompt" in the plan document. This is necessary to preserve the context of the task setting in our roadmap file as accurately as possible without the "broken telephone" effect.

Also include steps for manual testing: what needs to be clicked through in the interface.

Follow the principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.
Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design.
Use Best Practices.

This will be Flask and light SQL.

---

### 1. Problem Statement and Goals

We need a planner for movement and development where goals are points (nodes) and movements/dependencies are directed edges (arrows). Users can:
- Create goals, split them into stages (sub-steps), branch to new subgraphs.
- Track time (calendar duration and effort hours), costs, and team member participation per goal and per edge (if needed).
- Click a goal to open a full-fledged task with description, comments, attachments, and status.
- Zoom the graph with level-of-detail (LOD) so that only significant nodes are visible when zoomed out; details appear when zooming in (Google Maps-like behavior).
- Size/weight of a node should represent its importance (e.g., number of subnodes, effort hours, in-degree/out-degree, or composite score).

Primary objectives:
- Minimum friction MVP: single-node deployable backend (Flask), simple frontend (vanilla/Alpine + Cytoscape.js), SQLite as light SQL.
- Clean extensibility towards Postgres and richer auth/roles later.
- Solid UX for graph creation and editing, plus core tracking (time entries, basic cost entries).

Non-goals for MVP:
- Complex multi-tenant RBAC, SSO, real-time collaboration, and heavy analytics. These are future phases.

---

### 2. Principles and Constraints

- SOLID, DRY, KISS, SoC, Single Level of Abstraction, Clean Code Practices.
- UI/UX: simple, intuitive, consistent, accessible (WCAG-minded), responsive, fast.
- English-only code, identifiers, comments, UI labels.
- Flask application with blueprints and service layers; SQLAlchemy ORM; Alembic migrations.
- Light SQL: SQLite for local/dev; Postgres-ready models and migrations.
- Deterministic API contracts; JSON:API-flavored responses where sensible.
- Logging, basic error handling, and minimal security (session auth or token for MVP).

---

### 3. High-Level Architecture

- Backend: Flask
  - Structure: `app/` with blueprints (`graph`, `tasks`, `tracking`, `users`), `services/`, `repositories/`, `models/`, `schemas/`.
  - ORM: SQLAlchemy; Migrations: Alembic.
  - Validation/serialization: Marshmallow (or pydantic via dataclasses-json if preferred). We'll use Marshmallow for Flask alignment.
  - Auth (MVP): Basic session auth; simple User model. Future: JWT/OAuth.
  - Testing: pytest + coverage; factory boy for fixtures.

- Database: SQLite (dev). Tables optimized for Postgres later (UUIDs, created_at indexes).

- Frontend: Server-rendered Jinja + Alpine.js + Cytoscape.js
  - No heavy build step initially. Single-page graph canvas, modals for CRUD.
  - Cytoscape.js for graph visualization (zoom, pan, style, events).
  - LOD: client-side thresholds based on zoom; future server-side aggregation for huge graphs.

- Static assets: simple Tailwind CDN (or minimal CSS) to keep UI modern without tooling.

---

### 4. Data Model (MVP)

Entities:
- User(id, email, name, role, created_at)
- Project(id, name, description, archived, created_at)
- Node(id, project_id, title, description, status, importance_score, planned_hours, actual_hours, planned_cost, actual_cost, assignee_id, parent_id nullable for hierarchy, created_at)
- Edge(id, project_id, source_node_id, target_node_id, type [dependency/part-of/relates], weight, created_at)
- TimeEntry(id, node_id, user_id, started_at, ended_at, hours, note)
- CostEntry(id, node_id, amount, currency, note, incurred_at)
- Comment(id, node_id, user_id, body, created_at)
- Tag(id, name), NodeTag(node_id, tag_id)

Indexes:
- On `Node(project_id)`, `Edge(project_id)`, `TimeEntry(node_id)`, `Comment(node_id)`, timestamps.

Notes:
- `importance_score` is computed and cached (denormalized) for performance; recalculated on relevant changes.
- `parent_id` enables stages/sub-steps; edges handle arbitrary DAG relationships.

---

### 5. Node Size/Visibility Scoring (LOD)

Composite score per node for rendering and visibility:
- Inputs: total actual/planned hours, degree centrality (in/out degree), number of descendants, number of incident edges, recency of activity, open status.
- Example formula v1 (tunable):
  `score = 0.5*log(1 + total_hours) + 0.2*log(1 + descendants) + 0.2*log(1 + degree) + 0.1*activity_decay`
- LOD behavior:
  - At zoom < Z1: show nodes with score >= T1 (cluster others as group placeholders).
  - At Z1<=zoom<Z2: show medium nodes; optionally collapse child trees.
  - At zoom >= Z2: show all nodes.
  - MVP: purely client-side using Cytoscape viewport zoom and data-driven styles; future: server-side aggregation/tiling if graphs grow large.

---

### 6. API Surface (MVP)

Base path: `/api/v1`

- Auth
  - POST `/auth/login`, POST `/auth/logout`

- Projects
  - GET `/projects`, POST `/projects`, GET `/projects/{id}`, PATCH `/projects/{id}`, POST `/projects/{id}/archive`

- Nodes
  - GET `/projects/{id}/nodes` (query: include=edges, search=, min_score=)
  - POST `/projects/{id}/nodes`
  - GET `/nodes/{id}`
  - PATCH `/nodes/{id}`
  - DELETE `/nodes/{id}`
  - POST `/nodes/{id}/comments`
  - POST `/nodes/{id}/time-entries`
  - POST `/nodes/{id}/cost-entries`

- Edges
  - POST `/projects/{id}/edges`
  - DELETE `/edges/{id}`

- Metrics
  - GET `/projects/{id}/metrics` (precomputed totals, score dist, critical-like path hint)

Response shape:
- JSON objects with `data`, `meta`, `errors[]` (if any). IDs as strings.

---

### 7. UI Flows (MVP)

- Graph Canvas
  - Toolbar: Add Node, Add Edge, Select, Pan, Zoom In/Out, Fit.
  - Sidebar: Node details (title, description, status, assignee, hours, cost, comments pane, time tracking add form).
  - Modal dialogs for create/edit node and edge.
  - LOD: Nodes smaller/hidden based on zoom; significant nodes persist.

- Task View (Node details)
  - Comment thread, time entries list, cost entries list.
  - Quick actions: Start timer (manual), Add time entry, Change status.

---

### 8. Roadmap and Checklist

Phases are incremental; do not delete items—update status and add notes.

#### Phase 0 — Project Bootstrap
- [x] Choose stack versions (Flask, SQLAlchemy, Alembic, Marshmallow, Cytoscape.js, Alpine.js, Tailwind CDN).
- [x] Create Flask app skeleton (config, blueprints, error handlers, logging).
- [x] Setup SQLAlchemy models and Alembic.
- [x] Basic auth (session) and User model.
- [x] Seed script for demo data.

Notes/Issues:
- N/A

#### Phase 1 — Core Graph CRUD
- [x] Models: Project, Node, Edge, Comment, TimeEntry, CostEntry, Tag.
- [x] Repositories and services with unit tests.
- [x] API endpoints for CRUD (projects/nodes/edges).
- [x] Jinja template with Cytoscape.js canvas; render graph from API.
- [x] Create/edit/delete node and edge from UI.

Notes/Issues:
- Graph layout: use Cytoscape `cose-bilkent` or `breadthfirst` as default; allow manual drag.

#### Phase 2 — Task Details and Tracking
- [x] Sidebar task panel with add forms (comment/time/cost) in project.html.
- [x] TimeEntry/CostEntry add and rollup; recompute `importance_score` on write.
- [x] List comments/time/cost in UI.

Notes/Issues:
- Hours aggregation should be recalculated asynchronously if needed (MVP can be synchronous).

#### Phase 3 — LOD and Metrics
- [x] Client-side zoom-based LOD rules.
- [x] Node sizing/coloring based on score and status.
- [x] Metrics endpoint for project overview.
- [x] Simple critical-path-like hint (longest path by planned hours over DAG subset).

Notes/Issues:
- Detect cycles to avoid path calculations over non-DAG sections.

#### Phase 4 — Usability and Polish
- [x] Keyboard shortcuts (create node, connect, search focus).
- [x] Inline search and filter by status.
- [x] Export/Import (JSON), Screenshot PNG export from canvas.
- [x] Onboarding help overlay.
- [x] Persist node positions and use preset layout if available.

Notes/Issues:
- Large graph performance tuning: style throttling, request debouncing.

#### Phase 5 — Persistence and Deployment
- [x] Config profiles (dev/prod), env vars, logging.
- [x] SQLite file path and backups; Postgres migration path documented.
- [x] Dockerfile (optional), simple deployment guide.

#### Migrations
- [x] Alembic baseline migration and upgrade applied.
#### Phase 6 — Compound Nodes (Groups)
- [x] Data model: `Node.is_group` flag, persisted positions via `NodeLayout`.
- [x] API: `POST /projects/{id}/groups`, `POST /groups/{group_id}/ungroup`.
- [x] Status aggregation for parents based on children.
- [x] UI: multi-select, Group/Ungroup buttons, double-click collapse/expand.
- [x] Collapsed icon: centered dice-5 (5 dots), color by aggregated status.
- [x] Icon shown only when collapsed; hidden when expanded.
- [x] Auto-collapse initialization and persistence in `localStorage`.
- [x] Restore group node coordinates on load; keep after collapse/expand.
- [x] ID normalization to strings; LOD excludes children when collapsed.


Notes/Issues:
- N/A

---

### 9. Manual Testing Scenarios (MVP)

Basic flows to click through:

1) Project creation
- Open Home → click "New Project" → enter name/description → Save.
- Expect redirect to empty graph view.

2) Create first goals and connect
- Click "+ Node" → enter title/description → Save.
- Repeat for a second node.
- Click "Connect" → select source then target → Save edge.
- Pan/zoom; verify LOD hides tiny nodes when zoomed out.

3) Edit node and task details
- Click a node → sidebar opens.
- Change status to "In Progress", set planned hours, assignee.
- Add comment → check it appears with timestamp.

4) Track time and costs
- In sidebar → "Add Time Entry" → enter hours/note → Save.
- Verify node shows updated totals.
- Add cost entry → check totals and currency formatting.

5) Branch and stages
- Create a child node via "Add Sub-step" from node menu.
- Verify parent/child relation; layout updates.

6) Delete and undo safeguard
- Delete an edge → confirm it disappears.
- Try deleting a node with children → app asks to confirm.

7) Metrics overview
- Open Project metrics → verify totals of hours, costs, top nodes by score.

8) Persistence
- Reload page → data persists.

9) Accessibility basics
- Navigate with keyboard on toolbar and sidebar.
- Verify focus outlines and ARIA labels for key controls.

---

### 10. Risks and Mitigations

- Large graphs performance → Start with client-only LOD; add server-side tiling if needed.
- Data integrity with edges → DB constraints and cascade rules; cycle detection on certain operations.
- Overcomplicated UI → Keep MVP minimal: few buttons, consistent patterns, progressive disclosure.
- Time/cost tracking complexity → Start with manual entries; integrate timers later.
- SQLite concurrency → Fine for dev/small teams; document Postgres upgrade path early.

---

### 11. Definition of Done (MVP)

- Users can create/edit/delete nodes and edges within a project.
- Each node can store task details, comments, time entries, and cost entries.
- Graph is zoomable/pannable with basic LOD and node sizing by score.
- Totals and metrics visible at project level.
- API covered by unit tests for services/repositories; smoke tests for endpoints.
- Basic auth and persistence across sessions.

---

### 12. Implementation Details

Libraries (proposed):
- Backend: Flask, SQLAlchemy, Alembic, Marshmallow, Flask-Login (or Flask-Security-Too minimal), python-dotenv, pytest.
- Frontend: Cytoscape.js (+ cose-bilkent layout), Alpine.js, Tailwind via CDN.

Coding standards:
- Type hints for Python.
- Service layer contains business logic; blueprints are thin.
- Avoid deep nesting; use guard clauses; handle errors explicitly.

Logging & errors:
- Structured logs (JSON in prod), request IDs, centralized error handler returning JSON errors.

---

### 13. Database Schema (DDL Sketch)

Note: Alembic will generate migrations; this is a conceptual sketch.

```sql
-- ids may be TEXT (UUID) in SQLite; in Postgres use UUID type
CREATE TABLE user (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'user',
  created_at TEXT NOT NULL
);

CREATE TABLE project (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  archived INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);

CREATE TABLE node (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'todo',
  importance_score REAL NOT NULL DEFAULT 0,
  planned_hours REAL NOT NULL DEFAULT 0,
  actual_hours REAL NOT NULL DEFAULT 0,
  planned_cost REAL NOT NULL DEFAULT 0,
  actual_cost REAL NOT NULL DEFAULT 0,
  assignee_id TEXT REFERENCES user(id),
  parent_id TEXT REFERENCES node(id) ON DELETE SET NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE edge (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  source_node_id TEXT NOT NULL REFERENCES node(id) ON DELETE CASCADE,
  target_node_id TEXT NOT NULL REFERENCES node(id) ON DELETE CASCADE,
  type TEXT NOT NULL DEFAULT 'dependency',
  weight REAL NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);

CREATE TABLE time_entry (
  id TEXT PRIMARY KEY,
  node_id TEXT NOT NULL REFERENCES node(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES user(id),
  started_at TEXT,
  ended_at TEXT,
  hours REAL NOT NULL,
  note TEXT
);

CREATE TABLE cost_entry (
  id TEXT PRIMARY KEY,
  node_id TEXT NOT NULL REFERENCES node(id) ON DELETE CASCADE,
  amount REAL NOT NULL,
  currency TEXT NOT NULL DEFAULT 'USD',
  note TEXT,
  incurred_at TEXT NOT NULL
);

CREATE TABLE comment (
  id TEXT PRIMARY KEY,
  node_id TEXT NOT NULL REFERENCES node(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES user(id),
  body TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE tag (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE node_tag (
  node_id TEXT NOT NULL REFERENCES node(id) ON DELETE CASCADE,
  tag_id TEXT NOT NULL REFERENCES tag(id) ON DELETE CASCADE,
  PRIMARY KEY (node_id, tag_id)
);
```

---

### 14. API Contract (Examples)

Create Node (request):
```json
{
  "title": "Design MVP",
  "description": "Prepare wireframes and data model",
  "status": "todo",
  "planned_hours": 12,
  "assignee_id": "<user-id>",
  "parent_id": null
}
```

Create Node (response):
```json
{
  "data": {
    "id": "<uuid>",
    "project_id": "<uuid>",
    "title": "Design MVP",
    "status": "todo",
    "importance_score": 0.0
  },
  "meta": {}
}
```

List Graph (response excerpt):
```json
{
  "data": {
    "nodes": [{"id": "n1", "title": "A", "score": 1.2, "status": "todo"}],
    "edges": [{"id": "e1", "source": "n1", "target": "n2", "type": "dependency"}]
  },
  "meta": {"count_nodes": 42, "count_edges": 58}
}
```

---

### 15. Next Iteration Backlog

- Auth UI: login/logout page, current user in header; protect write ops.
  - [x] Minimal Auth UI added in headers of `index.html` and `project.html` (Login/Logout, current user via `/api/v1/auth/me`).
  - [x] All write endpoints in `app/blueprints/graph/routes.py` protected with `@login_required` (projects/nodes/edges/comments/time/cost/groups/position).
  - [x] Client now shows a friendly "Login required" alert on 401 responses.
  - [ ] Replace prompt-based login with proper form/modal and validation.
- Roles & Permissions: admin/user; limit node/edge edits for non-admins.
- Tags & Filters: tag CRUD, filter by tag/assignee/status; quick tag add.
- Saved Views: persist viewport, filters, selection; list of saved views.
- Attachments: upload/download (local dev storage), show in node panel.
- Import/Export v2: CSV import, richer JSON (mappings), progress feedback.
- Performance: debounced requests, batch updates, list virtualization.
- Testing: API auth smoke; basic Playwright e2e for UI flows.

- Compound Nodes (Multi-node groups): DONE in Phase 6.

#### Added — Web UI: Create Board (Project)
- [x] Home page lists boards and provides a form to create a new one
- [x] "Create & Open" button redirects to `/projects/{id}` after creation
- [x] Uses `/api/v1/projects` POST endpoint

- Node Status Management:
  - Status vocabulary (English): `planned` (default), `in-progress`, `done`, `blocked`.
  - API: allow PATCH `/nodes/{id}` with `status`; optional bulk update.
  - UI: status selector in sidebar; color coding already mapped; add filter by status (done).
  - Group aggregation: parent/group status derived from children (priority: blocked > in-progress > planned > done) for color.

---

### 16. Future Enhancements

- Real-time collaboration (WebSocket) and presence.
- Advanced RBAC, SSO, audit logs.
- Attachments storage (S3/Blob) and previews.
- Auto-layout presets, saved viewpoints, roadmap timelines.
- Import from Jira/Asana; export to CSV.
- Server-side LOD and clustering for very large graphs.

---

### 17. Change Log (keep appending)

- [x] 2025-08-28 — Document created. Initial draft.
- [x] 2025-08-28T23:07:38Z — Last Updated set via MCP.
- [x] 2025-08-28T23:12:26Z — Phase 0: versions chosen, Flask skeleton created.
- [x] 2025-08-28T23:16:46Z — Alembic configured; models scaffolded.
- [x] 2025-08-28T23:28:41Z — Repositories/services implemented; tests passed.
- [x] 2025-08-28T23:33:11Z — CRUD API for projects/nodes/edges added.
- [x] 2025-08-28T23:41:41Z — Node/edge create-edit-delete implemented in UI.
- [x] 2025-08-29T08:03:38Z — Node positions persistence and preset layout added.
- [x] 2025-08-29T11:14:30Z — Compound nodes UX: dice-5 icon with transparent background, show only when collapsed; robust collapse/expand with persisted state; string IDs normalization; saved coordinates for groups respected; LOD ignores hidden children.
 - [x] 2025-08-29T14:27:31Z — Home UI for creating boards (projects): list existing, create form, Create & Open action.
 - [x] 2025-08-30T01:08:51Z — Auth MVP: protected write endpoints with login_required; login/logout UI in headers; 401 handling in client; roadmap updated.
 - [x] 2025-08-30T04:13:30Z — Board rename via PATCH /api/v1/projects/{id}; Rename buttons in project header and boards list.
 - [x] 2025-08-30T04:20:00Z — New nodes appear at viewport top-left; position persisted via /nodes/{id}/position.
 - [x] 2025-08-30T04:25:00Z — Edge direction arrows clarified (triangle heads, hover/selected emphasis).
  - [x] 2025-08-30T01:28:11Z — Arrow styles tuned: smaller arrowheads and lighter hover/selected thickness.


