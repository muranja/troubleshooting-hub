# Troubleshooting Hub

A lightweight, zero-dependency local web renderer, full-text search portal, and Antigravity skill for Markdown troubleshooting playbooks and post-mortems.

## Features
- **Local-only HTTP server** (`127.0.0.1:8898` by default) with strict directory confinement.
- **Formatted directory indexing:** Automatically scans category subdirectories (`*.md`) plus optional read-only `--extra-dir` paths (`TROUBLE_EXTRA_DIRS`).
- **Instant full-text & metadata search:** Filters across title, tags, host, status, folder, and document body with highlighted match snippets (`/` to focus search, `Esc` to close/clear).
- **Zero-dependency Markdown reader:** Renders headings, GFM tables, fenced code blocks with one-click copy, blockquotes, task lists, and a live Table of Contents.
- **Antigravity Skill included:** [skill/troubleshooting-documenter/SKILL.md](skill/troubleshooting-documenter/SKILL.md) teaches Antigravity to recognize debugging sessions, proactively offer to document the issue + why each check is necessary, and refresh the local hub.
- **Privacy-first `.gitignore`:** Personal Markdown entries and `files.json` are ignored by default so your real host logs never get pushed to GitHub.

---

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/muranja/troubleshooting-hub.git ~/Desktop/troubleshooting
cd ~/Desktop/troubleshooting
```

*(You can clone it anywhere—if not `~/Desktop/troubleshooting`, set `export TROUBLE_DIR="/path/to/troubleshooting"` in your shell profile.)*

### 2. Install CLI commands (`troubleup` / `troubledown`) & Antigravity skill
Run the included installer:

```bash
chmod +x install.sh
./install.sh
```

What `./install.sh` does:
- Symlinks `bin/troubleup` and `bin/troubledown` into `~/.local/bin` (override with `--bin-dir ~/bin`).
- Links `skill/troubleshooting-documenter` into `~/.agents/skills/troubleshooting-documenter` and `~/.gemini/antigravity/skills/troubleshooting-documenter` (skip with `--no-skill`).

Verify your setup:
```bash
which troubleup troubledown
troubleup
```

Then open **http://127.0.0.1:8898/** in your browser. Stop the server anytime with `troubledown`.

---

## Manual Setup (Alternative)
If you prefer not to run `install.sh`:

```bash
# Run directly without installing CLI links
python3 server.py --host 127.0.0.1 --port 8898

# Or install the Antigravity skill manually
mkdir -p ~/.gemini/antigravity/skills ~/.agents/skills
ln -sfn "$PWD/skill/troubleshooting-documenter" ~/.agents/skills/troubleshooting-documenter
ln -sfn ~/.agents/skills/troubleshooting-documenter ~/.gemini/antigravity/skills/troubleshooting-documenter
```

### Configuration Environment Variables
- `TROUBLE_PORT` — Port to bind (default `8898`)
- `TROUBLE_HOST` — Bind address (default `127.0.0.1`)
- `TROUBLE_DIR` — Path to your troubleshooting hub directory
- `TROUBLE_EXTRA_DIRS` — Colon-separated read-only Markdown directories to include in search (e.g. `export TROUBLE_EXTRA_DIRS="$HOME/docs/troubleshooting"`)

---

## Adding Troubleshooting Entries

Create category subdirectories (for example `boot-and-startup/`, `network-and-ports/`, `systemd-and-services/`, `app-debugging/`) or use the skill helper script:

```bash
python3 skill/troubleshooting-documenter/scripts/new_entry.py \
  --title "Nginx fails on boot waiting for VPN interface" \
  --category "network-and-ports" \
  --host "vps" \
  --status "Fixed" \
  --tags "nginx,systemd,vpn,boot"
```

Every `.md` entry uses [templates/TEMPLATE.md](templates/TEMPLATE.md) metadata headers right below `# Title`:

```markdown
# Short Descriptive Title

- **Date**: YYYY-MM-DD
- **Host**: pc | server
- **Status**: Fixed | Monitoring | Recurring | Playbook
- **Tags**: systemd, cgroup, boot
```

Restart Antigravity (or open a new conversation) after installing the skill so it picks up `troubleshooting-documenter` automatically.
