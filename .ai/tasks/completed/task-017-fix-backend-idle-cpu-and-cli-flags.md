# Task 017: Fix Backend Idle High CPU Usage & CLI Argument Forwarding

- **Status**: Completed (2026-08-27)
- **Target Component**: `apps/backend/config.py`, `apps/backend/main.py`, `apps/backend/pyproject.toml`, `package.json`, `.ai/instructions/backend-python.md`
- **Instruction Reference**: [backend-python.md](../../instructions/backend-python.md)

---

## 🔍 Problem & Root Cause Analysis

### 1. High Idle CPU Utilization (~100% Core Load)
* **Symptom**: When the FastAPI backend was left running with no active clients or WebSocket connections, Python consumed excessive CPU resources continuously.
* **Root Cause 1 (Missing `watchfiles`)**: The optional Rust-based file watcher library `watchfiles` was missing from the backend dependencies. Uvicorn fell back to `StatReload`, a pure-Python polling loop executing `os.stat` every second.
* **Root Cause 2 (Unscoped Root Monorepo Watch)**: Dev reload was launched from the monorepo root without `--reload-dir apps/backend`. `StatReload` was actively traversing and statting all 67,800+ files in `node_modules/`, `apps/backend/.venv/`, `.git/`, `.nx/`, and `.angular/` every second.

### 2. CLI Parameter Rejection (`--engine`, `--model`)
* **Symptom**: Running `bun run backend:dev --engine lmstudio --model gemma-3-4b-it` failed with:
  ```
  Error: No such option '--engine'. Did you mean '--env-file'?
  ```
* **Root Cause**: `backend:dev` invoked the `uvicorn` binary directly (`uvicorn apps.backend.server:app ...`), which only accepts Uvicorn flags and rejects application arguments.

---

## 🛠️ Implemented Solutions

1. **Installed `watchfiles`**:
   - Added `watchfiles` to [`apps/backend/pyproject.toml`](../../apps/backend/pyproject.toml) via `uv add --project apps/backend watchfiles` to leverage native Linux `inotify` kernel events.

2. **Scoped Auto-Reload Directory**:
   - Added `--reload` and `reload_dirs` support to `Settings` in [`apps/backend/config.py`](../../apps/backend/config.py).
   - Configured [`apps/backend/main.py`](../../apps/backend/main.py) to pass `reload_dirs=["apps/backend"]` whenever auto-reload is enabled, strictly isolating file watching to backend Python code.

3. **Unified CLI Entrypoints via `main.py`**:
   - Updated `backend` and `backend:dev` scripts in [`package.json`](../../package.json) to both route through `apps/backend/main.py`:
     ```json
     "backend": "PYTHONPATH=. uv run --project apps/backend python3 apps/backend/main.py",
     "backend:dev": "PYTHONPATH=. uv run --project apps/backend python3 apps/backend/main.py --reload"
     ```
   - Enabled custom CLI arguments (`--engine`, `--model`, `--port`, `--host`, `--base-url`, `--api-key`) to be accepted and parsed by `argparse` across both commands.

4. **Updated Backend Documentation**:
   - Documented the `watchfiles` requirement, `--reload-dir` scoping rule, `OMP_WAIT_POLICY=PASSIVE` pattern, and standard CLI commands in [`.ai/instructions/backend-python.md`](../../instructions/backend-python.md).

---

## ✅ Verification
- Ran `bun run backend:dev --help` and `bun run backend --help` to verify CLI parameter support.
- Tested `bun run backend:dev --engine lmstudio --model gemma-3-4b-it` successfully booting the server with auto-reload scoped to `apps/backend`.
