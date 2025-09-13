# Node Chain Creation via Hold-C and Clicks — Roadmap

## Initial Prompt (translated)

I want to add the ability to create a node on the board as follows: if I hold C and then click on some node, and then on an empty place, not on a node, then in this empty place a node appears which is already connected with the node I clicked on in the previous click. This way, by the way, you can create several nodes in a chain.

I’m thinking about how to add labels to nodes right away. First option: on the click that creates the node, slide out a sidebar for the node name, but in this case the chain creation mode seems to be broken, because I’ll release C. Or do it like this: while C is not released—allow creating nodes, but as soon as it is released, the sidebar slides out and the node that is in focus, selected, the one that was last clicked is edited.

Please analyze the task and the project in depth and decide how best to implement this.

Create a detailed, step-by-step plan of actions to implement this task in a separate file-document. We have a folder docs/features for this. If there is no such folder, create it. Fix in the document as much as possible all discovered and tried problems, nuances and solutions, if any. As you progress through the implementation of this task, you will use this file as a todo checklist; you will update this file and document in it what has been done, how it was done, what problems arose and what decisions were made. For history, do not delete items, you can only update their status and comment. If in the course of implementation it becomes clear that something needs to be added from tasks—add it to this document. This will help us preserve the context window, remember what we have already done and not forget to do what was planned. Remember that only the English language is allowed in the code and comments, project labels.

Also include steps for manual testing, that is, what needs to be clicked in the interface.

Follow SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices. Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design. Use Best Practices.

If you need the current time, get it from the time MCP Server.

---

## Context Summary and Constraints

- Frontend is implemented in `app/templates/project.html` using Cytoscape.
- Existing connect mode already supports: hold `C` (or Cyrillic `С`) to activate temporary connect mode, click source node, then click target node to create an edge. Releasing `C` cancels the mode automatically (timeout and keyup handler). See the self-invoking `connectMode()` block with handlers around lines ~1813–1855.
- Node creation currently happens via toolbar `Add Node` button which prompts for a title then POSTs `/api/v1/projects/{projectId}/nodes`, and `addNodeToCy` places the node at a default top-left position and persists position via POST `/api/v1/nodes/{id}/position`.
- There is no current flow to create a node by clicking on the empty canvas with a specific position.
- Node schema (`NodeSchema`) requires `title` and `project_id`. Position is stored separately via `NodeLayout` via `/nodes/{node_id}/position` endpoint.
- Sidebar auto-reveal logic exists but is suppressed while connect mode is active or `C` is held.

Implications:
- We can extend the connect mode to support: if active and after selecting source node, a tap on background creates a new node at the clicked position, then creates an edge from source to the new node. While `C` is held, allow repeating to chain-create multiple nodes.
- To avoid breaking the chain when editing title, delay opening the sidebar until `C` is released. Then focus the last created/selected node and reveal the sidebar for title editing. Inline title field (`#selNodeTitle`) supports direct editing and saving on blur/Enter.

---

## Goals and Non-Goals

- Goals
  - Add “Hold-C Chain Create” mode that: source node tap → background tap → create node at position → auto-link from source → keep mode active until `C` is released.
  - Support creating multiple nodes in sequence without releasing `C`.
  - After `C` release, automatically open sidebar focused on the last created node’s title for quick naming.
  - Provide accessible UI hints and predictable behaviors (ESC to cancel, timeout, cursor feedback).
- Non-Goals
  - Server changes to schemas or models (not needed).
  - Bulk undo/redo; advanced edge routing.

---

## UX Design

- Activation
  - Hold `C` to enter temporary connect/chain mode (existing). The hint banner already appears. Cursor switches to crosshair.
- Interaction
  1) While holding `C`, click an existing node N to set it as source (adds CSS class `connect-source`).
  2) While still holding `C`:
     - Click another node → create edge N → M (existing behavior).
     - Click on empty background → create a new node at click position P, then create edge N → New, keep mode active and set New as new source to continue chaining by clicking background again (optional behavior) or allow clicking a different node.
  - Cancel with ESC or releasing `C`.
- Titling Flow
  - During hold: do not open sidebar (keep chain uninterrupted).
  - On `keyup C`: reveal sidebar if hidden; select/focus the last created node; place caret into `#selNodeTitle` (contenteditable) for immediate typing.
- Visual Feedback
  - Reuse existing hint overlay for connect mode; extend text to mention background click creates a new node.
  - Flash animation on newly created node.

Accessibility
- Keyboard: Holding `C` is compatible with existing flow; ESC cancels. Focus management after release targets title field.

---

## Technical Design

- New client logic inside `connectMode()` IIFE in `project.html`:
  - Track additional state:
    - `lastCreatedNodeId` (string | null)
    - `pendingSourceId` (reuse existing `sourceId`)
  - Extend event handling:
    - On `cy.on('tap', (evt) => { if (active && evt.target === cy) ... })` branch, instead of cancel, perform chain-create if a `sourceId` is chosen and `isConnectKeyHeld` is true:
      - Compute graph position from `evt.position` (Cytoscape API provides x/y in graph coords).
      - Create node via POST `/api/v1/projects/${projectId}/nodes` with a temporary title (e.g., "New node").
      - Immediately call `addNodeToCy` but override its default position behavior to place at `evt.position` and persist position.
      - Create edge via POST `/api/v1/projects/${projectId}/edges` from `sourceId` to the new node id.
      - Update `sourceId = newNodeId` to allow chaining.
      - Store `lastCreatedNodeId = newNodeId`.
      - Keep `active` until keyup/timeout.
    - On `document.addEventListener('keyup', isConnectKey)`: after `cancel()`, if `lastCreatedNodeId`, programmatically:
      - Select the node in Cytoscape.
      - Ensure sidebar is visible (`applySidebarVisibility()` flows exist).
      - Focus `#selNodeTitle` for inline rename.
  - Modify `addNodeToCy(n)` to optionally accept a position param. If provided, use it instead of the top-left default and persist via `/nodes/{id}/position`.
- Safety and Idempotency
  - Debounce/lock on creation clicks to avoid duplicate POSTs due to double taps.
  - Validate duplicate edges (already checked).

- Server: No changes needed. Use existing endpoints:
  - POST `/api/v1/projects/{project_id}/nodes` { title }
  - POST `/api/v1/nodes/{id}/position` { x, y }
  - POST `/api/v1/projects/{project_id}/edges` { source_node_id, target_node_id }

- Labels
  - Default title: "New node" (localized label can be introduced later; current UI uses English).
  - Post-release inline edit updates via existing handler: `#selNodeTitle` saves on blur/Enter.

---

## Edge Cases and Decisions

- If user clicks background before selecting a source node: do nothing, show a subtle shake on hint or a toast.
- If user releases `C` immediately after creating the node but before edge POST completes: ensure `keyup` handler waits a tick before selecting the node; failure-safe—if edge fails, still focus node title.
- If node creation fails (401 unauthorized): show alert (existing postJSON handles 401) and cancel mode.
- If the clicked background position is outside the current viewport: rely on Cytoscape event position which is in graph coords; persist as-is.
- Autoscroll on selection: existing logic centers selected node if outside padding; reuse it to bring last node into view.

---

## Implementation Steps (Checklist)

1. Update `addNodeToCy(n)` to accept optional `{ x, y }` position, use it when provided; persist via `/nodes/{id}/position`.
2. In `connectMode()`:
   - Extend hint text to mention background click creates a new node.
   - In background tap handler, if `active && sourceId && window.isConnectKeyHeld` then chain-create:
     - Lock while creating.
     - POST node (title: "New node").
     - Add node at `evt.position` and persist position.
     - POST edge from `sourceId` to new node id.
     - Set `sourceId = newNodeId`; set `lastCreatedNodeId = newNodeId`.
     - Keep `active` true; keep crosshair cursor.
   - In keyup handler for `C`:
     - After `cancel()`, if `lastCreatedNodeId` exists: select it, ensure sidebar visible, focus `#selNodeTitle`.
3. Minor: Flash effect on new node (optional CSS class toggle for 300ms).
4. QA pass: verify no regressions in existing connect mode and sidebar auto-hide rules.

---

## Manual Test Plan

- Precondition: Open a project board with at least one node A.
- Chain create basic
  - Hold `C`.
  - Click node A (source). Cursor becomes crosshair; A marked as source.
  - Click empty background point P1.
    - A new node N1 appears at P1 with default title "New node".
    - An edge A → N1 is created.
    - Mode stays active; N1 becomes the current source.
  - Click empty background point P2.
    - N2 appears at P2; edge N1 → N2 is created.
  - Release `C`.
    - Sidebar opens (if hidden).
    - N2 is selected; caret focuses `#selNodeTitle` for immediate typing.
    - Type a name, press Enter; title saves and reflects on node.
- Mixed targets
  - Hold `C`, click node B, then click node C: creates edge B → C (regression check).
  - While still holding `C`, click background P3: creates node N3 and edge C → N3.
- Cancel/timeout
  - Press ESC while active: mode cancels; no further actions.
- Error flows
  - If unauthenticated, creating node should prompt "Login required" alert and cancel mode.

---

## Risks and Mitigations

- Duplicate click firing → Use a simple in-flight flag to guard concurrent creations.
- Sidebar focus race → Delay focus via requestAnimationFrame or setTimeout(0) after DOM/Cytoscape updates.
- Performance when chaining many nodes → Operations are O(1)/O(E) minimal; acceptable for current scale.

---

## Acceptance Criteria

- Holding `C`, clicking a source node, then clicking background creates a new node at the clicked position and an edge from source to the new node.
- Repeating background clicks continues the chain without releasing `C`.
- Releasing `C` brings up the sidebar (if hidden) and focuses the last created node’s title for inline editing.
- Existing connect mode behaviors remain intact (node-to-node edges, ESC cancel, duplicate prevention).

---

## Status Log

- 2025-09-12: Drafted roadmap and technical design. Pending user approval to implement.
