# GitHub Issues – Agentic Guidelines

These guidelines define how autonomous agents should interact with GitHub Issues in this repository.

## Purpose

This repository contains the X-Wing Miniatures icon font. Issues may cover:

- Glyph additions or corrections
- Build-pipeline improvements
- Tournament data collection (automated scraping via GitHub Actions)

---

## Issue Lifecycle

| State | Meaning |
|---|---|
| `open` | Not yet triaged or in progress |
| `in progress` | Actively being worked on (assign to yourself) |
| `review` | Work complete; waiting for human review |
| `closed` | Done or rejected |

---

## Agentic Behavior Rules

### 1. Always read before acting
Before making changes, read the full issue body **and** all existing comments. Understand the intent and any partial work already done.

### 2. One issue → one branch → one PR
Create a dedicated feature branch per issue (`copilot/<issue-slug>`) and open exactly one pull request that closes the issue.

### 3. Minimal-change principle
Make the **smallest possible** set of changes that fully address the issue. Do not refactor unrelated code.

### 4. Deduplication
For tournament data collection tasks, always deduplicate records by **tournament ID** before persisting results. Never re-insert a record whose ID is already present in the output file.

### 5. Platform defaults
The following platforms are **excluded by default** unless explicitly enabled in the workflow inputs:

- `listfortress` – considered unmaintained; opt-in only

Enabled by default:
- `longshanks`
- `challonge`
- `bcp` (Best Coast Pairings)

### 6. Time range
Time ranges for data collection are expressed in **whole days** (integer ≥ 1). The default is `7` days (rolling week). Maximum allowed value is `365`.

### 7. Tests
- If the repository has an existing test suite, add or update tests for every functional change.
- Scripts under `scripts/` must be executable (`chmod +x`) and include a `--help` flag.

### 8. Secrets
Never hard-code API keys, tokens, or credentials. Use GitHub Actions secrets (e.g., `${{ secrets.BCP_API_KEY }}`) and document required secrets in the issue or PR description.

### 9. Commit messages
Use the imperative mood and reference the issue number:

```
feat: add BCP platform support (#42)
fix: deduplicate by ID before write (#43)
```

### 10. Definition of Done
A task is complete when:
1. Code changes are committed and pushed.
2. All existing CI checks pass.
3. The PR description explains *what* changed and *why*.
4. A human reviewer has approved (or the issue owner has confirmed).
