## Sidebar Task Comments: Collapse Empty Space When No Comments

Status: Proposed
Owner: System
Last Updated: 2025-09-07

### Initial Prompt (translated)

We have a task panel in the sidebar and a block with comments. When this block has no comments, there is first an empty space and then somewhere below the input field for entering a comment. We should not show this empty space.

=== Analyse the Task and project ===

Deeply analyze our task, our project and decide how to implement it best.

==================================================

=== Create Roadmap ===

Create a detailed, step-by-step plan of actions for implementing this task in a separate file-document. We have a folder docs/features for this. If there is no such folder, create it. Document in this file, as detailed as possible, all the problems, nuances and solutions already discovered and tried, if any. As you progress with the implementation of this task, you will use this file as a to-do checklist, you will update this file and document what has been done, how it was done, what problems arose and what decisions were made. For history, do not delete items, you can only update their status and comment. If during implementation it becomes clear that something needs to be added from tasks — add it to this document. This will help us preserve the context window, remember what has already been done and not forget to do what was planned. Remember that only the English language is allowed in the code and comments, project labels. When you write the plan, stop and ask me whether I agree to start implementing it or if something needs to be adjusted in it.

Also include steps for manual testing, i.e., what needs to be clicked in the interface.

==================================================

=== SOLID, DRY, KISS, UI/UX, etc ===

Follow the principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.
Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design.
Use Best Practices.

---

## 1) Problem Statement

When there are no comments for the selected task, the comments block still reserves a tall scrollable area before the input form. This creates unnecessary empty space and worsens UX.

## 2) Current Implementation (as of app/templates/project.html)

- Container `#taskCommentsBody` is a flex column with a CSS variable `--commentsHeight` and a height clamp: `height: clamp(20vh, var(--commentsHeight), 80vh)`.
- Inside, `#taskCommentsContent` is `flex-1 flex flex-col min-h-0`.
- The comments list lives inside a wrapper `<div class="flex-1 min-h-0">` and the list itself is `<ul id="commentsList" class="text-sm space-y-1 h-full overflow-auto"></ul>`.
- Because the list wrapper uses `flex-1` and the `<ul>` uses `h-full`, the list occupies the available height even when it is empty, pushing the input form to the bottom.
- Comments are loaded in `refreshLists(nodeId)`. After fetching, the code clears the list and appends `<li>` entries. There is no empty-state handling.

## 3) Goals and Non-Goals

### Goals
- Remove the large empty area when there are zero comments.
- Keep the form visible close to the section header, with minimal spacing.
- Do not break the resizer/fullscreen behavior for when comments exist.
- Keep the implementation simple, robust, and idempotent.

### Non-Goals
- Redesigning the entire comments block.
- Changing sanitization, editor, or attachments logic.

## 4) Options Considered

1. Hide the list container when empty.
   - Pros: Very small change, minimal risk, preserves existing layout when comments exist.
   - Cons: None significant.

2. Reduce `#taskCommentsBody` height when empty.
   - Pros: Also helps shrinking the overall section.
   - Cons: Interacts with resizer persistence, can surprise users when the first comment appears and height abruptly changes.

3. Reorder form above the list.
   - Pros: Input always visible at the top.
   - Cons: Larger refactor; contradicts established layout.

Decision: Implement Option 1. Optionally add a tiny height reduction (without touching persistence) only if needed after visual check.

## 5) Implementation Plan (Checklist)

- [ ] Add empty-state handling in `refreshLists`:
  - Compute `hasComments = Array.isArray(c.data) && c.data.length > 0`.
  - Toggle visibility of the list wrapper (the direct parent of `#commentsList`).
    - If empty: `listWrapper.classList.add('hidden')`.
    - If not empty: `listWrapper.classList.remove('hidden')`.
  - Do not remove existing sizing classes; just use `hidden` to avoid layout shifts.
- [ ] Ensure that when comments appear (after posting), the list shows again and scroll behaves as before.
- [ ] Optional: if visual polish is needed, slightly reduce vertical gap above the form via small utility classes (no global CSS).
- [ ] Keep resizer and fullscreen logic unchanged.
- [ ] Update this document with results and mark items done.

## 6) Acceptance Criteria

- With zero comments, the input form appears immediately below the controls, without a large empty area.
- After adding the first comment, the list appears in the same session without reload.
- Resizer and fullscreen work identically when comments are present.
- No regressions for existing comments rendering and editing flows.

## 7) Manual Test Plan

Preconditions: A project with a selectable node; sidebar visible.

Steps:
1. Select a node with zero comments.
   - Expected: No large empty space above the comment input; list area is hidden.
2. Type a comment and submit.
   - Expected: The new comment appears; the list becomes visible; input remains below the list.
3. Reload the page and reselect the same node.
   - Expected: The comment list renders correctly; resizer height persists; no layout jumps.
4. Delete all comments.
   - Expected: The list hides again; no empty space returns.
5. Toggle comments fullscreen on/off with zero and non-zero comments.
   - Expected: No visual glitches; list remains hidden when empty.

## 8) Risks and Mitigations

- Risk: Hiding the wrapper could interfere with future features targeting `#commentsList` sizing.
  - Mitigation: Only toggle `hidden`; keep existing classes intact.
- Risk: Edge cases where `c.data` is undefined or API errors occur.
  - Mitigation: Guard with `Array.isArray()` and default to empty.

## 9) Rollback Plan

Revert the empty-state toggle changes in `refreshLists`. No database or migration impact.

## 10) Change Log

- 2025-09-07: Document created; analysis completed; plan proposed to hide the list wrapper when empty, minimal change approach.


