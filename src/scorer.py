import config


def score_posts(posts: list[dict]) -> list[dict]:
    scored = [_score_post(p) for p in posts]
    # warm leads first, then by keyword count desc
    scored.sort(key=lambda x: (x["bucket"] == "warm", x["score"]), reverse=True)
    return scored


def _score_post(post: dict) -> dict:
    text     = post["post_text"].lower()
    headline = (post.get("author_headline") or "").lower()

    # Stage 1a: headline rejection
    for term in config.REJECT_HEADLINE_CONTAINS:
        if term in headline:
            return _build(post, bucket="rejected", matched=[], reason=f"author headline matches '{term}'")

    # Stage 1b: post-content rejection (job postings, recruiter blasts, etc.)
    for pattern in config.REJECT_POST_PATTERNS:
        if pattern in text:
            return _build(post, bucket="rejected", matched=[], reason=f"post matches rejection pattern '{pattern}'")

    # Stage 1c: require at least one approved tech keyword
    matched = [kw for kw in config.TECH_KEYWORDS if kw in text]
    if not matched:
        return _build(post, bucket="rejected", matched=[], reason="no approved tech keywords found")

    return _build(post, bucket="warm", matched=matched, reason=None)


def _build(post: dict, *, bucket: str, matched: list, reason: str | None) -> dict:
    return {
        "name":             post["author_name"],
        "profile_url":      post["profile_url"],
        "author_headline":  post.get("author_headline", ""),
        "post_text":        post["post_text"],
        "post_url":         post.get("post_url", ""),
        "score":            len(matched),
        "bucket":           bucket,
        "matched_keywords": matched,
        "score_breakdown":  {kw: 1 for kw in matched},
        "rejection_reason": reason,
        "invite":           None,
        "email":            None,
    }
