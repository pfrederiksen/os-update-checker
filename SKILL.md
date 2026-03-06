---
name: os-update-checker
description: "Check for available apt/OS package updates with per-package changelog summaries and risk classification. Use when: checking system update status, before approving upgrades, or in heartbeats/cron for periodic OS health monitoring. Reports security vs standard updates, changelog notes, and risk level. Read-only — does not install or modify anything."
---

# OS Update Checker

Read-only apt update checker. Lists upgradable packages, fetches changelogs for each, and classifies risk level (security, moderate, low). Designed to give enough context to approve or defer an upgrade — no guessing required.

## Usage

```bash
# Human-readable summary with changelogs
python3 scripts/check_updates.py

# JSON output (for dashboards, cron, integrations)
python3 scripts/check_updates.py --format json

# Skip changelogs for a quick count
python3 scripts/check_updates.py --no-changelog
```

## Output

**Text mode:** Per-package summary showing version delta, source repo, risk level, and top changelog lines.

**JSON mode:**
```json
{
  "total": 2,
  "security_count": 0,
  "packages": [
    {
      "name": "nodejs",
      "current_version": "22.22.0",
      "new_version": "22.22.1",
      "source": "noble-updates",
      "is_security": false,
      "risk": "🟢 low",
      "changelog_summary": "nodejs (22.22.1) ...\n  * cli: mark --heapsnapshot..."
    }
  ]
}
```

## Risk Classification

- 🔴 **security** — source repo contains `-security` (e.g. `noble-security`)
- 🟡 **moderate** — critical system packages (kernel, openssh, openssl, libc)
- 🟢 **low** — standard maintenance updates

## How It Works

1. Runs `apt list --upgradable` to enumerate packages needing updates
2. For each package, fetches the most recent changelog entry via `apt changelog <package>`
3. Classifies risk based on source repo and package name
4. Reports in text or JSON format

## What It Does NOT Do

- Does not run `apt upgrade` or install anything
- Does not write to any files
- Does not restart any services

## System Access

- **Commands:** `apt list --upgradable` (read-only), `apt changelog <package>` (fetches from changelogs.ubuntu.com)
- **Network:** Outbound HTTPS to `changelogs.ubuntu.com` per package (read-only)
- **No file writes**

## Requirements

- Python 3.10+
- `apt` available (Debian/Ubuntu)
- Outbound HTTPS for changelog fetching (or use `--no-changelog` to skip)
