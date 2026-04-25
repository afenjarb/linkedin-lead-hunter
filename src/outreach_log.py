from datetime import datetime
from pathlib import Path

LOG_PATH = Path("outreach_log.md")


def append_run(leads: list[dict], mode: str) -> Path:
    """Append warm leads with generated outreach to outreach_log.md."""
    actionable = [l for l in leads if l.get("invite") or l.get("email")]
    if not actionable:
        return LOG_PATH

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"\n## Run: {timestamp} ({mode})\n",
        f"_{len(actionable)} leads with outreach generated_\n",
    ]

    for lead in actionable:
        lines += [
            f"\n### {lead['name']}\n",
            f"**Profile:** {lead['profile_url']}  \n",
            f"**Headline:** {lead.get('author_headline', '')}  \n",
            f"**Keywords:** {', '.join(lead['matched_keywords'])}  \n",
            f"**Post excerpt:** {lead['post_text'][:200].replace(chr(10), ' ')}...\n",
        ]
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
                f"{lead['email']}\n",
                "```\n",
            ]
        lines.append("\n---\n")

    is_new = not LOG_PATH.exists() or LOG_PATH.stat().st_size == 0
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        if is_new:
            f.write("# Outreach Log\n")
        f.writelines(lines)

    return LOG_PATH
