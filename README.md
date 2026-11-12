# Troubleshooting Hub

A lightweight, zero-dependency local web renderer and full-text search portal for Markdown troubleshooting playbooks and post-mortems.

## Features
- **Local-only HTTP server** (`127.0.0.1:8898` by default) with strict directory confinement.
- **Formatted directory indexing:** Automatically scans category subdirectories (`*.md`) plus optional read-only `--extra-dir` paths (`TROUBLE_EXTRA_DIRS`).
- **Instant full-text & metadata search:** Filters across title, tags, host, status, folder, and document body with highlighted match snippets (`/` to focus search, `Esc` to close/clear).
- **Zero-dependency Markdown reader:** Renders headings, GFM tables, fenced code blocks with one-click copy, blockquotes, task lists, and a live Table of Contents.
- **Privacy-first `.gitignore`:** Personal Markdown entries and `files.json` are ignored by default so you can keep your real host logs local while sharing the tool publicly.
- **Antigravity Skill included:** See [skill/troubleshooting-documenter/SKILL.md](skill/troubleshooting-documenter/SKILL.md) to let your AI assistant automatically recognize debugging sessions and document them into formatted directories.

## Quick Start

```bash
# Run directly
python3 server.py

# Or install the CLI helpers to ~/bin (or any directory on your PATH)
chmod +x bin/troubleup bin/troubledown
./bin/troubleup
```

Open `http://127.0.0.1:8898/` in your browser. Stop the server anytime with `./bin/troubledown`.

### Optional Environment Variables
- `TROUBLE_PORT` — Port to bind (default `8898`)
- `TROUBLE_HOST` — Bind address (default `127.0.0.1`)
- `TROUBLE_DIR` — Path to your troubleshooting hub directory
- `TROUBLE_EXTRA_DIRS` — Optional colon-separated read-only Markdown directories to include

## Entry Format
Create category subdirectories (for example `boot-and-startup/`, `network-and-ports/`) and start entries from [templates/TEMPLATE.md](templates/TEMPLATE.md):

```markdown
# Short Descriptive Title

- **Date**: YYYY-MM-DD
- **Host**: pc | server
- **Status**: Fixed | Monitoring | Recurring | Playbook
- **Tags**: systemd, cgroup, boot
```
