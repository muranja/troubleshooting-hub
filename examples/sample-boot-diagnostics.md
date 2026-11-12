# Unexpected Background Process After Reboot: 8-Check Playbook

- **Date**: 2026-01-01
- **Host**: workstation
- **Status**: Playbook
- **Tags**: boot, systemd, cgroup, journalctl, diagnostics

## Symptom
A resource-heavy process appears automatically after a reboot or desktop login without being launched manually from a terminal.

## Root Cause
Background processes on modern Linux can be initiated by user `systemd` units, transient desktop scopes, IDE/agent session auto-resume, XDG autostart entries, or `@reboot` cron jobs—often reparenting to PID 1 or `systemd --user` so `ps` alone hides the true launcher.

## The 8 Diagnostic Checks (and Why Each One Is Necessary)

| # | Check | Why It Is Necessary |
|---|---|---|
| 1 | `ps aux` + `systemctl list-unit-files --state=enabled` | Confirms exact binary/PID and rules out standard system/user services |
| 2 | `ps -eo pid,ppid,lstart,cmd` + `pstree -aps <pid>` + `/proc/<pid>/cgroup` | Cgroups retain the original transient scope even after `nohup`/daemon reparenting |
| 3 | `systemctl --user status <scope>` + `~/.config/autostart/` + `crontab -l` | Lists sibling processes in the same cgroup and eliminates login autostart / `@reboot` cron |
| 4 | `uptime -s` + `systemd-cgls` + `~/.bashrc` / `~/.profile` | Separates kernel-boot launches from post-login or interactive shell triggers |
| 5 | `journalctl --user --since ...` | Identifies the exact desktop launcher (`gnome-shell`, timer, daemon) that created the scope |
| 6 | Application-specific logs | Reveals internal commands executed inside a parent app or runner |
| 7 | Application state DB / config (read-only) | Explains *why* the parent app executed that command (e.g., resumed task vs. schedule) |
| 8 | Final `ps -ef` verification | Confirms live process state after cleanup or remediation |
