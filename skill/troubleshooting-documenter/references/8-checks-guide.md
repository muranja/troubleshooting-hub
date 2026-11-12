# 8-Check Boot & Process Investigation Reference

When diagnosing an unexpected background process or boot-time launch, follow this 8-step funnel and document **why each check is necessary**:

1. **Running processes & enabled `systemd` units** (`ps aux`, `systemctl list-unit-files --state=enabled`) — Confirms exact PID/binary/flags and eliminates persistent services.
2. **Parent PID, `pstree`, & `/proc/<pid>/cgroup`** — Recovers the true owning cgroup/scope even when `nohup` or daemonization reparents the process to PID 1 or `systemd --user`.
3. **Scope status, user units, XDG autostart, & `crontab`** — Lists sibling processes in the same cgroup and eliminates login `.desktop` autostarts and `@reboot` cron jobs.
4. **Boot timestamp (`uptime -s`), `systemd-cgls`, & shell RC files** — Separates kernel-boot launches from post-login or interactive shell triggers.
5. **User journal (`journalctl --user`) & app log discovery** — Pinpoints the desktop or daemon event (`gnome-shell`, timer, service) that created the scope.
6. **Application-specific logs** — Reveals internal commands spawned inside a parent application or runner.
7. **Application state database / config (read-only)** — Explains *why* the parent application ran that command (e.g., auto-resumed suspended task vs. schedule).
8. **Final live process verification & cleanup** — Confirms live state before/after remediation and ensures no stray diagnostic tasks remain.
