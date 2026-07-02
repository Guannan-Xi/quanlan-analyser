# QLanalyser Browser E2E Runner Setup - 2026-06-27

## Purpose

This note closes the browser E2E infrastructure blocker caused by old scripts importing `../frontend/node_modules/playwright` directly.

Active browser E2E scripts now use:

- `scripts/lib/playwright_runtime.mjs`
- package import `playwright` when available
- optional `QLANALYSER_PLAYWRIGHT_MODULE_DIR`
- system Microsoft Edge fallback through `QLANALYSER_BROWSER_EXECUTABLE` or the standard Windows Edge paths

## Required QA Machine Setup

One of the following must be true before running browser E2E scripts with plain Node:

1. Project dependencies are installed and `playwright` is resolvable from the repository.
2. `QLANALYSER_PLAYWRIGHT_MODULE_DIR` points to a local Playwright package directory.
3. The runner wraps execution with a Node module search path that exposes a complete Playwright installation.

The browser executable can be configured with:

```powershell
$env:QLANALYSER_BROWSER_EXECUTABLE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
```

If unset, the helper checks common Microsoft Edge installation paths.

## Smoke Command

```powershell
node --check scripts/lib/playwright_runtime.mjs
node scripts/acceptance_customer_sidebar_navigation_governance.mjs
```

If Playwright is not resolvable, the helper fails with a clear setup error instead of silently importing a stale project-local path.

## Scope Boundary

This runner setup does not install dependencies, does not change router/Headroom/gateway/IPC/model routes, and does not touch TimeChart or the epilepsy source workbench.
