Agent-2A Pre-commit Instructions

1. Install pre-commit (if not already):

```bash
pip install pre-commit
pre-commit install
```

2. The pre-commit config runs `ruff`, `black`, and the Agent-2A analyzer script. The analyzer will run on staged files and block commits that introduce obvious duplicate IDs across files or cross-tab imports.

3. To run the hooks manually:

```bash
pre-commit run --all-files
```

Notes:
- The analyzer uses a conservative heuristic; if it flags a problem that appears false-positive, coordinate with AGENT-2A or AGENT-1A before bypassing.
