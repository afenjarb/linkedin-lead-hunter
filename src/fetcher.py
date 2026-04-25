import json
import os
from pathlib import Path

from apify_client import ApifyClient

import config

MOCK_PATH = Path("data/mock_posts.json")


def fetch_posts(live: bool) -> list[dict]:
    if live:
        return _fetch_live()
    return _fetch_mock()


def _fetch_live() -> list[dict]:
    print("[LIVE] Fetching posts from Apify...")
    client = ApifyClient(os.environ[config.APIFY_TOKEN_ENV])
    run = client.actor(config.APIFY_ACTOR_ID).call(run_input={
        "urls": config.APIFY_SEARCH_URLS,
        "limitPerSource": config.APIFY_LIMIT_PER_SOURCE,
        "deepScrape": False,
    })
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    return [_normalize(item) for item in items]


def _fetch_mock() -> list[dict]:
    print("[MOCK] Loading posts from data/mock_posts.json")
    with open(MOCK_PATH) as f:
        raw = json.load(f)
    return [_normalize(p) for p in raw]


def _author_subfield(post: dict, field: str) -> str:
    author = post.get("author")
    return author.get(field, "") if isinstance(author, dict) else ""


def _normalize(post: dict) -> dict:
    author_name = (
        post.get("authorName")
        or post.get("author_name")
        or _author_subfield(post, "name")
        or post.get("actorName")
        or "Unknown"
    )
    profile_url = (
        post.get("authorUrl")
        or post.get("author_profile_url")
        or post.get("authorProfileUrl")
        or post.get("profileUrl")
        or _author_subfield(post, "url")
        or ""
    )
    post_text = (
        post.get("text")
        or post.get("post_text")
        or post.get("postText")
        or post.get("content")
        or post.get("description")
        or ""
    )
    post_url = (
        post.get("postUrl")
        or post.get("post_url")
        or post.get("url")
        or post.get("link")
        or ""
    )
    posted_at = (
        post.get("postedAtISO")
        or post.get("postedAt")
        or post.get("posted_at")
        or post.get("date")
        or post.get("timestamp")
        or post.get("publishedAt")
        or ""
    )
    author_headline = (
        post.get("authorHeadline")
        or post.get("author_headline")
        or _author_subfield(post, "headline")
        or ""
    )
    return {
        "author_name":     author_name,
        "author_headline": author_headline,
        "profile_url":     profile_url,
        "post_text":       post_text,
        "post_url":        post_url,
        "posted_at":       posted_at,
    }
