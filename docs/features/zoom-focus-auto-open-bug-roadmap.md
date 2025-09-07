## Auto-open Link on Zoom — Focus Selection Bug (Anchor vs. Center)

### Context and Symptoms
- The board uses Cytoscape.js with custom smooth wheel zoom and LOD logic in `app/templates/project.html`.
- When you click a node that has a `link_url` and then zoom in, navigation opens the correct link, as expected.
- After a full page refresh, if you do not click any node and start zooming so that a particular node is in focus, navigation sometimes opens a link belonging to a different node far away in the graph.

### Hypothesis and Root Cause
- The auto-open logic runs on zoom via `checkAndAutoOpenLinkOnOversized()`.
- If no node is selected (`selectedNodeId` is empty), it derives a focus candidate using `findFocusedNodeForZoom()`.
- Current focus heuristic relies primarily on the viewport center and node rendered size/proximity, not on the actual wheel-zoom anchor (cursor position) used during zoom.
- Our custom wheel zoom code anchors zoom to the cursor coordinates, but the focus-finding uses viewport center; these can diverge, especially right after page load when there is no selection and the cursor is not centered. As a result, a different node (near the center or simply larger) may be chosen and its link is opened.

### Current Implementation Snapshot (Code Pointers)
- Auto-open on zoom:
  - `checkAndAutoOpenLinkOnOversized()` subscribes to `cy.on('zoom', ...)` and decides whether to navigate once thresholds are met (near full-screen node size or near-max zoom).
  - When `selectedNodeId` is not set, it calls `findFocusedNodeForZoom()` to pick a node.
- Focus picking (today):
  - `findFocusedNodeForZoom()` ranks nodes by whether they are under viewport center, their rendered size, and distance from viewport center.
  - It only considers nodes with a non-empty `link_url` and that are visible (not `display: none`).
- Smooth wheel zoom:
  - We disable default user zoom and implement wheel zoom via RAF. We maintain a local `anchor` (rendered position) per wheel event to zoom toward the cursor.

### Design Goals
- Respect user intention when zooming without prior click: if the user zooms toward a node (cursor-anchored), only that node should be considered for auto-open (when oversized). If there is no clear target under the cursor, do not open anything.
- Maintain performance and simplicity (KISS) and keep behavior predictable (UI/UX).
- Keep code readable and robust (SOLID/DRY/SoC).

### Proposed Solution
1) Anchor-based focus selection when no node is selected
   - Track the latest cursor position over the Cytoscape container and the latest wheel-zoom anchor globally (module-level), initialized to viewport center.
   - Replace `findFocusedNodeForZoom()` with an anchor-first strategy:
     - Primary: return the visible node (not `display: none`) whose `renderedBoundingBox()` contains the current anchor and has a non-empty `link_url`.
     - Secondary: if none contains the anchor, choose the nearest visible node to the anchor within a reasonable pixel radius (e.g., 32–64 px in rendered coordinates); break ties by smaller distance, then by larger rendered area.
     - Fallback: if none is within the radius, return null and do not auto-open.
   - This prevents selecting far-away nodes and aligns behavior with the zoom anchor (cursor).

2) Interaction with LOD
   - Continue to ignore nodes with `style('display') === 'none'`.
   - Consider only base nodes (exclude children of collapsed groups) similar to current LOD safeguards.

3) Thresholds and once-only gating
   - Keep the existing oversized checks and once-per-node gating via `oversizedOpenFiredForNodeIds`.
   - Continue prewarm/prerender hints as today (unchanged).

4) Accessibility and keyboard zoom
   - When zooming via buttons (no cursor anchor), default the anchor to viewport center.
   - Only auto-open when the anchor actually intersects/targets a node. Otherwise, no action.

### Acceptance Criteria
- After page refresh, without clicking, zooming toward a linked node opens the correct node’s link when oversized.
- Anchor-based selection never opens a link for a node far from the zoom anchor.
- Ctrl+click behavior remains unchanged.
- Performance remains smooth with large graphs and LOD on.

### Implementation Plan (Step-by-Step)
1. Introduce global anchor tracking
   - Promote the `anchor` variable (currently local to the wheel handler) to a module-level variable initialized to viewport center.
   - Update it on `wheel` and `mousemove` over the Cytoscape container to reflect the latest cursor position.

2. Implement `findNodeByAnchor()`
   - Input: current `anchor` in rendered coordinates.
   - Filter candidates: visible nodes with non-empty `link_url`.
   - Primary match: node whose rendered box contains `anchor`.
   - Secondary match: nearest node to `anchor` within a pixel radius; tie-break by distance then by area.
   - Return node id or null.

3. Update `checkAndAutoOpenLinkOnOversized()`
   - When `selectedNodeId` is empty, use `findNodeByAnchor()` instead of viewport-center ranking.
   - If it returns null, do nothing (no speculative navigation to unrelated nodes).

4. Keep thresholds/gating as-is
   - Retain `RATIO_TH_PRIMARY`, `RATIO_TH_SECONDARY`, and `MAX_ZOOM_OPEN_LEVEL` values.
   - Preserve once-only gating per node id.

5. Inline docs and code clarity
   - Keep comments concise (English), explain “why” for anchor-first focus.
   - Follow existing formatting and style.

### Manual Test Plan (What to click)
1) Repro the reported scenario
   - Open a project with at least two nodes that have `link_url` set, placed far apart.
   - Reload the page. Do not click any node.
   - Hover the desired linked node and zoom in with the mouse wheel until it fills most of the screen.
   - Expected: Navigation opens the link of the hovered node, not a different one.

2) Click-first behavior still works
   - Click a linked node to select it, then zoom in until oversized.
   - Expected: The same node’s link opens, once.

3) No link → no navigation
   - Hover an unlinked node and zoom to oversized.
   - Expected: No navigation.

4) Off-center anchor
   - Move the cursor off-center, toward a linked node near an edge, then zoom in.
   - Expected: That node is chosen and opens; the viewport center does not influence selection.

5) Button zoom
   - Use the Zoom In button several times without moving the cursor or clicking nodes.
   - Expected: Only if the anchor (default center) coincides with a linked node will navigation occur; otherwise nothing opens.

6) LOD interplay
   - With LOD enabled, ensure hidden nodes are not considered; hover a visible linked node and zoom.
   - Expected: Only visible linked nodes are candidates and behave correctly.

### Risks and Mitigations
- Risk: Picking nearest node within a radius may still choose an unintended target.
  - Mitigation: Require containment-first; use a conservative radius (start with ~32 px) and prefer no action when ambiguous.
- Risk: Extra computations on zoom could affect performance.
  - Mitigation: Operate only on visible nodes, short-circuit early, and keep the search simple.
- Risk: Keyboard-only users may not have an anchor under a node.
  - Mitigation: Default to center; consider adding a modest hint or documentation if needed.

### Initial Prompt (English Translation)
The user’s original task description translated to English and preserved for context.

"""
I have a board at `http://127.0.0.1:5050/projects/87654234-b24e-4abe-9ca5-d93cefbed40e` with a dot that links to `http://127.0.0.1:5050/projects/220aee43-ba07-4862-ab5d-b68743026cd6`. If you click that dot and start zooming, navigation follows the link as expected. But if you refresh the page, do not click anywhere, and start zooming so that only this dot is in focus, navigation goes to a different page linked to another dot that is actually far away from this dot.

=== Analyse the Task and project ===

Deeply analyze our task and our project and decide how best to implement this.

==================================================

=== Create Roadmap ===

Create a detailed, step-by-step action plan for implementing this task in a separate document file. We have a `docs/features` folder for this. If such a folder does not exist, create it. Document, in as much detail as possible, all discovered and tried problems, nuances, and solutions if any. As you progress in implementing this task, you will use this file as a to-do checklist; you will update this file and document what has been done, how it was done, what problems arose, and what decisions were made. For history, do not delete items; only update their status and add comments. If during implementation it becomes clear that something needs to be added from tasks — add it to this document. This will help us preserve context, remember what we have already done, and not forget to do what was planned. Remember that only the English language is allowed in the code and comments and in the project text. When you write the plan, stop and ask me if I agree to start implementing it or if something needs to be adjusted in it.

Also include steps for manual testing, i.e., what needs to be clicked in the interface.

==================================================

=== SOLID, DRY, KISS, UI/UX, etc ===

Follow the principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.
Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design.
Use Best Practices.
"""

### Implementation Checklist
- [ ] Promote `anchor` to module scope and initialize to viewport center.
- [ ] Update `anchor` on `wheel` and `mousemove` over Cytoscape container.
- [ ] Implement `findNodeByAnchor()` with containment-first, nearest-within-radius fallback.
- [ ] Use `findNodeByAnchor()` in `checkAndAutoOpenLinkOnOversized()` when no selection.
- [ ] Keep once-only gating and thresholds; ensure visible-only filtering.
- [ ] Add concise inline comments; match existing formatting.
- [ ] Manual test pass (scenarios above) across small and large graphs.

### Notes
- Keep code and comments in English.
- Prefer clarity over cleverness; avoid over-optimization.

### Changelog
- 2025-09-07: Drafted roadmap with anchor-based focus selection to fix mismatched auto-open after reload with no prior selection.


