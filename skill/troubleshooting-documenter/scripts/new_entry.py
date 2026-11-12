#!/usr/bin/env python3
"""
Create a formatted Markdown troubleshooting entry and optionally trigger
a live rescan on the local Troubleshooting Hub server.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request

DEFAULT_HUB_DIR: Path = Path.home() / "Desktop" / "troubleshooting"
DEFAULT_PORT: int = 8898
VALID_STATUSES: tuple[str, ...] = ("Fixed", "Monitoring", "Recurring", "Playbook")


def slugify(value: str) -> str:
    """Convert arbitrary text into a lowercase kebab-case filename slug."""
    cleaned = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE).strip().lower()
    slug = re.sub(r"[_\s-]+", "-", cleaned).strip("-")
    return slug or "entry"


def resolve_hub_dir(cli_dir: Path | None) -> Path:
    """Resolve the Troubleshooting Hub directory from CLI, env, or default."""
    if cli_dir is not None:
        return cli_dir.expanduser().resolve()
    env_dir = os.environ.get("TROUBLE_DIR", "").strip()
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    return DEFAULT_HUB_DIR.resolve()


def build_markdown(
    title: str,
    date_str: str,
    host: str,
    status: str,
    tags: list[str],
) -> str:
    """Render standard troubleshooting Markdown boilerplate."""
    tags_line = ", ".join(t.strip().lower() for t in tags if t.strip()) or "diagnostics"
    return (
        f"# {title.strip()}\n\n"
        f"- **Date**: {date_str}\n"
        f"- **Host**: {host.strip()}\n"
        f"- **Status**: {status}\n"
        f"- **Tags**: {tags_line}\n\n"
        "## Symptom\n"
        "Exact error text or observed behavior, including the command that revealed it.\n\n"
        "## Root Cause\n"
        "The true underlying cause (not the initial assumption).\n\n"
        "## Diagnostic Checks & Fix\n"
        "Document each check run, the exact command, and **why it is necessary**.\n\n"
        "```bash\n"
        "# diagnostic / failing check\n\n"
        "# fix / passing check\n"
        "```\n\n"
        "## Verification\n"
        "Command and expected output proving the issue is resolved.\n\n"
        "## Prevention\n"
        "Specific rule, guardrail, or preflight check to prevent recurrence.\n"
    )


def trigger_rescan(port: int) -> bool:
    """Notify the local Troubleshooting Hub server to rescan Markdown files."""
    url = f"http://127.0.0.1:{port}/api/rescan"
    req = urllib.request.Request(url, method="POST", data=b"")
    try:
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            if resp.status == 200:
                payload = json.loads(resp.read().decode("utf-8"))
                print(f"Rescanned live hub ({payload.get('count', '?')} docs indexed)")
                return True
    except (urllib.error.URLError, TimeoutError, ValueError):
        pass
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a formatted troubleshooting entry")
    parser.add_argument("--title", required=True, help="Concise problem title")
    parser.add_argument("--category", default="general", help="Formatted category folder (e.g. boot-and-startup)")
    parser.add_argument("--host", default="pc", help="Target host label (e.g. pc, vps, server)")
    parser.add_argument("--status", default="Fixed", choices=VALID_STATUSES, help="Entry status")
    parser.add_argument("--tags", default="diagnostics", help="Comma-separated tags")
    parser.add_argument("--date", default=datetime.date.today().isoformat(), help="Entry date (YYYY-MM-DD)")
    parser.add_argument("--dir", type=Path, default=None, help="Troubleshooting Hub root directory")
    parser.add_argument("--port", type=int, default=int(os.environ.get("TROUBLE_PORT", DEFAULT_PORT)))
    parser.add_argument("--no-rescan", action="store_true", help="Skip live hub rescan")
    args = parser.parse_args()

    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.date):
        print(f"Error: invalid date '{args.date}' (expected YYYY-MM-DD)", file=sys.stderr)
        return 1

    hub_dir = resolve_hub_dir(args.dir)
    if not hub_dir.is_dir():
        print(f"Error: hub directory does not exist: {hub_dir}", file=sys.stderr)
        return 1

    category_slug = slugify(args.category)
    title_slug = slugify(args.title)[:60]
    target_dir = (hub_dir / category_slug).resolve()
    if not target_dir.is_relative_to(hub_dir):
        print("Error: invalid category path", file=sys.stderr)
        return 1

    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / f"{args.date}-{title_slug}.md"
    if target_file.exists():
        print(f"Error: entry already exists: {target_file}", file=sys.stderr)
        return 1

    tag_list = [t for t in args.tags.split(",") if t.strip()]
    content = build_markdown(
        title=args.title,
        date_str=args.date,
        host=args.host,
        status=args.status,
        tags=tag_list,
    )
    target_file.write_text(content, encoding="utf-8")
    print(f"Created {target_file}")

    if not args.no_rescan:
        trigger_rescan(args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
