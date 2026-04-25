# ── Environment variable names ────────────────────────────────────────────────
APIFY_TOKEN_ENV  = "APIFY_API_TOKEN"
OPENAI_TOKEN_ENV = "OPENAI_API_KEY"

# ── LLM model ─────────────────────────────────────────────────────────────────
OPENAI_MODEL = "gpt-4o-mini"

# ── Apify actor + search URLs ─────────────────────────────────────────────────
APIFY_ACTOR_ID = "supreme_coder/linkedin-post"

# Search URLs are anchored on actual product/tech names — not the company name.
# People talk about the tech (Astra DB, LangFlow, AstraDB), not "DataStax".
# LinkedIn does semantic search so searching "Astra" surfaces Astra DB + Astra
# Streaming posts; our scorer then filters on specific approved keywords.
APIFY_SEARCH_URLS = [
    "https://www.linkedin.com/search/results/content/?keywords=Astra+DB&datePosted=past-month&origin=FACETED_SEARCH",
    "https://www.linkedin.com/search/results/content/?keywords=AstraDB&datePosted=past-month&origin=FACETED_SEARCH",
    "https://www.linkedin.com/search/results/content/?keywords=Astra&datePosted=past-month&origin=FACETED_SEARCH",
    "https://www.linkedin.com/search/results/content/?keywords=LangFlow&datePosted=past-month&origin=FACETED_SEARCH",
    "https://www.linkedin.com/search/results/content/?keywords=Cassandra+DataStax&datePosted=past-month&origin=FACETED_SEARCH",
]
APIFY_LIMIT_PER_SOURCE = 5

# ── Stage 1a: approved tech-stack keywords (case-insensitive substring match) ──
TECH_KEYWORDS = [
    "datastax",
    "astra db",
    "astradb",
    "cassandra",
    "langflow",        # DataStax-acquired open-source LLM pipeline tool
    "stargate",        # DataStax open API layer for Cassandra
    "astra streaming",
    "wide-column",
    "sstable",         # Cassandra internal storage format
    "apache pulsar",   # DataStax Streaming backbone (full name only)
]

# ── Stage 1b: hard-reject if author headline contains any of these ─────────────
REJECT_HEADLINE_CONTAINS = [
    "datastax",
    "ibm",           # IBM acquired DataStax
    "aiven",         # managed Cassandra competitor
    "instaclustr",   # managed Cassandra competitor
]

# ── Stage 1c: hard-reject if post text contains any of these ──────────────────
# Catches job postings, vendor self-promo, recruiter blasts
REJECT_POST_PATTERNS = [
    "we're hiring",
    "we are hiring",
    "#hiring",
    "hiring now",
    "open position",
    "job opportunity",
    "apply now",
    "send resume",
    "send your resume",
    "dm me your resume",
    "dm me your cv",
    "looking for a ",
    "i'm recruiting",
    "i am recruiting",
]
