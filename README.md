# AI Ecosystem Radar

Daily AI ecosystem intelligence for jobs, news, GitHub projects, and knowledge trends.

The project is intentionally lightweight: Python standard library only, GitHub Actions for scheduling, and GitHub repository files as the database.

## What It Produces

Every run writes:

- `data/daily/YYYY-MM-DD.json`
- `data/latest.json`
- `dist/reports/YYYY-MM-DD-index.zh.md`
- `dist/reports/YYYY-MM-DD-jobs-report.zh.md`
- `dist/reports/YYYY-MM-DD-news-report.zh.md`
- `dist/reports/YYYY-MM-DD-github-report.zh.md`
- `dist/latest/index.zh.md`
- `dist/latest/jobs-report.zh.md`
- `dist/latest/news-report.zh.md`
- `dist/latest/github-report.zh.md`

The daily JSON is the canonical structured record. The dated Markdown files are the archived Chinese reading reports; `dist/latest/` mirrors the newest report set for quick access.

## Daily Schedule

The workflow runs at `0 0 * * *` UTC, which is 08:00 in Beijing time.

It can also be started manually from the GitHub Actions tab with `workflow_dispatch`.

## Report Structure

The Chinese reports are split into:

1. `index.zh.md`: daily summary, knowledge trends, cross signals, and coverage
2. `jobs-report.zh.md`: AI job trends, target location scope, skills, and JD excerpts
3. `news-report.zh.md`: AI news items
4. `github-report.zh.md`: GitHub hot projects

Each core section targets at least 5 items per day. If a source fails or a section has fewer than 5 items, the run still writes the report and records warnings in `coverage`, `warnings`, and `errors`.

## Job Filtering

The job section only keeps roles in these target scopes:

- Mainland China onsite roles
- Southeast Asia remote roles
- Global remote roles, including broadly remote US/Europe/Americas listings

Specific non-target local roles, such as Brazil-only listings, are filtered out. Each retained job stores the extracted `location_scope`, `location_scope_label`, full-ish `jd` text, `jd_excerpt`, `jd_language`, optional `jd_excerpt_zh`, and concrete `skills` detected from the JD. English JDs are shown with the original excerpt plus a Chinese interpretation; Chinese JDs are shown as-is without a duplicate translation.

## Run Locally

```bash
python3 -m unittest discover -s tests
python3 scripts/build_daily_radar.py
```

Open `dist/latest/index.zh.md` after the build, or browse the dated archive under `dist/reports/`. The project intentionally keeps only Chinese Markdown reports.

## Configure Sources

Edit `config/sources.json`.

Supported source types:

- `rss`
- `remotive`
- `remoteok`
- `hn_algolia`
- `github_search`

For GitHub API sources, the GitHub Action passes `GITHUB_TOKEN` automatically to improve rate limits.
