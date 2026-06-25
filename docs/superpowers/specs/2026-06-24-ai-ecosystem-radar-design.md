# AI Ecosystem Radar Design

## Goal

Create a standalone daily AI ecosystem radar that runs every morning at 08:00 Beijing time, collects AI jobs, AI news, hot GitHub projects, and AI knowledge trend signals, then stores structured daily data inside the GitHub repository.

## Scope

The project is separate from AI Investment Radar. It may reuse the same engineering shape: a Python collector, configurable sources, Markdown reports, structured JSON output, tests, and a GitHub Actions workflow.

## Data Contract

Each run writes:

- `data/daily/YYYY-MM-DD.json`
- `data/latest.json`
- `dist/daily-report.zh.md`

The JSON record contains:

- `date`
- `timezone`
- `generated_at`
- `coverage`
- `summary`
- `jobs`
- `news`
- `github_repos`
- `knowledge_trends`
- `cross_signals`
- `errors`
- `warnings`

Each core section targets at least five records. The system must not invent source items. If source coverage is insufficient, it records the shortage in `coverage` and `warnings`.

## Sources

Jobs use public job APIs and hiring feeds such as Remotive, RemoteOK, and Hacker News Algolia search. News uses RSS feeds, primarily Google News RSS searches. GitHub projects use GitHub Search API queries. Knowledge trends are derived from the collected jobs, news, and repository text using a configured trend watchlist.

## Report

The report is Chinese-only and starts with a daily summary, then jobs, news, GitHub projects, knowledge trends, cross signals, and coverage. The report should be readable in three to five minutes and link back to the raw source items for follow-up.

## Scheduling

GitHub Actions uses `cron: "0 0 * * *"`, which corresponds to 08:00 Asia/Shanghai. The workflow also supports manual dispatch.

## Error Handling

Source failures do not fail the whole report. The run stores successful results, records source errors, and flags coverage gaps. Tests should cover parsers, data shaping, coverage, cross signals, and output writing.
