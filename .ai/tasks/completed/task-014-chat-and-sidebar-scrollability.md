# Task 014: Chat Message Feed and Sidebar Scrollability & Auto-Scroll

- **Status**: Completed
- **Target Component**: `apps/frontend/src/app/chat/chat-history.component.ts`, `apps/frontend/src/app/chat/chat-container.component.ts`
- **Spec Reference**: [001-core-text-chat.md](../../specs/001-core-text-chat.md)

## Objective
Ensure the chat message viewport and sidebar conversation list are reliably scrollable with automatic stick-to-bottom behavior for incoming messages:

1. **Scrollable Chat Message Viewport**:
   - Ensure the `.messages-viewport` container and `.chat-history-container` properly constrain height (`min-height: 0`, `overflow-y: auto`) in flex layouts so messages scroll smoothly without pushing the input bar or overflowing the viewport.

2. **Auto-Scroll to Recent Messages (Stick to Bottom)**:
   - Automatically scroll to the bottom of the message feed when new user messages are sent, new assistant tokens stream in, or audio begins playing.
   - Preserve scroll position when the user manually scrolls up to inspect previous conversation history.

3. **Scrollable Sidebar Conversation List**:
   - Constrain the `.sessions-list` in the sidebar (`overflow-y: auto`, `min-height: 0`, `flex: 1`) so long lists of conversations can be scrolled cleanly without overflowing the sidebar footer or layout.
