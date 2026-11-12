---
name: troubleshooting-documenter
description: >-
  Recognizes when a technical problem, bug, outage, or root-cause investigation
  is being handled or resolved ("huddling" on an issue), proactively offers to
  document it into the local Troubleshooting Hub in formatted category folders
  with Symptom, Root Cause, Diagnostic Checks & Why They Are Necessary,
  Verification, and Prevention, and keeps personal entries safely gitignored.
---

# Troubleshooting Documenter Skill

Use this skill whenever a conversation involves debugging a failure, tracing an unexpected process, fixing a broken service/build/theme, or running multi-step diagnostic checks.

## 1. Recognize & Offer Documentation
When a non-trivial problem is actively investigated or resolved:
1. Proactively ask the user at a natural stopping point:
   > *"Would you like me to document this issue and its diagnostic checks in your Troubleshooting Hub?"*
2. If the user already asked to log, record, or save the troubleshooting steps, create the entry immediately.

## 2. Choose the Formatted Category Directory
Locate the hub directory (`$TROUBLE_DIR`, default `~/Desktop/troubleshooting`). Place entries inside a clean kebab-case category folder:
- `boot-and-startup/` — Boot, systemd, cgroup, autostart, and background process issues
- `network-and-ports/` — Firewall, nginx, TLS, DNS, tunnels, and port conflicts
- `systemd-and-services/` — User/system daemons, timers, and unit failures
- `build-and-deploy/` — Build pipelines, packaging, CI, and deployment regressions
- `app-debugging/` — Runtime crashes, state DBs, UI/CSS regressions, and SDK issues

Name files `YYYY-MM-DD-<short-kebab-slug>.md`. You can scaffold a new file and auto-rescan the hub with [scripts/new_entry.py](./scripts/new_entry.py):

```bash
python3 scripts/new_entry.py \
  --title "Short descriptive title" \
  --category "boot-and-startup" \
  --host "pc" \
  --status "Fixed" \
  --tags "systemd,cgroup,boot"
```

## 3. Required Entry Structure
Keep these exact metadata fields right under `# <Title>` so the hub's search index and filter pills parse them cleanly:

```markdown
# <Concise Problem Title>

- **Date**: YYYY-MM-DD
- **Host**: pc | vps | <target>
- **Status**: Fixed | Monitoring | Recurring | Playbook
- **Tags**: comma, separated, lowercase, keywords
```

Include these sections:
1. **`## Symptom`** — Exact error text, failing command, or observed signature.
2. **`## Root Cause`** — The actual underlying reason (not the initial guess).
3. **`## Diagnostic Checks & Fix`** — Exact commands run (failing → passing) and **why each check is necessary** (for boot/process mysteries, see [references/8-checks-guide.md](./references/8-checks-guide.md)).
4. **`## Verification`** — Exact command and observed output proving the issue is fixed.
5. **`## Prevention`** — Concrete guardrail or rule to stop recurrence.

## 4. Refresh the Live Local Hub
If the hub is running on `127.0.0.1:8898`, trigger a rescan so the new entry becomes searchable immediately:

```bash
curl -s -X POST "http://127.0.0.1:${TROUBLE_PORT:-8898}/api/rescan" || true
```

## 5. Git & Privacy Guardrails
- The Troubleshooting Hub repository ignores personal Markdown logs (`*.md`, category folders, and `files.json`) via `.gitignore`.
- **Never** `git add -f` personal incident files, host IPs, credentials, or `files.json` into git.
- Run `git status` before committing any tool updates to verify only public tool/template/skill files are tracked.
