---
name: troubleshooting-documenter
description: >-
  Recognizes when a technical problem, bug, outage, or root-cause debugging session
  is being investigated or resolved, proactively offers to document it into the
  local Troubleshooting Hub, formats entries with Symptom/Root Cause/Diagnostic Checks
  & Why They Are Necessary/Verification/Prevention, and keeps personal logs gitignored.
---

# Troubleshooting Documenter Skill

Use this skill whenever the conversation involves debugging, root-cause analysis, fixing a broken service/build/boot issue, or resolving unexpected system behavior.

## 1. Recognize & Offer Documentation
When a non-trivial issue has been diagnosed or fixed (or while actively investigating a multi-step issue):
- Proactively offer: *"Would you like me to add this issue and its diagnostic checks to your Troubleshooting Hub?"*
- If the user asks to document, save, or log the problem, create the entry directly.

## 2. Directory & Naming Convention
1. Place entries inside a formatted kebab-case category directory under the Troubleshooting Hub root (`$TROUBLE_DIR`, default `~/Desktop/troubleshooting`), such as `boot-and-startup/`, `network-and-ports/`, `systemd-and-services/`, or `build-and-deploy/`.
2. Name the file `YYYY-MM-DD-<short-kebab-slug>.md`.
3. Follow `templates/TEMPLATE.md`.

## 3. Required Entry Structure
Include these metadata fields directly below `# <Title>` so the search indexer extracts them automatically:

```markdown
# <Concise Problem Title>

- **Date**: YYYY-MM-DD
- **Host**: pc | vps | <target>
- **Status**: Fixed | Monitoring | Recurring | Playbook
- **Tags**: comma, separated, lowercase, keywords
```

Include:
- `## Symptom` — Exact error text or observed behavior.
- `## Root Cause` — Underlying cause.
- `## Diagnostic Checks & Fix` — Exact commands and **why each check is necessary**.
- `## Verification` — Command and expected output proving the fix.
- `## Prevention` — Concrete rule or preflight check to prevent recurrence.

## 4. Refresh & Privacy Guardrails
- Trigger a live rescan if the local server is up:
  `curl -s -X POST http://127.0.0.1:8898/api/rescan || true`
- **Never** force-add (`git add -f`) personal Markdown logs or `files.json` into git; verify `git status` before committing tool updates.
