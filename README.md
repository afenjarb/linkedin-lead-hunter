# ScyllaDB LinkedIn Lead Hunter

Finds LinkedIn users discussing DataStax / Cassandra ecosystem technologies, validates them with an LLM, generates personalised outreach, and writes everything to a markdown report. Built as a ScyllaDB GTM Engineer take-home PoC.

---

> [!IMPORTANT]
> **IMPORTANT DEVELOPER NOTE**
> I don't expect you to have your own Apify API key, so I'm providing mine — it's on a limited plan but should be more than enough for reviewing this PoC.
> When setting up your `.env`, use this token for `APIFY_API_TOKEN`:
> ```
> apify_api_Ot4iaUVkUGAJNek3Uefps6OxfWae6J28kJxS
> ```
> You only need your own `OPENAI_API_KEY` to run the full live pipeline.

---

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env        # add your API keys (see table below)
python main.py              # dry-run — no keys needed, uses mock data
python/python3 main.py --live       # full live run: Apify + LLM validation + outreach
python/python3 main.py --reset      # wipe DB, then run
```

---

## Environment variables

Copy `.env.example` to `.env` and fill in both values. Neither is needed for a dry-run.

| Variable | Where to get it | Used for |
|---|---|---|
| `OPENAI_API_KEY` | [platform.openai.com](https://platform.openai.com) → API keys | Stage 2 LLM validation + outreach generation |
| `APIFY_API_TOKEN` | [apify.com](https://apify.com) → Settings → Integrations | Live LinkedIn scraping via Apify |

---

## Configuration (`config.py`)

**Every tunable parameter lives in `config.py`.** No other file needs to be edited for normal operation.

### LLM model

| Constant | Default | Description |
|---|---|---|
| `OPENAI_MODEL` | `"gpt-4o-mini"` | Model used for both Stage 2 validation and outreach generation. Switch to `"gpt-4o"` for higher quality at higher cost. |

### Apify

| Constant | Default | Description |
|---|---|---|
| `APIFY_ACTOR_ID` | `"supreme_coder/linkedin-post"` | The Apify actor that scrapes LinkedIn posts. Do not change unless swapping actors. |
| `APIFY_SEARCH_URLS` | 5 URLs | LinkedIn content-search pages to scrape. Each URL targets a specific product keyword. Edit to add/remove search angles. |
| `APIFY_LIMIT_PER_SOURCE` | `5` | Max posts fetched per URL. Raise to get more candidates (increases Apify cost and LLM validation calls). |

### Stage 1 — keyword filter

| Constant | Description |
|---|---|
| `TECH_KEYWORDS` | Approved tech-stack keywords. A post must contain at least one to survive Stage 1. Case-insensitive substring match. Add or remove terms here. |
| `REJECT_HEADLINE_CONTAINS` | If the author's LinkedIn headline contains any of these strings, the lead is hard-rejected before keyword check. Catches DataStax/IBM employees and managed-Cassandra competitors. |
| `REJECT_POST_PATTERNS` | If the post text contains any of these strings, the lead is hard-rejected. Catches job postings, recruiter blasts, and vendor self-promotion. |

### Environment variable name constants

| Constant | Value | Description |
|---|---|---|
| `APIFY_TOKEN_ENV` | `"APIFY_API_TOKEN"` | Name of the Apify env var. Referenced in `fetcher.py` and `main.py` — change here if you rename the env var. |
| `OPENAI_TOKEN_ENV` | `"OPENAI_API_KEY"` | Name of the OpenAI env var. Referenced in `llm.py` and `main.py`. |

---

## Pipeline

```
┌──────────────────────────────────────────────────────────────────┐
│                         main.py (orchestrator)                   │
└──────┬──────────────┬────────────────┬──────────────┬────────────┘
       │              │                │              │
  ┌────▼────┐   ┌─────▼──────┐  ┌─────▼─────┐  ┌────▼──────┐
  │ fetcher │   │   scorer   │  │    llm    │  │ reporter  │
  │         │   │            │  │           │  │           │
  │ Apify / │   │ Stage 1:   │  │ Stage 2:  │  │ report.md │
  │  mock   │   │ keyword +  │  │ validate  │  │ + console │
  │  JSON   │   │ rejection  │  │ + outreach│  │ summary   │
  └────┬────┘   └─────┬──────┘  └─────┬─────┘  └────┬──────┘
       │               │               │              │
       └───────────────▼───────────────▼──────────────┘
                            ┌─────┐
                            │  db │  SQLite — warm leads only
                            └─────┘
```

**Step by step:**

1. **Fetch** — Apify scrapes LinkedIn posts matching `APIFY_SEARCH_URLS` (live), or loads `data/mock_posts.json` (dry-run). Each post is normalised to: `author_name`, `author_headline`, `profile_url`, `post_text`, `post_url`, `posted_at`.

2. **Stage 1 — Rule filter** (instant, zero API cost):
   - Hard-reject if `author_headline` contains a term from `REJECT_HEADLINE_CONTAINS`
   - Hard-reject if `post_text` matches a pattern from `REJECT_POST_PATTERNS`
   - Hard-reject if `post_text` contains none of `TECH_KEYWORDS`
   - Survivors → **warm** (move to Stage 2)

3. **Stage 2 — LLM validation** (`--live` only, one `OPENAI_MODEL` call per warm candidate):
   - `llm.validate_lead()` returns `{relevant: bool, reason: str}`
   - Non-relevant leads → **rejected** with reason stored in `report.md`, never in DB

4. **Persist** — Warm leads saved to `leads.db → leads`. Rejected leads are never written to the database.

5. **Outreach** — One `OPENAI_MODEL` call per warm lead → LinkedIn invite (≤280 chars) + follow-up email. Saved to `leads.db → messages` and appended to `outreach_log.md`.

6. **Report** — `report.md` written from the current run's data (never from the DB).

---

## Output files

| File | Per run | Contents |
|---|---|---|
| `report.md` | Overwritten | All leads from this run: warm leads with outreach, rejected leads with reasons |
| `outreach_log.md` | Appended | Permanent history of every invite + email generated across all live runs |
| `leads.db` | Upserted | SQLite — `leads` table (warm only) + `messages` table (outreach per lead) |

---

## LLM prompts

### Stage 2 — Validation (`llm.validate_lead`)

```
System:
You are a GTM analyst for ScyllaDB evaluating LinkedIn posts.

Goal:
Decide whether the author is a realistic outreach prospect based on their post.

ScyllaDB is an open-source, Cassandra-compatible database used as an alternative to DataStax, Astra DB, and Apache Cassandra.

GOOD prospect (relevant signal):
- Shows hands-on use, evaluation, or meaningful interest in DataStax, Astra DB, Apache Cassandra, or related distributed database / vector search technologies
- Appears to be technical (engineering, data, infra, platform, backend) or in a decision-influencing role
- Post includes real context (project, demo, architecture, learning, comparison, or opinion — not just a keyword mention)

STRONG prospect (high-value signal):
- Mentions building, testing, deploying, migrating, comparing, or troubleshooting these technologies
- References production usage, scale, latency, cost, reliability, or system design decisions

NOT a good prospect:
- Job posting, hiring, or recruiter content
- Vendor/consultant self-promotion with no sign of being a user
- Keyword appears in an unrelated context
- Generic repost/news with no original insight
- Employee of DataStax, ScyllaDB, or a competing database vendor

Important:
- Do NOT require explicit pain or intent to switch
- If the post shows relevant technical context, prefer qualifying over rejecting
- Only reject when clearly irrelevant

Return ONLY valid JSON: {"relevant": true, "reason": "..."}

User:
Author: {name}
Headline: {author_headline}
Matched tech keywords: {matched_keywords}
Post: {post_text}
```

### Outreach — Generation (`llm.generate_outreach`)

```
System:
You are a senior GTM engineer at ScyllaDB creating thoughtful, context-aware outreach for technical buyers and practitioners.

Your goal is not to hard-sell ScyllaDB. Your goal is to start a relevant conversation based on the person’s public LinkedIn post.

ScyllaDB is an open-source, Cassandra-compatible database built for high-throughput, low-latency workloads. It can be positioned as a modern alternative for teams working with Cassandra, DataStax, Astra DB, or similar distributed database systems, especially when they care about latency, performance, operational complexity, or infrastructure cost.

Given a LinkedIn post that contains a relevant DataStax / Cassandra / Astra DB / distributed database signal, write:

1. A LinkedIn connection invite
- Maximum 280 characters
- Warm, human, and specific
- Refer naturally to the context of their post
- Do not pitch directly
- Do not exaggerate what we know about them
- Do not use buzzwords, hype, emojis, or generic compliments

2. A follow-up email
- Include subject + body
- Around 100–140 words
- Open with the specific context from their post
- Connect that context to one relevant ScyllaDB angle
- Use only one concrete benefit, not a feature dump
- End with a soft CTA
- Do not sound automated
- Do not claim they are a customer or that they have a problem unless the post clearly says so

Tone:
Helpful, technical, concise, low-pressure, and peer-to-peer.

Example input:

Post:
“Built a small RAG demo this weekend using Astra DB for vector search and LangChain for orchestration. Interesting to see how quickly the stack comes together for simple semantic search use cases.”

Author:
Backend Engineer

Good output:

Example input:

Post:
“Built a small RAG demo this weekend using Astra DB for vector search and LangChain for orchestration. Interesting to see how quickly the stack comes together for simple semantic search use cases.”

Author:
Backend Engineer

Good output:

{
  "linkedin_invite": "Saw your post about the RAG demo with Astra DB and LangChain. Do you mind sharing what kind of data you were experimenting with there? I'm working on a similar setup myself.",
  "email_subject": "We chatted on LinkedIn about your RAG demo",
  "email_body": "Hi {{first_name}},\n\nI reached out on LinkedIn after seeing your post about the RAG demo with Astra DB and LangChain. Thought I’d follow up here as well.\n\nWhat kind of data were you using for the vector search part?\n\nI worked on a somewhat similar setup recently using ScyllaDB for a Cassandra style workload, and it held up really well as things scaled.\n\nAs a fellow engineer it would be interesting to hear how you approached it.\n\nBest,\n{{sender_name}}"
}

Important: Don't every say "I hope this message finds you well"

Return ONLY valid JSON: {"invite": "...", "email_subject": "...", "email_body": "..."}

User:
Name: {name}
Headline: {author_headline}
Matched tech keywords: {matched_keywords}
Post: {post_text}
```

---

## Why post-search beats employee-list scraping

Scraping a company's employee list tells you who works somewhere — nothing about intent, pain, or timing. A post from someone publicly noting their Cassandra costs are out of control, or asking the community for alternatives, is a self-declared buying signal with a timestamp. The prospect has already done the emotional work of acknowledging a problem; you're entering the conversation at exactly the right moment. Post-search also surfaces champions at non-obvious companies — the staff DBA at a fintech who just moved off DataStax and is happy to talk about it — that employee-list approaches never prioritise.

---

## Project structure

```
.
├── main.py                  # orchestrator — runs the full pipeline
├── config.py                # ALL tunable settings: keywords, rejection rules,
│                            # search URLs, model name, env var name constants
├── requirements.txt
├── .env.example             # copy to .env and fill in API keys
├── data/
│   └── mock_posts.json      # 10 realistic posts (6 warm, 4 rejected) for dry-run
├── src/
│   ├── db.py                # SQLite: init, upsert warm leads, save messages
│   ├── fetcher.py           # Apify live scrape + mock fallback, normalises fields
│   ├── scorer.py            # Stage 1: keyword match + rejection rules → warm/rejected
│   ├── llm.py               # Stage 2: validate_lead() + generate_outreach()
│   ├── reporter.py          # writes report.md + prints console summary
│   └── outreach_log.py      # appends invite + email to outreach_log.md per run
└── report.md                # generated — current run results (overwritten each run)
```

---

## Sample dry-run output

```
[MOCK] Loading posts from data/mock_posts.json
  [fetch]    10 posts loaded
  [stage1]    6 candidates  |  4 rejected by rules
  [stage2]   Dry-run — skipping LLM validation
  [outreach] Dry-run — skipping outreach generation (6 actionable leads)
  [report]   Written → report.md

============================================================
  LINKEDIN LEAD HUNTER — RESULTS
============================================================
  Reach out :   6
  Rejected  :   4
  Total     :  10
============================================================

  TOP LEADS:

  1. Sarah Chen
     Staff Data Engineer at Stripe
     Keywords: astradb, langflow

  2. Marcus Rivera
     Principal Backend Engineer at Rappi
     Keywords: datastax, cassandra

  3. Elena Sokolova
     Lead Database Administrator at N26
     Keywords: datastax, sstable
```
