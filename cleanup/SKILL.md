---
name: cleanup
description: Clean up build artifacts, test caches, and temporary files generated during AI-assisted development. Use after running tests (pytest, colcon), builds (colcon build), or when the workspace accumulates unnecessary cache directories.
---

# Cleanup

Remove reproducible build/test artifacts that clutter the workspace. Only delete files that can be regenerated or are explicitly gitignored.

## Workflow

1. Run the scan command to list all artifacts.
2. Confirm the artifact list with the user before deleting.
3. Delete confirmed artifacts.
4. Report the number of deleted directories and bytes recovered.

## Scan Commands

```bash
# Python test caches (pytest)
find . -name ".pytest_cache" -type d

# Python bytecode cache
find . -name "__pycache__" -type d

# ROS2 / colcon build output (already in .gitignore)
du -sh build/ install/ log/ 2>/dev/null

# CMake temporary files outside build/
find . -name "CMakeCache.txt" -not -path "*/build/*"
find . -name "cmake_install.cmake" -not -path "*/build/*"
```

## Delete Commands

```bash
# Dry-run first, then execute
find . -name ".pytest_cache" -type d -exec rm -rf {} +
find . -name "__pycache__" -type d -exec rm -rf {} +
```

## Boundaries

- Never delete `build/`, `install/`, or `log/` without explicit user confirmation — these require a full rebuild.
- Never delete source files, configuration, weights, datasets, or any file NOT listed in `.gitignore`.
- Do not delete files tracked by git (`git ls-files`).
- The `.pytest_cache` and `__pycache__` directories are always safe to delete; they regenerate automatically on the next test run.
