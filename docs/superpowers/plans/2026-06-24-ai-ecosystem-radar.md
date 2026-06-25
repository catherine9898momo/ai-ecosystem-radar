# AI Ecosystem Radar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone GitHub Action project that creates a daily AI ecosystem radar with repository-local data storage.

**Architecture:** Use one standard-library Python script for collection, normalization, trend extraction, report rendering, and output writing. Keep source definitions in JSON and use GitHub Actions to run tests, build the radar, upload artifacts, and commit `data/` plus `dist/` back to the repository.

**Tech Stack:** Python 3.12 standard library, unittest, GitHub Actions, RSS/Atom, public JSON APIs, GitHub Search API.

## Global Constraints

- Project directory: `ai-ecosystem-radar`.
- Schedule: `cron: "0 0 * * *"` for 08:00 Beijing time.
- Storage: GitHub repository files under `data/` and `dist/`.
- Minimum daily target: at least 5 jobs, 5 news items, 5 GitHub projects, and 5 knowledge trends when sources provide enough data.
- Do not fabricate source items; record coverage gaps and source errors.

---

### Task 1: Tests And Core Collector

**Files:**
- Create: `tests/test_build_daily_radar.py`
- Create: `scripts/build_daily_radar.py`

**Interfaces:**
- Produces: `parse_rss_items(source_name: str, tags: list[str], data: bytes, section: str) -> list[dict]`
- Produces: `parse_remotive_jobs(source_name: str, tags: list[str], data: bytes) -> list[dict]`
- Produces: `parse_github_repos(source_name: str, tags: list[str], data: bytes) -> list[dict]`
- Produces: `build_daily_record(items: list[dict], errors: list[dict], config: dict, now: datetime | None = None) -> dict`
- Produces: `write_outputs(record: dict, output_root: Path) -> None`

- [x] **Step 1: Write failing parser and output tests**

Run: `python3 -m unittest tests/test_build_daily_radar.py`

Expected: FAIL because `scripts/build_daily_radar.py` does not exist.

- [x] **Step 2: Implement the collector script**

Implement RSS parsing, Remotive parsing, RemoteOK parsing, Hacker News parsing, GitHub search parsing, item normalization, knowledge trend extraction, cross-signal generation, coverage tracking, and report output.

- [ ] **Step 3: Run tests**

Run: `python3 -m unittest tests/test_build_daily_radar.py`

Expected: PASS.

### Task 2: Configuration, Workflow, And Docs

**Files:**
- Create: `config/sources.json`
- Create: `.github/workflows/daily-ai-ecosystem-radar.yml`
- Create: `README.md`
- Create: `.gitignore`
- Create: `docs/superpowers/specs/2026-06-24-ai-ecosystem-radar-design.md`
- Create: `docs/superpowers/plans/2026-06-24-ai-ecosystem-radar.md`

**Interfaces:**
- Consumes: `scripts/build_daily_radar.py`
- Produces: a manually runnable and scheduled GitHub Actions workflow.

- [x] **Step 1: Add source configuration**

Add public AI job, AI news, and GitHub repository sources in `config/sources.json`.

- [x] **Step 2: Add GitHub Action**

Add a workflow that runs tests, builds the radar, uploads artifacts, and commits `data/` plus `dist/`.

- [x] **Step 3: Add README and project docs**

Document outputs, schedule, local commands, source configuration, and coverage behavior.

- [ ] **Step 4: Run full verification**

Run: `python3 -m unittest discover -s tests`

Expected: PASS.
