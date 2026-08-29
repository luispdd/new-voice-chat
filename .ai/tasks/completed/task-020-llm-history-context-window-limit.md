# Task 020: Increase and Configure LLM Message History Context Limit

- **Status**: Completed
- **Target Component**: `apps/backend/config.py`, `apps/backend/server.py`, `.ai/specs/001-core-text-chat.md`, `.ai/specs/004-session-persistence-mongo.md`
- **Instruction Reference**: [backend-python.md](../../instructions/backend-python.md)
- **Spec Reference**: [001-core-text-chat.md](../../specs/001-core-text-chat.md), [004-session-persistence-mongo.md](../../specs/004-session-persistence-mongo.md)

## Objective
Increase the LLM conversation prompt context history from 20 messages to 50 messages (~25 turns) to better utilize model context windows (such as 8k context in LM Studio and local LLMs) without incurring high prefill latency, and ensure this limit is consistently applied and configurable via backend settings.

## Requirements
1. **Configurable History Limit**:
   - Add `llm_history_limit: int` (default `50`) to `Settings` in `apps/backend/config.py`.
   - Support configuration via environment variable `LLM_HISTORY_LIMIT` and CLI argument `--history-limit`.
2. **Consistent Retrieval across Handlers**:
   - Use `settings.llm_history_limit` in REST `/api/chat` endpoint.
   - Use `settings.llm_history_limit` in WebSocket `/ws/chat` streaming handler.
3. **Spec Alignment**:
   - Ensure `.ai/specs/001-core-text-chat.md` and `.ai/specs/004-session-persistence-mongo.md` reflect the updated 50-message context window baseline.
4. **Verification**:
   - Run backend test suite and verify configuration parsing and endpoint context query limits.
