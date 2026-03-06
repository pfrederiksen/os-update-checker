# OS Update Checker

[![ClawHub](https://img.shields.io/badge/ClawHub-os--update--checker-blue)](https://clawhub.com/pfrederiksen/os-update-checker)
[![Version](https://img.shields.io/badge/version-1.0.0-green)]()

An [OpenClaw](https://openclaw.ai) skill that lists available apt package updates, fetches changelogs for each package, and classifies risk — so you know exactly what's changing before you approve an upgrade.

## Features

- 📦 **Full upgradable package list** — name, version delta, source repo
- 📋 **Per-package changelogs** — fetches the most recent entry from Ubuntu's changelog server
- 🔴🟡🟢 **Risk classification** — security, moderate (kernel/openssl/openssh), or low
- 📄 **JSON output** — `--format json` for dashboards and cron
- ⚡ **`--no-changelog` flag** — fast mode when you just need the count
- 🔒 **Read-only** — never installs or modifies anything

## Installation

```bash
clawhub install os-update-checker
```

## Usage

```bash
# Full summary with changelogs
python3 scripts/check_updates.py

# JSON output
python3 scripts/check_updates.py --format json

# Quick count only
python3 scripts/check_updates.py --no-changelog
```

## Example Output

```
📦 2 package(s) upgradable

**nodejs** 22.22.0 → 22.22.1
  Source: nodesource  |  Risk: 🟢 low
  Changelog:
    nodejs (22.22.1) ...
    * cli: mark --heapsnapshot-near-heap-limit as stable
    * build: test on Python 3.14

**linux-base** 4.5ubuntu9+24.04.1 → 4.5ubuntu9+24.04.2
  Source: noble-updates  |  Risk: 🟢 low
  Changelog:
    linux-base (4.5ubuntu9+24.04.2) noble; urgency=medium
    * Add missing Apport links for HWE kernel packages
```

## Requirements

- Python 3.10+
- Debian/Ubuntu with `apt`
- Outbound HTTPS to `changelogs.ubuntu.com` (or use `--no-changelog`)

## License

MIT

## Links

- [ClawHub](https://clawhub.com/pfrederiksen/os-update-checker)
- [OpenClaw](https://openclaw.ai)
