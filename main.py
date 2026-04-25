#!/usr/bin/env python3
"""
LinkedIn Lead Hunter — ScyllaDB GTM take-home PoC

Usage:
  python main.py            # dry-run: mock posts + LLM pipeline if OPENAI_API_KEY is set
  python main.py --live     # Apify fetch + LLM validate + OpenAI outreach (both keys required)
  python main.py --reset    # wipe DB before run
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

import config
from src import db, fetcher, llm, outreach_log, reporter, scorer


def main() -> None:
    parser = argparse.ArgumentParser(description="LinkedIn Lead Hunter for ScyllaDB")
    parser.add_argument("--live", action="store_true", help="Use Apify + OpenAI (needs .env keys)")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate database")
    args = parser.parse_args()

    if args.reset and Path("leads.db").exists():
        Path("leads.db").unlink()
        print("  [reset] leads.db deleted")

    db.init_db()

    # ── 1. FETCH ──────────────────────────────────────────────────────────────
    if args.live and not os.getenv(config.APIFY_TOKEN_ENV):
        sys.exit(f"ERROR: {config.APIFY_TOKEN_ENV} not set in .env")
    posts = fetcher.fetch_posts(live=args.live)
    print(f"  [fetch] {len(posts)} posts loaded")

    # ── 2. STAGE 1: keyword filter + rejection rules ───────────────────────────
    scored = scorer.score_posts(posts)
    candidates = [l for l in scored if l["bucket"] == "warm"]
    rejected1  = [l for l in scored if l["bucket"] == "rejected"]
    print(f"  [stage1] {len(candidates)} candidates  |  {len(rejected1)} rejected by rules")

    # ── 3. STAGE 2: LLM relevance validation ─────────────────────────────────
    has_openai = bool(os.getenv(config.OPENAI_TOKEN_ENV))
    if args.live and not has_openai:
        sys.exit(f"ERROR: {config.OPENAI_TOKEN_ENV} not set in .env")

    if candidates and has_openai:
        print(f"  [stage2] LLM validating {len(candidates)} candidates...")
        for lead in candidates:
            result = llm.validate_lead(lead)
            if not result["relevant"]:
                lead["bucket"] = "rejected"
                lead["rejection_reason"] = f"LLM: {result['reason']}"
                print(f"           ✗ {lead['name']} — {result['reason']}")
            else:
                print(f"           ✓ {lead['name']}")
    elif not has_openai:
        print(f"  [stage2] Skipping LLM validation — {config.OPENAI_TOKEN_ENV} not set")

    # ── 4. PERSIST — only confirmed warm leads ─────────────────────────────────
    actionable = [l for l in scored if l["bucket"] == "warm"]
    lead_ids: dict[str, int] = {}
    for lead in actionable:
        lid = db.upsert_lead(lead)
        lead_ids[lead["profile_url"]] = lid

    # ── 5. GENERATE OUTREACH ──────────────────────────────────────────────────
    if actionable and has_openai:
        mode = "live" if args.live else "dry-run"
        print(f"  [outreach] Generating messages for {len(actionable)} leads...")
        for lead in actionable:
            try:
                msgs = llm.generate_outreach(lead)
                db.save_messages(lead_ids[lead["profile_url"]], msgs["invite"], msgs["email"])
                lead["invite"] = msgs["invite"]
                lead["email"]  = msgs["email"]
                print(f"             ✓ {lead['name']}")
            except Exception as exc:
                print(f"             ✗ {lead['name']}: {exc}")

        log_path = outreach_log.append_run(actionable, mode=mode)
        print(f"  [log] Outreach appended → {log_path.resolve()}")
    elif not has_openai:
        print(f"  [outreach] Skipping outreach generation — {config.OPENAI_TOKEN_ENV} not set ({len(actionable)} actionable leads)")

    # ── 6. REPORT — always from current run ───────────────────────────────────
    html_path = reporter.render_report(scored)
    print(f"  [report] Written → {html_path.resolve()}")
    reporter.print_console_summary(scored)


if __name__ == "__main__":
    main()
