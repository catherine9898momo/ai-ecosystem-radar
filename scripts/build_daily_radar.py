#!/usr/bin/env python3
import datetime as dt
import email.utils
import hashlib
import html
import json
import os
import re
import textwrap
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "sources.json"


TAG_KEYWORDS = {
    "agents": ["agent", "agentic", "tool use", "function calling"],
    "rag": ["rag", "retrieval", "vector", "embedding"],
    "mcp": ["mcp", "model context protocol"],
    "evals": ["evaluation", "evaluations", "eval", "evals", "observability", "benchmark"],
    "ai_coding": ["coding", "code assistant", "developer tool", "ide"],
    "multimodal": ["multimodal", "vision", "audio", "video"],
    "llmops": ["llmops", "deployment", "monitoring", "inference"],
    "fine_tuning": ["fine-tuning", "finetuning", "lora", "adapter"],
    "slm": ["small language model", "slm", "on-device", "edge ai"],
    "ai_infra": ["gpu", "inference", "serving", "cuda", "kubernetes"],
}


TAG_LABELS_ZH = {
    "agents": "智能体",
    "rag": "RAG",
    "mcp": "MCP",
    "evals": "评测与可观测性",
    "ai_coding": "AI 编程",
    "multimodal": "多模态",
    "llmops": "LLMOps",
    "fine_tuning": "微调",
    "slm": "小模型与端侧 AI",
    "ai_infra": "AI 基础设施",
    "llm": "大模型",
    "models": "模型发布",
    "policy": "政策监管",
    "remote": "远程岗位",
}

TAG_PRIORITY = [
    "agents",
    "rag",
    "mcp",
    "evals",
    "ai_coding",
    "multimodal",
    "llmops",
    "fine_tuning",
    "slm",
    "ai_infra",
    "llm",
    "models",
    "policy",
    "remote",
]

SECTION_LABELS_ZH = {
    "jobs": "岗位",
    "news": "新闻",
    "github_repos": "GitHub 项目",
    "knowledge_trends": "知识趋势",
}

STATUS_LABELS_ZH = {
    "ok": "达标",
    "insufficient": "不足",
    "daily_evidence": "今日有直接证据",
    "watchlist": "观察清单",
}

TREND_SUMMARY_ZH = {
    "Agentic workflows": "智能体工作流关注模型如何规划任务、调用工具并完成多步骤工作。",
    "Retrieval-Augmented Generation": "RAG 关注如何把外部知识检索、向量库和引用证据接入大模型应用。",
    "Model Context Protocol": "MCP 关注 AI 应用如何用标准化方式连接工具、数据源和外部系统。",
    "AI coding workflows": "AI 编程工作流关注 IDE、CLI、代码审查和自动化开发中的模型协作方式。",
    "LLM evaluation and observability": "评测与可观测性关注如何测试、追踪和监控生产环境中的大模型行为。",
    "Multimodal AI": "多模态 AI 关注文本、图像、音频和视频等多种输入输出的统一处理。",
    "Small and on-device models": "小模型与端侧 AI 关注本地、边缘设备和隐私敏感场景中的模型部署。",
}


def keyword_matches(text: str, keyword: str) -> bool:
    pattern = r"(?<![a-z0-9])" + re.escape(keyword.lower()) + r"(?![a-z0-9])"
    return re.search(pattern, text) is not None


def is_ai_related(text: str) -> bool:
    ai_terms = [
        "ai",
        "artificial intelligence",
        "llm",
        "large language model",
        "machine learning",
        "generative",
        "gpt",
        "agent",
        "rag",
        "nlp",
        "computer vision",
    ]
    lower = text.lower()
    return any(keyword_matches(lower, term) for term in ai_terms)


MAINLAND_CHINA_TERMS = [
    "china",
    "mainland china",
    "beijing",
    "shanghai",
    "shenzhen",
    "guangzhou",
    "hangzhou",
    "chengdu",
    "wuhan",
    "nanjing",
    "suzhou",
    "xiamen",
    "中国",
    "北京",
    "上海",
    "深圳",
    "广州",
    "杭州",
    "成都",
]

SOUTHEAST_ASIA_TERMS = [
    "southeast asia",
    "sea",
    "singapore",
    "malaysia",
    "thailand",
    "vietnam",
    "indonesia",
    "philippines",
    "jakarta",
    "bangkok",
    "kuala lumpur",
    "manila",
    "ho chi minh",
    "新加坡",
    "马来西亚",
    "泰国",
    "越南",
    "印尼",
    "菲律宾",
]

GLOBAL_REMOTE_TERMS = [
    "worldwide",
    "global",
    "anywhere",
    "fully remote",
    "remote",
    "americas",
    "europe",
    "emea",
    "usa timezones",
    "us timezones",
    "north america",
]

LOCATION_SCOPE_LABELS = {
    "china_mainland_onsite": "中国大陆现场",
    "southeast_asia_remote": "东南亚 Remote",
    "global_remote": "Global Remote",
}

SKILL_KEYWORDS = [
    ("Python", ["python"]),
    ("TypeScript", ["typescript", "type script"]),
    ("JavaScript", ["javascript"]),
    ("PyTorch", ["pytorch"]),
    ("TensorFlow", ["tensorflow"]),
    ("LangChain", ["langchain"]),
    ("LlamaIndex", ["llamaindex", "llama index"]),
    ("DSPy", ["dspy"]),
    ("RAG", ["rag", "retrieval augmented generation", "retrieval-augmented generation"]),
    ("向量数据库", ["vector database", "vector db", "vector databases", "embedding database"]),
    ("MCP", ["mcp", "model context protocol"]),
    ("Agents", ["agent", "agents", "agentic"]),
    ("评测", ["evaluation", "evaluations", "eval", "evals", "benchmark"]),
    ("可观测性", ["observability", "tracing", "monitoring"]),
    ("微调", ["fine-tuning", "finetuning", "lora"]),
    ("Prompt Engineering", ["prompt engineering", "prompting"]),
    ("vLLM", ["vllm"]),
    ("CUDA", ["cuda"]),
    ("Docker", ["docker"]),
    ("Kubernetes", ["kubernetes", "k8s"]),
    ("FastAPI", ["fastapi"]),
    ("SQL", ["sql", "postgres", "mysql"]),
]


def has_any_term(text: str, terms: list[str]) -> bool:
    lower = text.lower()
    return any(keyword_matches(lower, term) for term in terms)


def detect_job_location_scope(location: str, text: str = "") -> str | None:
    location_text = (location or "").strip()
    combined = f"{location_text} {text}".lower()
    location_lower = location_text.lower()
    remote_hint = has_any_term(combined, ["remote", "distributed", "work from home", "anywhere", "global", "worldwide"])

    if has_any_term(location_lower, MAINLAND_CHINA_TERMS):
        if not remote_hint or has_any_term(combined, ["onsite", "on-site", "hybrid", "现场"]):
            return "china_mainland_onsite"

    if has_any_term(location_lower, SOUTHEAST_ASIA_TERMS) and remote_hint:
        return "southeast_asia_remote"

    if has_any_term(location_lower, GLOBAL_REMOTE_TERMS):
        return "global_remote"

    if location_lower in {"", "remote"} and remote_hint:
        return "global_remote"

    return None


def extract_skills(text: str) -> list[str]:
    lower = (text or "").lower()
    skills = []
    for label, keywords in SKILL_KEYWORDS:
        if any(keyword_matches(lower, keyword) for keyword in keywords):
            skills.append(label)
    return skills[:12]


def detect_text_language(text: str) -> str:
    if not text:
        return "unknown"
    zh_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    letters = len(re.findall(r"[A-Za-z]", text))
    if zh_chars >= 12 and zh_chars >= letters * 0.15:
        return "zh"
    if letters >= 20:
        return "en"
    return "unknown"


def jd_chinese_interpretation(item: dict) -> str:
    skills = item.get("skills") or []
    skill_text = "、".join(skills[:8]) if skills else "未提取到明确技能点"
    scope = item.get("location_scope_label") or "未匹配"
    company = item.get("company") or "该公司"
    return f"该岗位要求的核心技能包括 {skill_text}；岗位范围为 {scope}；发布方为 {company}。"


def enrich_job_item(item: dict) -> None:
    jd = strip_html(item.get("jd") or item.get("summary") or "")
    item["jd"] = jd[:5000]
    item["jd_excerpt"] = short(jd, 420) if jd else "未抓取到 JD 描述。"
    item["jd_language"] = detect_text_language(jd)
    skills = item.get("skills") or extract_skills(f"{item.get('title', '')} {jd} {' '.join(item.get('tags', []))}")
    item["skills"] = skills
    scope = item.get("location_scope") or detect_job_location_scope(item.get("location", ""), f"{item.get('title', '')} {jd}")
    if scope:
        item["location_scope"] = scope
        item["location_scope_label"] = LOCATION_SCOPE_LABELS[scope]
    if item["jd_language"] == "en":
        item["jd_excerpt_zh"] = jd_chinese_interpretation(item)


DEFAULT_CONFIG = {
    "timezone": "Asia/Shanghai",
    "minimum_items_per_section": 5,
    "max_items_per_section": 10,
    "knowledge_trends": [
        {
            "name": "Agentic workflows",
            "keywords": ["agent", "agentic", "tool use", "function calling"],
            "summary": "Agents that can plan, call tools, and complete multi-step work.",
        },
        {
            "name": "Retrieval-Augmented Generation",
            "keywords": ["rag", "retrieval", "vector", "embedding"],
            "summary": "Knowledge-grounded LLM systems built on retrieval, vector search, and citations.",
        },
        {
            "name": "Model Context Protocol",
            "keywords": ["mcp", "model context protocol"],
            "summary": "A tool and context integration pattern for connecting AI apps to external systems.",
        },
        {
            "name": "AI coding workflows",
            "keywords": ["coding", "code assistant", "developer tool", "ide"],
            "summary": "AI-assisted software development workflows across IDEs, CLIs, and review tools.",
        },
        {
            "name": "LLM evaluation and observability",
            "keywords": ["evaluation", "eval", "observability", "benchmark"],
            "summary": "Testing, scoring, tracing, and monitoring production LLM behavior.",
        },
        {
            "name": "Multimodal AI",
            "keywords": ["multimodal", "vision", "audio", "video"],
            "summary": "Models and applications that combine text, image, audio, and video inputs.",
        },
        {
            "name": "Small and on-device models",
            "keywords": ["small language model", "slm", "on-device", "edge ai"],
            "summary": "Smaller models optimized for local, edge, or privacy-sensitive deployment.",
        },
    ],
    "sources": {
        "jobs": [],
        "news": [],
        "github_repos": [],
    },
}


def fetch_url(url: str) -> bytes:
    headers = {
        "User-Agent": "ai-ecosystem-radar/0.1 (+https://github.com/)",
        "Accept": "application/json, application/rss+xml, application/atom+xml, text/xml, */*",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token and "api.github.com" in url:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def strip_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = html.unescape(value)
    if "â" in value or "Ã" in value:
        try:
            value = value.encode("latin1").decode("utf-8")
        except UnicodeError:
            pass
    return re.sub(r"\s+", " ", value).strip()


def parse_date(value: str) -> str:
    if not value:
        return ""
    value = value.strip()
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed:
            return parsed.astimezone(dt.timezone.utc).isoformat()
    except Exception:
        pass
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc).isoformat()
    except Exception:
        return value


def child_text(element: ET.Element, names: list[str]) -> str:
    for name in names:
        found = element.find(name)
        if found is not None and found.text:
            return found.text.strip()
    return ""


def atom_link(entry: ET.Element) -> str:
    for link in entry.findall("{http://www.w3.org/2005/Atom}link"):
        href = link.attrib.get("href")
        if href:
            return href
    return ""


def classify_tags(text: str, seed_tags: list[str] | None = None) -> list[str]:
    lower = text.lower()
    tags = set(seed_tags or [])
    for tag, keywords in TAG_KEYWORDS.items():
        if any(keyword_matches(lower, keyword) for keyword in keywords):
            tags.add(tag)
    return sorted(tags)


def stable_id(section: str, title: str, url: str) -> str:
    digest = hashlib.sha1(f"{section}|{title}|{url}".encode("utf-8")).hexdigest()
    return digest[:16]


def build_item(
    section: str,
    source: str,
    title: str,
    url: str,
    published_at: str,
    summary: str,
    tags: list[str] | None = None,
    extra: dict | None = None,
) -> dict:
    title = strip_html(title)
    summary = strip_html(summary)
    all_tags = classify_tags(f"{title} {summary}", tags)
    item = {
        "id": stable_id(section, title, url),
        "section": section,
        "source": source,
        "title": title,
        "url": url,
        "published_at": parse_date(published_at),
        "summary": summary[:700],
        "tags": all_tags,
        "relevance_score": relevance_score(title, summary, all_tags),
    }
    if extra:
        item.update(extra)
    if section == "jobs":
        enrich_job_item(item)
    return item


def relevance_score(title: str, summary: str, tags: list[str]) -> int:
    text = f"{title} {summary}".lower()
    curated_tags = {"jobs", "news", "github", "ai", "llm", "models", "remote", "hiring", "policy"} | set(TAG_KEYWORDS)
    score = sum(1 for tag in tags if tag in curated_tags) * 2
    for keyword in ["ai", "llm", "agent", "rag", "mcp", "open source", "engineer"]:
        if keyword_matches(text, keyword):
            score += 1
    return score


def parse_rss_items(source_name: str, tags: list[str], data: bytes, section: str) -> list[dict]:
    root = ET.fromstring(data)
    items = []
    if root.tag.endswith("rss") or root.find("channel") is not None:
        for item in root.findall("./channel/item"):
            title = child_text(item, ["title"])
            link = child_text(item, ["link"])
            published = child_text(item, ["pubDate", "date"])
            summary = child_text(item, ["description", "summary"])
            items.append(build_item(section, source_name, title, link, published, summary, tags))
        return items

    atom_ns = "{http://www.w3.org/2005/Atom}"
    for entry in root.findall(f"{atom_ns}entry"):
        title = child_text(entry, [f"{atom_ns}title"])
        link = atom_link(entry)
        published = child_text(entry, [f"{atom_ns}published", f"{atom_ns}updated"])
        summary = child_text(entry, [f"{atom_ns}summary", f"{atom_ns}content"])
        items.append(build_item(section, source_name, title, link, published, summary, tags))
    return items


def parse_remotive_jobs(source_name: str, tags: list[str], data: bytes) -> list[dict]:
    payload = json.loads(data.decode("utf-8"))
    jobs = []
    for job in payload.get("jobs", []):
        title = job.get("title", "")
        company = job.get("company_name", "")
        location = job.get("candidate_required_location", "")
        description = job.get("description", "")
        filter_text = f"{title} {company} {description} {' '.join(job.get('tags', []))}"
        if not is_ai_related(filter_text):
            continue
        job_tags = tags
        item = build_item(
            "jobs",
            source_name,
            title,
            job.get("url", ""),
            job.get("publication_date", ""),
            description,
            job_tags,
            {"company": company, "location": location, "jd": description},
        )
        if not item.get("location_scope") or not item.get("skills"):
            continue
        jobs.append(item)
    return jobs


def parse_remoteok_jobs(source_name: str, tags: list[str], data: bytes) -> list[dict]:
    payload = json.loads(data.decode("utf-8"))
    jobs = []
    for job in payload:
        if not isinstance(job, dict) or not job.get("position"):
            continue
        filter_text = f"{job.get('position', '')} {job.get('company', '')} {job.get('description', '')}"
        if not is_ai_related(filter_text):
            continue
        job_tags = tags
        description = job.get("description", "")
        item = build_item(
            "jobs",
            source_name,
            job.get("position", ""),
            job.get("url", ""),
            job.get("date", ""),
            description,
            job_tags,
            {"company": job.get("company", ""), "location": job.get("location", ""), "jd": description},
        )
        if not item.get("location_scope") or not item.get("skills"):
            continue
        jobs.append(item)
    return jobs


def parse_hn_jobs(source_name: str, tags: list[str], data: bytes) -> list[dict]:
    payload = json.loads(data.decode("utf-8"))
    jobs = []
    for hit in payload.get("hits", []):
        title = hit.get("title") or hit.get("story_title") or ""
        url = hit.get("url") or hit.get("story_url") or ""
        summary = hit.get("story_text") or hit.get("comment_text") or title
        if title.lower().startswith("show hn"):
            continue
        role_text = f"{title} {summary}"
        if not has_any_term(role_text, ["hiring", "job", "role", "position", "engineer", "developer", "architect"]):
            continue
        item = build_item(
            "jobs",
            source_name,
            title,
            url,
            hit.get("created_at", ""),
            summary,
            tags + hit.get("_tags", []),
            {"company": "", "location": "", "jd": summary},
        )
        if not item.get("location_scope") or not item.get("skills"):
            continue
        jobs.append(item)
    return jobs


def parse_github_repos(source_name: str, tags: list[str], data: bytes) -> list[dict]:
    payload = json.loads(data.decode("utf-8"))
    repos = []
    for repo in payload.get("items", []):
        topics = repo.get("topics") or []
        summary = repo.get("description") or ""
        repos.append(
            build_item(
                "github_repos",
                source_name,
                repo.get("full_name", ""),
                repo.get("html_url", ""),
                repo.get("updated_at", ""),
                summary,
                tags + topics,
                {
                    "repo": repo.get("full_name", ""),
                    "stars": repo.get("stargazers_count", 0),
                    "language": repo.get("language") or "",
                },
            )
        )
    return repos


def load_config() -> dict:
    config = json.loads(json.dumps(DEFAULT_CONFIG))
    if CONFIG_PATH.exists():
        disk_config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        deep_update(config, disk_config)
    return config


def deep_update(base: dict, incoming: dict) -> None:
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_update(base[key], value)
        else:
            base[key] = value


def collect_source(source: dict, section: str) -> list[dict]:
    data = fetch_url(source["url"])
    source_type = source.get("type", "rss")
    tags = source.get("tags", [])
    name = source["name"]
    if source_type == "rss":
        return parse_rss_items(name, tags, data, section)
    if source_type == "remotive":
        return parse_remotive_jobs(name, tags, data)
    if source_type == "remoteok":
        return parse_remoteok_jobs(name, tags, data)
    if source_type == "hn_algolia":
        return parse_hn_jobs(name, tags, data)
    if source_type == "github_search":
        return parse_github_repos(name, tags, data)
    raise ValueError(f"Unsupported source type: {source_type}")


def collect_items(config: dict) -> tuple[list[dict], list[dict]]:
    items = []
    errors = []
    for section, sources in config.get("sources", {}).items():
        for source in sources:
            try:
                items.extend(collect_source(source, section))
            except Exception as exc:
                errors.append({"section": section, "source": source.get("name", ""), "url": source.get("url", ""), "error": str(exc)})
    return items, errors


def dedupe_items(items: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for item in items:
        key = item.get("url") or item.get("title")
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def sort_items(items: list[dict]) -> list[dict]:
    return sorted(items, key=lambda item: (item.get("relevance_score", 0), item.get("published_at", "")), reverse=True)


def build_knowledge_trends(sections: dict, config: dict) -> list[dict]:
    corpus = sections.get("jobs", []) + sections.get("news", []) + sections.get("github_repos", [])
    trends = []
    for candidate in config.get("knowledge_trends", []):
        keywords = [keyword.lower() for keyword in candidate.get("keywords", [])]
        evidence = []
        score = 0
        for item in corpus:
            text = f"{item.get('title', '')} {item.get('summary', '')} {' '.join(item.get('tags', []))}".lower()
            hits = [keyword for keyword in keywords if keyword in text]
            if hits:
                score += len(hits)
                if len(evidence) < 3:
                    evidence.append({"title": item.get("title", ""), "section": item.get("section", ""), "url": item.get("url", "")})
        trends.append(
            {
                "name": candidate["name"],
                "summary": candidate.get("summary", ""),
                "keywords": candidate.get("keywords", []),
                "evidence_count": score,
                "evidence": evidence,
                "status": "daily_evidence" if score else "watchlist",
            }
        )
    trends.sort(key=lambda trend: (trend["evidence_count"], trend["name"]), reverse=True)
    minimum = int(config.get("minimum_items_per_section", 5))
    return trends[:minimum]


def build_cross_signals(sections: dict) -> list[dict]:
    tag_sections = {}
    for section_name in ["jobs", "news", "github_repos"]:
        for item in sections.get(section_name, []):
            for tag in item.get("tags", []):
                tag_sections.setdefault(tag, set()).add(section_name)
    signals = []
    for tag, present_sections in sorted(tag_sections.items(), key=lambda pair: (-len(pair[1]), pair[0])):
        if len(present_sections) < 2:
            continue
        section_text = "、".join(SECTION_LABELS_ZH.get(section, section) for section in sorted(present_sections))
        tag_text = tag_label_zh(tag)
        signals.append(
            {
                "tag": tag,
                "sections": sorted(present_sections),
                "insight": f"{tag_text}同时出现在{section_text}中，说明主题已经同时出现在多个生态信号里，值得持续跟踪。",
            }
        )
        if len(signals) == 5:
            break
    return signals


def build_coverage(sections: dict, minimum: int) -> dict:
    coverage = {}
    for section in ["jobs", "news", "github_repos", "knowledge_trends"]:
        count = len(sections.get(section, []))
        coverage[section] = {
            "count": count,
            "minimum": minimum,
            "status": "ok" if count >= minimum else "insufficient",
        }
    return coverage


def build_daily_record(items: list[dict], errors: list[dict], config: dict, now: dt.datetime | None = None) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc)
    date = now.astimezone(dt.timezone(dt.timedelta(hours=8))).strftime("%Y-%m-%d")
    max_items = int(config.get("max_items_per_section", 10))
    minimum = int(config.get("minimum_items_per_section", 5))
    deduped = dedupe_items(items)
    sections = {
        "jobs": sort_items([item for item in deduped if item.get("section") == "jobs"])[:max_items],
        "news": sort_items([item for item in deduped if item.get("section") == "news"])[:max_items],
        "github_repos": sort_items([item for item in deduped if item.get("section") == "github_repos"])[:max_items],
    }
    sections["knowledge_trends"] = build_knowledge_trends(sections, config)
    sections["cross_signals"] = build_cross_signals(sections)
    coverage = build_coverage(sections, minimum)
    warnings = []
    for section, detail in coverage.items():
        if detail["status"] != "ok":
            section_label = SECTION_LABELS_ZH.get(section, section)
            warnings.append(f"{section_label}收集到 {detail['count']} 条，低于最低要求 {detail['minimum']} 条。")
    if any(trend["status"] == "watchlist" for trend in sections["knowledge_trends"]):
        warnings.append("部分知识趋势今日没有直接证据，已作为观察清单保留。")
    return {
        "date": date,
        "timezone": config.get("timezone", "Asia/Shanghai"),
        "generated_at": now.astimezone(dt.timezone.utc).isoformat(),
        "coverage": coverage,
        "summary": build_summary(sections),
        "jobs": sections["jobs"],
        "news": sections["news"],
        "github_repos": sections["github_repos"],
        "knowledge_trends": sections["knowledge_trends"],
        "cross_signals": sections["cross_signals"],
        "errors": errors,
        "warnings": warnings,
    }


def tag_label_zh(tag: str) -> str:
    return TAG_LABELS_ZH.get(tag, tag)


def ordered_theme_tags(tags: list[str]) -> list[str]:
    tag_set = set(tags)
    ordered = [tag for tag in TAG_PRIORITY if tag in tag_set]
    extras = sorted(tag for tag in tag_set if tag in TAG_LABELS_ZH and tag not in ordered)
    return ordered + extras


def theme_text_zh(tags: list[str], fallback: str = "AI 生态") -> str:
    labels = [tag_label_zh(tag) for tag in ordered_theme_tags(tags)]
    return "、".join(labels[:4]) if labels else fallback


def build_summary(sections: dict) -> list[str]:
    tag_counts = {}
    for section in ["jobs", "news", "github_repos"]:
        for item in sections.get(section, []):
            for tag in item.get("tags", []):
                if tag in {"jobs", "news", "github", "remote"}:
                    continue
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
    top_tags = sorted(tag_counts.items(), key=lambda pair: (-pair[1], pair[0]))[:5]
    bullets = [f"{tag} 在 {count} 条记录中出现，中文主题可理解为：{tag_label_zh(tag)}。" for tag, count in top_tags]
    while len(bullets) < 5:
        bullets.append("今日公开数据源覆盖有限，阅读时请结合覆盖情况和错误列表判断信号强度。")
    return bullets[:5]


def item_explanation_zh(item: dict, section: str) -> str:
    themes = theme_text_zh(item.get("tags", []))
    if section == "jobs":
        company = item.get("company") or "该公司"
        location = item.get("location") or "未标明地区"
        return f"该岗位信号与{themes} 相关，显示 {company} 在 {location} 对相关 AI 能力有招聘需求。"
    if section == "news":
        return f"这条动态与{themes}相关，可能反映相关产品、技术或监管方向的新变化。"
    if section == "github_repos":
        stars = item.get("stars", 0)
        language = item.get("language") or "未知语言"
        return f"这个项目与{themes} 相关，目前约 {stars} stars，主要语言为 {language}，可作为开源生态热度线索。"
    return f"该条目与{themes} 相关。"


def trend_summary_zh(trend: dict) -> str:
    return TREND_SUMMARY_ZH.get(trend.get("name", ""), trend.get("summary", ""))


def short(value: str, width: int = 220) -> str:
    return textwrap.shorten(value or "", width=width, placeholder="...")


def render_job_jd_lines(item: dict) -> list[str]:
    if item.get("jd_language") == "en":
        return [
            f"- JD 原文摘录：{item.get('jd_excerpt') or '未抓取到 JD 描述。'}",
            f"- JD 中文解读：{item.get('jd_excerpt_zh') or jd_chinese_interpretation(item)}",
        ]
    return [f"- JD 摘要：该岗位 JD 提到：{item.get('jd_excerpt') or '未抓取到 JD 描述。'}"]


def render_jobs_report_zh(record: dict) -> str:
    lines = [
        f"# AI 岗位趋势 - {record['date']}",
        "",
        f"岗位覆盖：{record['coverage']['jobs']['count']}/{record['coverage']['jobs']['minimum']}（{STATUS_LABELS_ZH.get(record['coverage']['jobs']['status'], record['coverage']['jobs']['status'])}）",
        "",
    ]
    for item in record["jobs"]:
        lines.extend(
            [
                f"### [{item['title']}]({item['url']})",
                f"- 公司：{item.get('company') or '未知'}",
                f"- 地区：{item.get('location') or '未知'}",
                f"- 来源：{item['source']}",
                f"- 匹配范围：{item.get('location_scope_label') or '未匹配'}",
                f"- 标签：{theme_text_zh(item.get('tags', []))}",
                f"- 技能点：{'、'.join(item.get('skills') or ['未提取到明确技能点'])}",
                f"- 关注点：{item_explanation_zh(item, 'jobs')}",
                *render_job_jd_lines(item),
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def render_news_report_zh(record: dict) -> str:
    lines = [
        f"# AI 新闻动态 - {record['date']}",
        "",
        f"新闻覆盖：{record['coverage']['news']['count']}/{record['coverage']['news']['minimum']}（{STATUS_LABELS_ZH.get(record['coverage']['news']['status'], record['coverage']['news']['status'])}）",
        "",
    ]
    for item in record["news"]:
        lines.extend(
            [
                f"### [{item['title']}]({item['url']})",
                f"- 来源：{item['source']}",
                f"- 发布时间：{item.get('published_at') or '未知'}",
                f"- 标签：{theme_text_zh(item.get('tags', []))}",
                f"- 摘要：{item_explanation_zh(item, 'news')}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def render_github_report_zh(record: dict) -> str:
    lines = [
        f"# GitHub 热门项目 - {record['date']}",
        "",
        f"GitHub 项目覆盖：{record['coverage']['github_repos']['count']}/{record['coverage']['github_repos']['minimum']}（{STATUS_LABELS_ZH.get(record['coverage']['github_repos']['status'], record['coverage']['github_repos']['status'])}）",
        "",
    ]
    for item in record["github_repos"]:
        lines.extend(
            [
                f"### [{item.get('repo') or item['title']}]({item['url']})",
                f"- Stars：{item.get('stars', 0)}",
                f"- Language：{item.get('language') or '未知'}",
                f"- 标签：{theme_text_zh(item.get('tags', []))}",
                f"- 简介：{item_explanation_zh(item, 'github_repos')}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def render_index_report_zh(record: dict) -> str:
    date = record["date"]
    lines = [
        f"# AI Ecosystem Radar - {date}",
        "",
        "## 今日摘要",
        "",
    ]
    lines.extend([f"- {bullet}" for bullet in record["summary"]])
    lines.extend(
        [
            "",
            "## 分报告",
            "",
            f"- [AI 岗位趋势](./{date}-jobs-report.zh.md)",
            f"- [AI 新闻动态](./{date}-news-report.zh.md)",
            f"- [GitHub 热门项目](./{date}-github-report.zh.md)",
            "",
            "## 知识框架与趋势",
            "",
        ]
    )
    for trend in record["knowledge_trends"]:
        evidence = "；".join(e["title"] for e in trend.get("evidence", [])) or "今日直接证据不足，作为观察清单保留"
        lines.extend(
            [
                f"### {trend['name']}",
                f"- 状态：{STATUS_LABELS_ZH.get(trend['status'], trend['status'])}",
                f"- 证据数量：{trend['evidence_count']}",
                f"- 说明：{trend_summary_zh(trend)}",
                f"- 证据：{evidence}",
                "",
            ]
        )
    lines.extend(["## 交叉信号", ""])
    if record["cross_signals"]:
        for signal in record["cross_signals"]:
            lines.append(f"- {signal['insight']}")
    else:
        lines.append("- 今日没有发现跨板块重复出现的明显标签。")
    lines.extend(["", "## 数据覆盖情况", ""])
    for section, detail in record["coverage"].items():
        section_label = SECTION_LABELS_ZH.get(section, section)
        status_label = STATUS_LABELS_ZH.get(detail["status"], detail["status"])
        lines.append(f"- {section_label}: {detail['count']}/{detail['minimum']}（{status_label}）")
    if record["warnings"]:
        lines.extend(["", "### 覆盖提醒"])
        lines.extend([f"- {warning}" for warning in record["warnings"]])
    if record["errors"]:
        lines.extend(["", "### 抓取错误"])
        lines.extend([f"- {error['section']} / {error['source']}: {error['error']}" for error in record["errors"]])
    return "\n".join(lines).strip() + "\n"


def render_report_zh(record: dict) -> str:
    return render_index_report_zh(record)


def remove_if_exists(path: Path) -> None:
    if path.exists():
        path.unlink()


def cleanup_nested_report_dirs(report_root: Path) -> None:
    if not report_root.exists():
        return
    for nested_dir in report_root.iterdir():
        if not nested_dir.is_dir():
            continue
        for path in nested_dir.glob("*.md"):
            path.unlink()
        try:
            nested_dir.rmdir()
        except OSError:
            pass


def write_report_set(record: dict, dist_dir: Path, report_dir: Path) -> None:
    date = record["date"]
    latest_dir = dist_dir / "latest"
    report_dir.mkdir(parents=True, exist_ok=True)
    latest_dir.mkdir(parents=True, exist_ok=True)
    cleanup_nested_report_dirs(report_dir)
    outputs = {
        f"{date}-jobs-report.zh.md": render_jobs_report_zh(record),
        f"{date}-news-report.zh.md": render_news_report_zh(record),
        f"{date}-github-report.zh.md": render_github_report_zh(record),
        f"{date}-index.zh.md": render_index_report_zh(record),
    }
    latest_names = {
        f"{date}-jobs-report.zh.md": "jobs-report.zh.md",
        f"{date}-news-report.zh.md": "news-report.zh.md",
        f"{date}-github-report.zh.md": "github-report.zh.md",
        f"{date}-index.zh.md": "index.zh.md",
    }
    for filename, content in outputs.items():
        (report_dir / filename).write_text(content, encoding="utf-8")
        (latest_dir / latest_names[filename]).write_text(content, encoding="utf-8")


def write_outputs(record: dict, output_root: Path = ROOT) -> None:
    daily_dir = output_root / "data" / "daily"
    dist_dir = output_root / "dist"
    report_dir = dist_dir / "reports"
    daily_dir.mkdir(parents=True, exist_ok=True)
    dist_dir.mkdir(parents=True, exist_ok=True)
    daily_payload = json.dumps(record, ensure_ascii=False, indent=2)
    (daily_dir / f"{record['date']}.json").write_text(daily_payload, encoding="utf-8")
    (output_root / "data" / "latest.json").write_text(daily_payload, encoding="utf-8")
    write_report_set(record, dist_dir, report_dir)
    remove_if_exists(dist_dir / "daily-report.zh.md")
    remove_if_exists(dist_dir / "daily-report.md")


def main() -> None:
    config = load_config()
    items, errors = collect_items(config)
    record = build_daily_record(items, errors, config)
    write_outputs(record, ROOT)
    print(
        "Wrote AI ecosystem radar for "
        f"{record['date']}: jobs={record['coverage']['jobs']['count']}, "
        f"news={record['coverage']['news']['count']}, "
        f"github_repos={record['coverage']['github_repos']['count']}, "
        f"knowledge_trends={record['coverage']['knowledge_trends']['count']}"
    )


if __name__ == "__main__":
    main()
