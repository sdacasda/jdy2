# Changelog

## v2

- Normalize shell-script line endings and permissions inside GitHub Actions.
- Invoke repository shell scripts explicitly through `bash`.
- Always create `output/WORKFLOW_STATUS.txt` before diagnostics collection.
- Do not require a firmware image in `build_mode=validate`.
- Do not add a second red error when no artifact files exist.

## v3

- Fix ShellCheck SC2164 in `collect_output.sh`.
- Validation workflow now passes ShellCheck instead of exiting with code 1.

## v4

- Reuses the swap already supplied by GitHub's Ubuntu runner.
- Never rewrites an active `/swapfile`.
- Creates an isolated fallback swap under `$RUNNER_TEMP` only when no swap exists.
- Falls back from `fallocate` to `dd`.
- Treats optional swap creation failure as a warning rather than a build failure.

