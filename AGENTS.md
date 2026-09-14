# Project Instructions

## Environment

- This project runs in Ubuntu under WSL2.
- Use Bash-compatible commands.
- Python dependencies and virtual environments are managed with `uv`.
- Prefer `uv run ...` when running Python tools.
- Do not use `pip install` unless explicitly requested.
- Do not modify `.env` or secrets.
- Dependencies are added in `pyproject.toml`. Do not add one without
  asking

## Working style

- Prefer small, incremental changes.
- Before making large architectural changes, explain the proposed approach first.
- Do not refactor unrelated code.
- Do not modify multiple files unless necessary.
- Inspect relevant files before editing them.
- Reuse existing project patterns and utilities where possible.

## Cost and context efficiency

- Do not scan the entire repository unless necessary.
- Start with the files directly relevant to the task.
- Avoid reading generated files, caches, build artifacts, virtual environments, or large datasets unless explicitly required.
- Prefer targeted searches over broad repository analysis.
- Keep explanations concise unless deeper reasoning is requested.

## Safety

- Do not delete files unless explicitly requested.
- Do not run destructive Git commands.
- Do not commit or push changes unless explicitly requested.
- Do not change dependency versions unless required by the task.
- Ask before installing new dependencies.

## Testing

- After modifying code, run the smallest relevant test first.
- Run broader tests only when the change justifies it.
- Report test failures clearly instead of attempting unrelated fixes.

## Git

- Keep changes focused on the requested task.
- Do not modify unrelated files.
- Before a large change, inspect the current Git diff/status.
- When a task is linked to a GitHub issue, completion includes the GitHub
  handoff: after the relevant tests pass, commit and push the implementation,
  add a concise issue comment with the commit and verification results, and
  close the issue only after the commit is integrated into `main`.
- If several linked issues are requested, complete and verify them in issue
  order and update each issue before moving to the next one.

## Documents

- `_docs/process.md` - how work is organized
- `_docs/entrystock_application_structure_guidelines.md` - how folders should be organised and instruction how they were reorginised from previous order: `_docs/map_entrypoint_structure_guidelines.md`