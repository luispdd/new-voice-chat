# Task 012: Conversation Management (Create, Edit Name, Delete)

- **Status**: Completed
- **Target Component**: `apps/frontend/src/app/chat/chat-container.component.ts`, `apps/frontend/src/app/core/api.service.ts`, `apps/backend/server.py`, `apps/backend/services/db.py`
- **Spec Reference**: [001-core-text-chat.md](../../specs/001-core-text-chat.md)

## Objective
Implement complete conversation lifecycle and naming management in the sidebar UI and backend API:

1. **Create Conversation**:
   - Provide a button to create new conversations and select the newly created session.

2. **Edit Conversation Name (Rename)**:
   - Allow users to edit and rename conversation titles directly in the sidebar (via inline text editing or rename action).
   - Persist updated conversation titles through the backend API (`PATCH /api/sessions/{session_id}` or `PUT /api/sessions/{session_id}`) in MongoDB.

3. **Delete Conversation**:
   - Allow users to delete individual conversations from the sidebar.
   - Automatically switch to the next available conversation (or create a new default one) when the active conversation is deleted.
   - Cascade deletion of all associated messages in the database.

4. **Conversation Switching & Display**:
   - Display conversation list in the sidebar and enable seamless switching between conversation histories.
