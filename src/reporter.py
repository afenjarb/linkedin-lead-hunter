from datetime import datetime
from pathlib import Path

OUTPUT_PATH = Path("report.md")


def render_report(leads: list[dict]) -> Path:
    warm     = [l for l in leads if l["bucket"] == "warm"]
    rejected = [l for l in leads if l["bucket"] == "rejected"]
    ts       = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "# ScyllaDB Lead Hunter — Report\n",
        f"_Run: {ts} · {len(warm)} reach out · {len(rejected)} rejected_\n",
        "\n---\n",
    ]

    lines.append(f"\n## ✓ Reach Out ({len(warm)})\n")
    for lead in warm:
        lines += _lead_block(lead)

    lines.append(f"\n## ✗ Rejected ({len(rejected)})\n")
    for lead in rejected:
        lines += _lead_block(lead)

    OUTPUT_PATH.write_text("".join(lines), encoding="utf-8")
    return OUTPUT_PATH


def _lead_block(lead: dict) -> list[str]:
    excerpt = lead["post_text"][:280].replace("\n", " ")
    lines = [
        f"\n### {lead['name']}\n",
    ]
    if lead.get("author_headline"):
        lines.append(f"**{lead['author_headline']}**  \n")
    if lead.get("profile_url"):
        lines.append(f"[View Profile]({lead['profile_url']})\n")

    lines.append(f"\n> {excerpt}{'…' if len(lead['post_text']) > 280 else ''}\n")

    if lead["matched_keywords"]:
        kws = " · ".join(f"`{k}`" for k in lead["matched_keywords"])
        lines.append(f"\n**Keywords matched:** {kws}\n")

    if lead.get("rejection_reason"):
        lines.append(f"\n**Rejected:** {lead['rejection_reason']}\n")

    if lead.get("invite"):
        lines += [
            "\n**LinkedIn Invite:**\n",
            f"> {lead['invite']}\n",
            f"_({len(lead['invite'])} chars)_\n",
        ]
    if lead.get("email"):
        lines += [
            "\n**Follow-up Email:**\n",
            "```\n",
            lead["email"] + "\n",
            "```\n",
        ]

    lines.append("\n---\n")
    return lines


def print_console_summary(leads: list[dict]) -> None:
    warm     = [l for l in leads if l["bucket"] == "warm"]
    rejected = [l for l in leads if l["bucket"] == "rejected"]

    print("\n" + "=" * 60)
    print("  LINKEDIN LEAD HUNTER — RESULTS")
    print("=" * 60)
    print(f"  Reach out : {len(warm):>3}")
    print(f"  Rejected  : {len(rejected):>3}")
    print(f"  Total     : {len(leads):>3}")
    print("=" * 60)

    if warm:
        print("\n  TOP LEADS:\n")
        for i, lead in enumerate(warm[:3], 1):
            excerpt = lead["post_text"][:120].replace("\n", " ")
            print(f"  {i}. {lead['name']}")
            print(f"     {lead.get('author_headline', '')}")
            print(f"     {lead['profile_url']}")
            print(f"     \"{excerpt}...\"")
            print(f"     Keywords: {', '.join(lead['matched_keywords'])}")
            if lead.get("invite"):
                print(f"     Invite: {lead['invite'][:80]}...")
            print()

    print("=" * 60)
    print(f"  Full report: {OUTPUT_PATH.resolve()}\n")
