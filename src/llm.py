import json
import os
import sys
from pathlib import Path

from openai import OpenAI

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

_client: OpenAI | None = None

_VALIDATE_SYSTEM = """\
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

Return ONLY valid JSON: {"relevant": true, "reason": "..."} or {"relevant": false, "reason": "..."}\
"""

_OUTREACH_SYSTEM = """\
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

Return ONLY valid JSON with keys: "invite", "email_subject", "email_body".\
"""


def _client_instance() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ[config.OPENAI_TOKEN_ENV])
    return _client


def validate_lead(lead: dict) -> dict:
    """Stage 2 filter. Returns {"relevant": bool, "reason": str}."""
    user_msg = (
        f"Author: {lead['name']}\n"
        f"Headline: {lead.get('author_headline') or 'unknown'}\n"
        f"Matched tech keywords: {', '.join(lead['matched_keywords'])}\n\n"
        f"Post:\n{lead['post_text']}"
    )
    resp = _client_instance().chat.completions.create(
        model=config.OPENAI_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _VALIDATE_SYSTEM},
            {"role": "user",   "content": user_msg},
        ],
        temperature=0,
        max_tokens=120,
    )
    return json.loads(resp.choices[0].message.content)


def generate_outreach(lead: dict) -> dict:
    """Returns {"invite": str, "email": str}."""
    user_msg = (
        f"Name: {lead['name']}\n"
        f"Headline: {lead.get('author_headline') or 'unknown'}\n"
        f"Matched tech keywords: {', '.join(lead['matched_keywords'])}\n\n"
        f"Post:\n{lead['post_text']}"
    )
    resp = _client_instance().chat.completions.create(
        model=config.OPENAI_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _OUTREACH_SYSTEM},
            {"role": "user",   "content": user_msg},
        ],
        temperature=0.7,
        max_tokens=600,
    )
    data = json.loads(resp.choices[0].message.content)

    invite = data.get("invite", "")
    if len(invite) > 280:
        invite = invite[:277] + "..."

    email = f"Subject: {data.get('email_subject', '')}\n\n{data.get('email_body', '')}"
    return {"invite": invite, "email": email}
