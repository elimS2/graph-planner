## Task Panel — Merge Selection & Linking, Separate Metadata

### Initial Prompt (translated to English)

We have a sidebar with a task panel, and inside it there are blocks Selection and Linking.

I would like a single block to display both Selected Node Title and Link URL and the checkbox to open or not open in a new tab, and to name this block accordingly.

Fields Translated Title (preview), Selected Node ID, Created At, Descendants (via edges) can be moved into a separate block.

=== Analyse the Task and project ===

Deeply analyze our task, our project and decide how this is best implemented.

==================================================

=== Create Roadmap ===

Create a detailed, comprehensive step-by-step plan of actions for implementing this task in a separate file-document. We have a folder docs/features for this. If there is no such folder, create it. Record in the document as thoroughly as possible all discovered and tried problems, nuances and solutions, if any. As you progress with this task, you will use this file as a todo checklist, updating this file and documenting what was done, how it was done, what problems arose and what solutions were chosen. For history, do not delete items; you may only update their status and comment. If during implementation it becomes clear that something needs to be added from tasks – add it to this document. This will help us preserve context, remember what has already been done, and not forget to do what was planned. Remember that only the English language is allowed in the code and comments and project labels. When you write the plan, stop and ask me whether I agree to start implementing it or if something needs to be adjusted in it.

Include this prompt that I wrote in the plan, but translate it into English. You can name it something like "Initial Prompt" in the plan document. This is needed in order to preserve in our roadmap file the exact context of the task statement without the "broken telephone" effect.

Also include in the plan steps for manual testing, i.e., what needs to be clicked in the interface.

==================================================

=== SOLID, DRY, KISS, UI/UX, etc ===

Follow the principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.
Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design.
Use Best Practices.

---

### Context and Current Behavior

- The sidebar UI is defined in `app/templates/project.html` under the Task tab.
- There are two adjacent blocks: `#taskSelectionBlock` (Selected Node Title, Translated Title, Selected Node ID, Created At) and `#taskLinkBlock` (Link URL, Open in new tab, hint).
- JS logic already wires:
  - Inline editing and save for `Selected Node Title` via `#selNodeTitle` (blur/Enter → PATCH `/api/v1/nodes/:id`).
  - Link URL input via `#selNodeLinkUrl` (blur/Enter → PATCH), checkbox `#openInNewTab` persisted to localStorage and PATCHed per-node.
  - Other metadata bindings: `#selNodeTitleTranslated`, `#selNode`, `#createdAt`, `#descCount`, refresh button `#btnRefreshTranslation`.
- The project recently added client-side block reordering with persistence keys `ORDER_KEYS.task` and default list `DEFAULT_TASK_IDS` in the same template.

Implication: We can restructure the Task Panel by adjusting the HTML structure and updating the default order array and collapsible wiring without backend changes.

### Goals

- Merge Selection and Linking content into a single, focused block (name: "Title & Link").
- Move metadata fields (Translated Title, Selected Node ID, Created At, Descendants) into a dedicated "Metadata" block.
- Preserve existing behaviors: inline title save, link URL save, open-in-new-tab preference, translation refresh, descendant count.
- Maintain collapsible UX and saved collapsed states; update storage keys only if we rename blocks.
- Keep code in English and apply SOLID/DRY/KISS.

### Non-Goals

- No backend API changes; reuse existing endpoints and data.
- No visual redesign beyond block grouping and headings.
- No change to keyboard shortcuts or graph interactions.

### Technical Design

1) HTML structure updates in `project.html`:
   - Create a new block container `#taskSelectionLinkBlock` with header title "Title & Link" and body containing:
     - Selected Node Title (inline editable `#selNodeTitle`)
     - Link URL input `#selNodeLinkUrl`
     - Checkbox `#openInNewTab` and hint `#linkHint`
   - Create a new block `#taskMetadataBlock` with header title "Metadata" and body containing:
     - Translated Title (preview) `#selNodeTitleTranslated` + `#btnRefreshTranslation`
     - Selected Node ID `#selNode`
     - Created At `#createdAt`
     - Descendants (via edges) `#descCount`
   - Remove old `#taskSelectionBlock` and `#taskLinkBlock` containers.

2) Collapsible wiring:
   - Add: `wireCollapsibleSection` for `taskSelectionLinkToggle` and `taskMetadataToggle` with storage keys:
     - `sidebar.task.selectionLink.collapsed`
     - `sidebar.task.metadata.collapsed`
   - Remove wiring for old `taskSelectionToggle` and `taskLinkToggle`.

3) Order persistence:
   - Update `DEFAULT_TASK_IDS` to include new ids, replacing the removed ones:
     - `['taskSelectionLinkBlock','taskMetadataBlock','taskStatusPriorityBlock', ...]`
   - Optionally migrate any previously saved order: when applying order, if old ids are present, map them to new ones gracefully (e.g., treat `taskSelectionBlock` or `taskLinkBlock` as `taskSelectionLinkBlock`). Keep logic simple and defensive.

4) JS bindings reuse:
   - The element ids for fields remain the same, so existing JS logic for inline title, link URL, open-in-new-tab, translation refresh, and metadata displays continues to work without code changes.
   - Only references to block toggle/body ids change in the collapsible wiring and order arrays.

5) Accessibility & UX:
   - Keep headings concise, consistent casing, and maintain keyboard focusability on inputs.
   - Ensure tab order remains logical: title → link url → checkbox.

6) Styling:
   - Use existing Tailwind utility classes already applied to blocks.
   - No custom CSS necessary.

### Edge Cases

- Saved collapsed state for old blocks won’t apply automatically. We accept this minimal disruption and start fresh for the new blocks.
- Saved order may reference removed ids. Our order application should ignore unknown ids and append new blocks by default.

### Step-by-Step Implementation Plan

1) Add new HTML blocks and move field elements under them while preserving the same element ids for inputs/spans.
2) Remove old Selection and Linking containers.
3) Update collapsible wiring to target new blocks and keys.
4) Update `DEFAULT_TASK_IDS` to include new block ids.
5) Manual pass: verify bindings, saves, and hint toggle still work.
6) Optional: Add simple mapping in order application to coalesce old ids into the new `taskSelectionLinkBlock`.

### Manual Test Plan (What to click)

1) Open a project page and ensure Task tab is active.
2) Select a node and verify:
   - Selected Node Title is editable and saves on Enter/blur.
   - Link URL saves on Enter/blur; invalid URL shows alert as before.
   - "Open in new tab (Ctrl+Click)" checkbox persists and patches per-node.
3) Expand Metadata block and verify:
   - Translated Title shows a value; clicking Refresh updates it.
   - Selected Node ID matches the selected node.
   - Created At displays a date/time.
   - Descendants count updates when selecting nodes with different descendant totals.
4) Collapse/expand both new blocks; reload to see collapsed states persist.
5) Verify block order persistence still works and new blocks appear in expected order by default.
6) Ctrl+click on the node still opens per preference (no regression).

### Risks, Assumptions, Mitigations

- Risk: Any missed reference to old block ids in wiring breaks collapse behavior.
  - Mitigation: Grep and update all `taskSelection*` and `taskLink*` wiring usages.
- Assumption: Keeping inner field ids unchanged ensures JS logic continues to work.
- Mitigation: Run manual tests on Windows/Chrome and Firefox.

### Tasks (Living Checklist)

- [x] Analyze current Selection/Linking/Metadata structure and bindings.
- [ ] Implement new `taskSelectionLinkBlock` and `taskMetadataBlock` in `project.html`.
- [ ] Update collapsible wiring and storage keys.
- [ ] Update `DEFAULT_TASK_IDS` and verify order behavior.
- [ ] Manual testing pass per checklist.
- [ ] Document any issues and decisions below.

### Changelog

- 2025-09-06: Drafted roadmap and testing plan.


