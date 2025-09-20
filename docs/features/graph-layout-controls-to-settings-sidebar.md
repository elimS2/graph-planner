# Move Graph Layout Controls from Header to Sidebar › Settings

Timestamp (UTC): 2025-09-20T14:41:01.691408+00:00

---

## Initial Prompt (translated to English)

Move the header buttons into the sidebar, into the Settings tab as a separate block. Come up with a good name for this block.

=== Analyse the Task and project ===

Analyze our task and project deeply and decide how best to implement it.

==================================================

=== Create Roadmap ===

Create a detailed, step-by-step implementation plan for this task in a separate file/document. We have a folder docs/features for this. If there is no such folder, create it. Document in this file all discovered and tried problems, nuances, and solutions as much as possible, if any. As we progress implementing this task you will use this file as a todo-checklist, updating it and documenting what is done, how it is done, what issues arose and which decisions were made. For history, do not delete items; you can only update their status and add comments. If, during implementation, it becomes clear that something needs to be added from tasks — add it to this document. This will help us keep the window of context, remember what we have already done and not forget to do what was planned. Remember that only the English language is allowed in code and comments, and project texts. When you write the plan, stop and ask me whether I agree to start implementing it or if something needs to be adjusted.

Include in the plan steps for manual testing — i.e., what to click in the interface.

==================================================

=== SOLID, DRY, KISS, UI/UX, etc ===

Follow the principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices. Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design. Use Best Practices.

==================================================

=== Get time from MCP Server ===

If you need the current time, get it from the time MCP Server.

---

## Context and Current State (discovery)

- Header previously included a grouped toolbar with graph layout controls, wrapped by a container with class `graph-layout-toolbar` in `app/templates/project.html` (now removed after relocation):

```107:137:app/templates/project.html
<div class="inline-flex items-center gap-2 ml-2 px-2 py-1 bg-slate-100 rounded graph-layout-toolbar">
  <label for="layoutMode" class="text-sm text-slate-700">Layout</label>
  <select id="layoutMode" class="border rounded px-2 py-1 text-sm">…</select>
  <select id="layoutAlgo" class="border rounded px-2 py-1 text-sm" title="Algorithm">…</select>
  <label for="layoutPreset" class="ml-2 text-sm text-slate-700">Preset</label>
  <select id="layoutPreset" class="border rounded px-2 py-1 text-sm" title="Preset layout">…</select>
  <button id="btnRunLayout" class="px-2 py-1 text-xs rounded bg-slate-200 text-slate-800">Run</button>
  <button id="btnRefineLayout" class="px-2 py-1 text-xs rounded bg-slate-200 text-slate-800" title="Reduce overlaps and shorten extra-long edges">Refine</button>
  <button id="btnRestoreSaved" class="px-2 py-1 text-xs rounded bg-slate-200 text-slate-800">Restore Saved</button>
  <label for="layoutSpacing" class="ml-2 text-sm text-slate-700">Spacing</label>
  <input id="layoutSpacing" type="range" min="0.8" max="2.4" step="0.1" value="1.2" class="align-middle">
  <span id="layoutSpacingValue" class="text-xs text-slate-600">x1.2</span>
  <button id="btnArrangeNeighbors" class="px-2 py-1 text-xs rounded bg-slate-200 text-slate-800" title="Arrange neighbors of the selected node in a circle">Arrange Neighbors</button>
</div>
```

- Event wiring for these controls is implemented later in the same file in an IIFE `wireLayoutControls()` using the element IDs above. The logic toggles preview mode, runs layouts (e.g., `runSuggestedLayout`), refines, restores, applies spacing, and presets.
- Sidebar exists with tabs `Task`, `Actions`, and `Settings` (`#tabTask`, `#tabActions`, `#tabSettings`) and panels `#taskPanel`, `#settingsPanel` in `project.html`.
- Settings tab initializes collapsible sections via `wireCollapsibleSection(...)`. There is order persistence for Settings blocks using `ORDER_KEYS.settings` and `DEFAULT_SETTINGS_IDS` (includes `lodBlock`, `sizeScalingBlock`, `scheduleBlock`, `serverInfo`, `envBlock`, `visibilityBlock`, `commentsSettingsBlock`, `autoHideBlock`, `autoHideHeaderBlock`, `translationBlock`).
- CSS previously hid `.graph-layout-toolbar` when comments are fullscreen. After moving controls to the sidebar, this rule was removed.

Implications:

- We can move the markup block (keeping the same element IDs) into a new collapsible block within `#settingsPanel` without changing most JS wiring. The existing `wireLayoutControls()` will continue to work by ID.
- We should register the new block within the settings reorder system and persist collapse state, matching current architecture (client-only, localStorage-backed).

## Naming for the New Settings Block

- Proposed title: "Graph Layout" (short, clear, matches existing labels like "Preset", "Algorithm").
- Alternative (if we want broader scope later): "Layout & Arrangement".
- For now, use: Graph Layout.

## Goals

- Relocate all layout controls from header toolbar into a dedicated block on the Sidebar › Settings tab.
- Keep functionality intact (preview mode, run, refine, restore, presets, spacing, arrange neighbors).
- Make the block collapsible, reorderable, and persist its collapsed state.
- Improve UI cleanliness in header; preserve Comments fullscreen behavior without hacks.

Non-goals (now):

- Back-end changes or new APIs.
- Refactoring underlying layout algorithms.
- Changing keyboard shortcuts or adding new ones.

## Detailed Implementation Plan

1) Markup — add new block under Settings panel

- Insert a new block container in `#settingsPanel`:
  - `id="layoutSettingsBlock"` (outer block)
  - Header toggle button `id="layoutSettingsToggle"`; body `id="layoutSettingsBody"`.
  - Title text: "Graph Layout".
  - Move the entire current header toolbar content (children of `.graph-layout-toolbar`) into `#layoutSettingsBody`.
  - Keep the element IDs unchanged (`layoutMode`, `layoutAlgo`, `layoutPreset`, `btnRunLayout`, `btnRefineLayout`, `btnRestoreSaved`, `layoutSpacing`, `layoutSpacingValue`, `btnArrangeNeighbors`).

2) Remove header toolbar

- Delete the `<div class="graph-layout-toolbar">…</div>` from the header area to declutter the top bar.
- Optionally retain a very small link/button in header to quickly jump to Settings › Graph Layout (e.g., a gear icon) — out of scope for now.

3) Settings panel integration

- Add a `wireCollapsibleSection({ toggleId: 'layoutSettingsToggle', bodyId: 'layoutSettingsBody', storageKey: 'sidebar.settings.layout.collapsed' })` call inside `showSettings()` init sequence (idempotent wiring like other sections).
- Add `layoutSettingsBlock` to `DEFAULT_SETTINGS_IDS` to be recognized by `applyPanelOrder` / `wireReorderablePanel`.

4) JS wiring validation

- Ensure `wireLayoutControls()` remains idempotent and works when elements are inside the sidebar. Because it queries by IDs, no code changes should be necessary. Validate initialization order: `wireLayoutControls()` executes after DOM is ready at end of document; the controls will be present.
- If we lazy-load Settings panel content, ensure elements are present at page load. In current template, content is static; only panel visibility toggles. OK.

5) CSS adjustments

- Remove or comment the special rule `.comments-fs .graph-layout-toolbar { display: none !important; }` since toolbar no longer exists in header.
- Optional: In fullscreen comments mode, the sidebar already has higher `z-index`; nothing special needed.

6) Persistence

- Collapse state for the new block: `localStorage['sidebar.settings.layout.collapsed']`.
- Order persistence: include `layoutSettingsBlock` in the arrays saved under `ORDER_KEYS.settings`.

7) Accessibility

- Header toggle is a button (`role="button"` implicit), supports keyboard (Enter/Space) via existing `wireCollapsibleSection` helper.
- Labels for selects remain associated via `for`/`id` pairs. Maintain tooltips (`title` attributes).

8) Cleanup and cross-doc updates

- Update feature docs that reference `.graph-layout-toolbar` (e.g., comments fullscreen overlay docs) to remove or note deprecation of that class in header.

## Edge Cases & Risks

- Risk: Event listeners in `wireLayoutControls()` run before elements exist.
  - Mitigation: Keep controls in the main template; they load with the page. Wiring occurs at end-of-body script; safe.
- Risk: LocalStorage keys collide or unexpected defaults.
  - Mitigation: Use a new, namespaced key for collapse; reuse the existing order keys infra.
- Risk: Users rely on quick access in header.
  - Mitigation: Settings tab is one click away; if needed, re-introduce a small shortcut later.

## Step-by-Step Edits (high-level checklist)

- [x] Create `layoutSettingsBlock` markup under `#settingsPanel` with header/body and move controls inside it.
- [x] Remove header `.graph-layout-toolbar` container.
- [x] Add `wireCollapsibleSection` call for the new block in `showSettings()`.
- [x] Add `layoutSettingsBlock` to `DEFAULT_SETTINGS_IDS` array.
- [x] Validate `wireLayoutControls()` works without changes; adjust if needed.
- [x] Remove obsolete CSS rule that hides `.graph-layout-toolbar` in comments fullscreen.
- [x] Update related docs to reflect the move.

## Manual Testing Scenarios

1) Basic presence
- Open project view. Switch to Settings tab. Verify the new "Graph Layout" block appears with controls.

2) Preview mode toggle
- In Graph Layout block: set Layout = Suggested. Verify Run/Restore/Algorithm/Spacing become enabled and the preview pill appears. Switch back to Saved; verify positions restore and preview pill disappears.

3) Run, Refine, Restore
- With Suggested mode active: click Run (with default algo fcose) — layout runs. Click Refine — overlaps reduce. Click Restore Saved — positions return to saved.

4) Presets
- With Suggested mode: choose each preset (Tree LR, Tree TB, Radial Tree, Circular). Verify layout changes as expected and respects spacing.

5) Spacing
- With Suggested mode: adjust slider; value text updates (xN.N). On change, layout recomputes.

6) Arrange Neighbors
- Select a node in the graph. Click Arrange Neighbors — neighbors arrange in a circle around the node.

7) Persistence
- Collapse the Graph Layout block. Reload the page. Verify collapsed state persists. Reorder blocks in Settings (if reorder UI is present) and reload; verify order persists.

8) Header regression
- Confirm header no longer contains layout controls; remaining header buttons (Reset View, Toggle Sidebar, etc.) work.

9) Comments fullscreen
- Toggle comments fullscreen. Ensure sidebar renders correctly; no stray toolbar overlays.

10) A11y
- Tab through controls. Labels/tooltip read properly. Header toggle accessible via keyboard.

## Rollout & Backout

- Rollout: Ship as a single UI change; no migrations. Keep code paths reversible.
- Backout: Revert the Settings block and restore the header toolbar markup; no data impact.

## Open Questions

- Do we want a small header shortcut to jump to Settings › Graph Layout?
- Should "Arrange Neighbors" live under Actions instead? For now we keep it under Graph Layout for discoverability with related controls.

## Notes on Principles

- SOLID/KISS/DRY: Reuse existing wiring helpers; avoid duplicating logic; keep IDs consistent to minimize code surface change.
- UI/UX: Cleaner header; controls live where users expect persistent settings. Accessible and consistent with other Settings blocks.

---

## Status Log

- 2025-09-20: Drafted plan; awaiting approval to implement.
- 2025-09-20: Implemented relocation to Settings → Graph Layout; updated code and docs; manual QA passed.



