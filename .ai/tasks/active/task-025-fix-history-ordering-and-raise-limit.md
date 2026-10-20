# Task 025: Fix LLM History Ordering and Raise Limit to 100

- **Status**: Active
- **Target Component**: `apps/backend/db/mongo.py`, `apps/backend/config.py`, `apps/backend/tests/test_config_history_limit.py`
- **Instruction Reference**: [backend-python.md](../../instructions/backend-python.md)
- **Spec Reference**: [001-core-text-chat.md](../../specs/001-core-text-chat.md), [004-session-persistence-mongo.md](../../specs/004-session-persistence-mongo.md)

## Objective
`get_messages` sorts ascending then applies `.limit()`, so once a conversation exceeds the limit the LLM receives the **oldest** N messages and never the newest. Fix it to return the most recent N messages (in chronological order) and raise the default LLM history limit from 50 to 100.

## Requirements
1. **Ordering Fix**:
   - In `get_messages`, query sorted by `timestamp` descending with `.limit(limit)`, then reverse so the result is chronological.
2. **Default Limit**:
   - Change the `llm_history_limit` default (env `LLM_HISTORY_LIMIT` and CLI `--history-limit`) from `50` to `100`.
3. **Tests**:
   - Update `test_config_history_limit.py` default assertion to `100`.
4. **Verification**:
   - Run backend test suite.
