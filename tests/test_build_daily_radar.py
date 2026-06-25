import datetime as dt
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


def load_build_daily_radar():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "build_daily_radar.py"
    spec = importlib.util.spec_from_file_location("build_daily_radar", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DailyRadarTests(unittest.TestCase):
    def test_parse_rss_news_items_extracts_title_link_and_summary(self):
        radar = load_build_daily_radar()
        rss = b"""<?xml version="1.0"?>
        <rss version="2.0">
          <channel>
            <item>
              <title>New AI agent framework launches</title>
              <link>https://example.com/news</link>
              <pubDate>Wed, 24 Jun 2026 00:30:00 GMT</pubDate>
              <description><![CDATA[Agent tooling now supports MCP and evaluations.]]></description>
            </item>
          </channel>
        </rss>
        """

        items = radar.parse_rss_items("AI News", ["news"], rss, "news")

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "New AI agent framework launches")
        self.assertEqual(items[0]["url"], "https://example.com/news")
        self.assertEqual(items[0]["section"], "news")
        self.assertIn("MCP", items[0]["summary"])
        self.assertIn("agents", items[0]["tags"])
        self.assertNotIn("ai_coding", items[0]["tags"])

    def test_keyword_matching_does_not_match_inside_words(self):
        radar = load_build_daily_radar()

        item = radar.build_item(
            section="news",
            source="News",
            title="AI evaluation guide",
            url="https://example.com/guide",
            published_at="2026-06-24T00:00:00Z",
            summary="A practical evaluation guide for contact center agents.",
            tags=["news"],
        )

        self.assertIn("evals", item["tags"])
        self.assertNotIn("ai_coding", item["tags"])

    def test_parse_remotive_jobs_normalizes_ai_job_fields(self):
        radar = load_build_daily_radar()
        payload = {
            "jobs": [
                {
                    "title": "Senior AI Engineer",
                    "company_name": "Example AI",
                    "candidate_required_location": "Worldwide",
                    "url": "https://example.com/job",
                    "publication_date": "2026-06-24T00:00:00Z",
                    "description": "Build RAG agents with Python, TypeScript, vector databases, MCP, and evaluation pipelines.",
                    "tags": ["python", "ai"],
                }
            ]
        }

        jobs = radar.parse_remotive_jobs("Remotive AI", ["jobs"], json.dumps(payload).encode())

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["section"], "jobs")
        self.assertEqual(jobs[0]["company"], "Example AI")
        self.assertEqual(jobs[0]["location"], "Worldwide")
        self.assertEqual(jobs[0]["location_scope"], "global_remote")
        self.assertIn("rag", jobs[0]["tags"])
        self.assertIn("evals", jobs[0]["tags"])
        self.assertIn("Python", jobs[0]["skills"])
        self.assertIn("MCP", jobs[0]["skills"])
        self.assertIn("Build RAG agents", jobs[0]["jd"])

    def test_jobs_are_filtered_to_target_regions(self):
        radar = load_build_daily_radar()
        payload = {
            "jobs": [
                {
                    "title": "AI Engineer Brazil",
                    "company_name": "Brazil AI",
                    "candidate_required_location": "Brazil",
                    "url": "https://example.com/brazil",
                    "publication_date": "2026-06-24T00:00:00Z",
                    "description": "Build LLM agents with Python.",
                    "tags": ["ai"],
                },
                {
                    "title": "AI Engineer Singapore Remote",
                    "company_name": "SEA AI",
                    "candidate_required_location": "Singapore, Remote",
                    "url": "https://example.com/singapore",
                    "publication_date": "2026-06-24T00:00:00Z",
                    "description": "Remote role building LLM agents with LangChain and vector databases.",
                    "tags": ["ai"],
                },
                {
                    "title": "AI Engineer Shanghai",
                    "company_name": "China AI",
                    "candidate_required_location": "Shanghai, China",
                    "url": "https://example.com/shanghai",
                    "publication_date": "2026-06-24T00:00:00Z",
                    "description": "Onsite role building multimodal AI products with PyTorch.",
                    "tags": ["ai"],
                },
                {
                    "title": "AI Engineer Global",
                    "company_name": "Global AI",
                    "candidate_required_location": "Worldwide",
                    "url": "https://example.com/worldwide",
                    "publication_date": "2026-06-24T00:00:00Z",
                    "description": "Global remote role building RAG systems with MCP and evaluations.",
                    "tags": ["ai"],
                },
            ]
        }

        jobs = radar.parse_remotive_jobs("Remotive AI", ["jobs"], json.dumps(payload).encode())

        self.assertEqual([job["title"] for job in jobs], [
            "AI Engineer Singapore Remote",
            "AI Engineer Shanghai",
            "AI Engineer Global",
        ])
        self.assertEqual(jobs[0]["location_scope"], "southeast_asia_remote")
        self.assertEqual(jobs[1]["location_scope"], "china_mainland_onsite")
        self.assertEqual(jobs[2]["location_scope"], "global_remote")

    def test_jobs_without_extractable_skills_are_skipped(self):
        radar = load_build_daily_radar()
        payload = {
            "jobs": [
                {
                    "title": "AI Operations Lead",
                    "company_name": "Example",
                    "candidate_required_location": "Worldwide",
                    "url": "https://example.com/ops",
                    "publication_date": "2026-06-24T00:00:00Z",
                    "description": "Global remote role coordinating teams and stakeholders.",
                    "tags": ["ai"],
                }
            ]
        }

        jobs = radar.parse_remotive_jobs("Remotive AI", ["jobs"], json.dumps(payload).encode())

        self.assertEqual(jobs, [])

    def test_hn_jobs_skip_show_hn_items_without_hiring_language(self):
        radar = load_build_daily_radar()
        payload = {
            "hits": [
                {
                    "title": "Show HN: Open Computer Use",
                    "url": "https://example.com/show",
                    "created_at": "2026-06-24T00:00:00Z",
                    "story_text": "An open-source devtool for running AI-generated code. We are hiring engineers for global remote work.",
                    "_tags": ["story"],
                },
                {
                    "title": "We are hiring AI Engineer",
                    "url": "https://example.com/hiring",
                    "created_at": "2026-06-24T00:00:00Z",
                    "story_text": "Global remote role building agents with Python.",
                    "_tags": ["story"],
                },
            ]
        }

        jobs = radar.parse_hn_jobs("Hacker News AI Hiring", ["jobs"], json.dumps(payload).encode())

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["title"], "We are hiring AI Engineer")
        self.assertEqual(jobs[0]["location_scope"], "global_remote")

    def test_parse_github_search_results_normalizes_repo_metadata(self):
        radar = load_build_daily_radar()
        payload = {
            "items": [
                {
                    "full_name": "example/agent-kit",
                    "html_url": "https://github.com/example/agent-kit",
                    "description": "A TypeScript framework for AI agents and tool use.",
                    "stargazers_count": 1234,
                    "language": "TypeScript",
                    "updated_at": "2026-06-24T00:00:00Z",
                    "topics": ["agents", "llm"],
                }
            ]
        }

        repos = radar.parse_github_repos("GitHub AI", ["github"], json.dumps(payload).encode())

        self.assertEqual(len(repos), 1)
        self.assertEqual(repos[0]["section"], "github_repos")
        self.assertEqual(repos[0]["repo"], "example/agent-kit")
        self.assertEqual(repos[0]["stars"], 1234)
        self.assertEqual(repos[0]["language"], "TypeScript")
        self.assertIn("agents", repos[0]["tags"])

    def test_build_daily_record_enforces_minimum_counts_and_cross_signals(self):
        radar = load_build_daily_radar()
        now = dt.datetime(2026, 6, 24, tzinfo=dt.timezone.utc)
        items = []
        for index in range(5):
            items.append(
                radar.build_item(
                    section="jobs",
                    source="Job Source",
                    title=f"AI Engineer {index}",
                    url=f"https://example.com/jobs/{index}",
                    published_at=now.isoformat(),
                    summary="Build agentic RAG systems with MCP and evaluations.",
                    tags=["jobs"],
                    extra={"company": "Example", "location": "Remote"},
                )
            )
            items.append(
                radar.build_item(
                    section="news",
                    source="News Source",
                    title=f"AI Agent News {index}",
                    url=f"https://example.com/news/{index}",
                    published_at=now.isoformat(),
                    summary="MCP support grows across agent tools.",
                    tags=["news"],
                )
            )
            items.append(
                radar.build_item(
                    section="github_repos",
                    source="GitHub",
                    title=f"example/agent-kit-{index}",
                    url=f"https://github.com/example/agent-kit-{index}",
                    published_at=now.isoformat(),
                    summary="Open source AI agent framework with RAG.",
                    tags=["github"],
                    extra={"repo": f"example/agent-kit-{index}", "stars": 100 + index, "language": "Python"},
                )
            )

        record = radar.build_daily_record(
            items=items,
            errors=[],
            config=radar.DEFAULT_CONFIG,
            now=now,
        )

        self.assertEqual(record["coverage"]["jobs"]["count"], 5)
        self.assertEqual(record["coverage"]["news"]["count"], 5)
        self.assertEqual(record["coverage"]["github_repos"]["count"], 5)
        self.assertEqual(record["coverage"]["knowledge_trends"]["count"], 5)
        self.assertTrue(record["cross_signals"])
        self.assertEqual(record["coverage"]["jobs"]["status"], "ok")

    def test_english_job_jd_gets_bilingual_report_fields(self):
        radar = load_build_daily_radar()
        job = radar.build_item(
            section="jobs",
            source="Job Source",
            title="AI Engineer",
            url="https://example.com/job",
            published_at="2026-06-24T00:00:00Z",
            summary="Build RAG agents with Python and MCP.",
            tags=["jobs"],
            extra={"company": "Example", "location": "Worldwide"},
        )
        record = radar.build_daily_record([job], [], radar.DEFAULT_CONFIG, dt.datetime(2026, 6, 24, tzinfo=dt.timezone.utc))

        report = radar.render_jobs_report_zh(record)

        self.assertEqual(record["jobs"][0]["jd_language"], "en")
        self.assertIn("- JD 原文摘录：Build RAG agents with Python and MCP.", report)
        self.assertIn("- JD 中文解读：该岗位要求的核心技能包括 Python、RAG、MCP、Agents", report)

    def test_chinese_job_jd_does_not_add_translation_line(self):
        radar = load_build_daily_radar()
        job = radar.build_item(
            section="jobs",
            source="Job Source",
            title="AI 工程师",
            url="https://example.com/job-cn",
            published_at="2026-06-24T00:00:00Z",
            summary="负责在上海现场构建 RAG 智能体系统，使用 Python、MCP 和评测流水线。",
            tags=["jobs"],
            extra={"company": "Example", "location": "Shanghai, China"},
        )
        record = radar.build_daily_record([job], [], radar.DEFAULT_CONFIG, dt.datetime(2026, 6, 24, tzinfo=dt.timezone.utc))

        report = radar.render_jobs_report_zh(record)

        self.assertEqual(record["jobs"][0]["jd_language"], "zh")
        self.assertIn("- JD 摘要：该岗位 JD 提到：负责在上海现场构建 RAG 智能体系统", report)
        self.assertNotIn("JD 中文解读", report)
        self.assertNotIn("JD 原文摘录", report)

    def test_write_outputs_creates_daily_json_latest_and_chinese_report(self):
        radar = load_build_daily_radar()
        now = dt.datetime(2026, 6, 24, tzinfo=dt.timezone.utc)
        job = radar.build_item(
            section="jobs",
            source="Job Source",
            title="AI Engineer",
            url="https://example.com/job",
            published_at=now.isoformat(),
            summary="Build RAG agents with MCP.",
            tags=["jobs", "agents"],
            extra={"company": "Example", "location": "Remote"},
        )
        news = radar.build_item(
            section="news",
            source="News Source",
            title="AI agent framework launches",
            url="https://example.com/news",
            published_at=now.isoformat(),
            summary="Agent tooling now supports MCP and evaluations.",
            tags=["news", "agents"],
        )
        repo = radar.build_item(
            section="github_repos",
            source="GitHub",
            title="example/agent-kit",
            url="https://github.com/example/agent-kit",
            published_at=now.isoformat(),
            summary="Open source AI agent framework with RAG.",
            tags=["github", "agents"],
            extra={"repo": "example/agent-kit", "stars": 1234, "language": "Python"},
        )
        record = radar.build_daily_record([job, news, repo], [], radar.DEFAULT_CONFIG, now)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir)
            stale_english_report = output_root / "dist" / "daily-report.md"
            stale_english_report.parent.mkdir(parents=True, exist_ok=True)
            stale_english_report.write_text("stale english report", encoding="utf-8")

            radar.write_outputs(record, output_root)

            daily_json = output_root / "data" / "daily" / "2026-06-24.json"
            latest_json = output_root / "data" / "latest.json"
            report_dir = output_root / "dist" / "reports"
            jobs_report = report_dir / "2026-06-24-jobs-report.zh.md"
            news_report = report_dir / "2026-06-24-news-report.zh.md"
            github_report = report_dir / "2026-06-24-github-report.zh.md"
            index_report = report_dir / "2026-06-24-index.zh.md"
            nested_jobs_report = report_dir / "2026-06-24" / "2026-06-24-jobs-report.zh.md"
            latest_jobs_report = output_root / "dist" / "latest" / "jobs-report.zh.md"
            old_single_report = output_root / "dist" / "daily-report.zh.md"
            english_report = output_root / "dist" / "daily-report.md"

            self.assertTrue(daily_json.exists())
            self.assertTrue(latest_json.exists())
            self.assertTrue(jobs_report.exists())
            self.assertTrue(news_report.exists())
            self.assertTrue(github_report.exists())
            self.assertTrue(index_report.exists())
            self.assertTrue(latest_jobs_report.exists())
            self.assertFalse(nested_jobs_report.exists())
            self.assertFalse(old_single_report.exists())
            self.assertFalse(english_report.exists())
            self.assertEqual(json.loads(latest_json.read_text(encoding="utf-8"))["date"], "2026-06-24")

            jobs_text = jobs_report.read_text(encoding="utf-8")
            news_text = news_report.read_text(encoding="utf-8")
            github_text = github_report.read_text(encoding="utf-8")
            index_text = index_report.read_text(encoding="utf-8")

            self.assertIn("# AI 岗位趋势 - 2026-06-24", jobs_text)
            self.assertIn("- 匹配范围：Global Remote", jobs_text)
            self.assertIn("- 技能点：RAG、MCP", jobs_text)
            self.assertIn("- JD 原文摘录：Build RAG agents with MCP.", jobs_text)
            self.assertIn("- JD 中文解读：该岗位要求的核心技能包括 RAG、MCP、Agents", jobs_text)
            self.assertIn("- 关注点：该岗位信号与智能体、RAG、MCP 相关", jobs_text)
            self.assertNotIn("## 2. AI 新闻动态", jobs_text)

            self.assertIn("# AI 新闻动态 - 2026-06-24", news_text)
            self.assertIn("- 摘要：这条动态与智能体、MCP、评测与可观测性相关", news_text)
            self.assertNotIn("## 3. GitHub 热门项目", news_text)

            self.assertIn("# GitHub 热门项目 - 2026-06-24", github_text)
            self.assertIn("- 简介：这个项目与智能体、RAG 相关", github_text)

            self.assertIn("# AI Ecosystem Radar - 2026-06-24", index_text)
            self.assertIn("2026-06-24-jobs-report.zh.md", index_text)
            self.assertIn("2026-06-24-news-report.zh.md", index_text)
            self.assertIn("2026-06-24-github-report.zh.md", index_text)
            self.assertIn("说明主题已经同时出现在", index_text)
            self.assertNotIn("appears in", index_text)



if __name__ == "__main__":
    unittest.main()
