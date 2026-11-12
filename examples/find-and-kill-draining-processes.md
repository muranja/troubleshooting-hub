# How to Find Draining Processes and Safely Kill Them

- **Date**: 2026-11-12
- **Host**: workstation
- **Status**: Playbook
- **Tags**: cpu, memory, swap, processes, kill, systemd, cgroup, diagnostics

## Symptom
The machine becomes sluggish, fans spin loudly, or RAM/swap fills up (`kswapd0` using CPU), and you need to identify which process is draining resources and stop it safely without breaking state or triggering instant respawns.

## Step 1: Identify What Is Draining the Machine
```bash
# Check overall RAM and swap pressure
free -h

# Top 15 CPU consumers
ps -eo pid,ppid,user,%cpu,%mem,rss:8,etime,args --sort=-%cpu | head -n 16

# Top 15 RAM (RSS) consumers
ps -eo pid,ppid,user,%cpu,%mem,rss:8,etime,args --sort=-%mem | head -n 16

# Roll up CPU and memory by systemd service / app cgroup
systemd-cgtop -n 1 --depth=3
```

**Why each check is necessary:**
- `free -h`: Distinguishes pure CPU load from **memory exhaustion / swap thrashing** (when `Mem available` is low, `Swap used` is high, and `kswapd0` climbs in CPU).
- `ps --sort=-%cpu` & `--sort=-%mem`: Reveals exact `PID`, `PPID`, `RSS` (real resident memory in KiB), uptime (`ELAPSED`), and full command arguments.
- `systemd-cgtop`: Aggregates multi-process apps (browsers, IDEs, containers, emulators) under one slice/scope so distributed memory hogs do not hide across 20 small PIDs.

## Step 2: Check Ownership Before Killing
```bash
# Replace <PID> with the target process ID
cat /proc/<PID>/cgroup
ps -fp $(ps -o ppid= -p <PID>)
```

**Why this is necessary:**
- Killing a worker spawned by a `systemd` service (`Restart=always`), a Docker restart policy, or an active background runner will only make it **respawn seconds later** with a new PID.
- `/proc/<PID>/cgroup` immediately tells you whether the process is standalone, inside a `systemd` service, inside a desktop app scope, or inside a container.

## Step 3: Safely Stop or Kill the Process
```bash
# 1. Request a graceful shutdown first (allows lockfiles and state to flush)
kill -TERM <PID>

# 2. Verify whether it exited (wait ~3-5 seconds)
ps -fp <PID>

# 3. Force-kill ONLY if it is hung and ignored SIGTERM
kill -KILL <PID>
```

If the process belongs to a `systemd` unit/scope or keeps respawning:
```bash
# User service or desktop app scope
systemctl --user stop <unit-or-scope-name>

# System service
sudo systemctl stop <service-name>
```

Always preview pattern matches first, and use a bracketed regex (`[p]attern`) or explicit numeric PIDs so `pkill -f` never matches and kills its own `bash -c` shell:
```bash
pgrep -af '[p]attern'
PIDS=$(pgrep -f '[p]attern')
[ -n "$PIDS" ] && kill -TERM $PIDS
```

## Verification
Re-run `ps` and `free -h` to confirm the PID is gone and CPU/memory pressure dropped:
```bash
ps -fp <PID> || echo "Process stopped"
free -h
```

