#!/usr/bin/env python3
"""
os-update-checker: Check for available apt package updates and fetch changelogs.

Outputs a summary of upgradable packages with per-package changelog summaries
and risk level (security vs standard) — read-only, no packages are installed.
"""

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field, asdict


@dataclass
class PackageUpdate:
    name: str
    current_version: str
    new_version: str
    source: str
    is_security: bool
    changelog_summary: str = ""


def run(cmd: list[str], timeout: int = 30) -> str:
    """Run a command and return stdout, or empty string on error."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def get_upgradable_packages() -> list[PackageUpdate]:
    """Parse `apt list --upgradable` output into PackageUpdate objects."""
    output = run(["apt", "list", "--upgradable"])
    packages: list[PackageUpdate] = []

    for line in output.splitlines():
        if line.startswith("Listing") or not line.strip():
            continue
        # Format: name/source version arch [upgradable from: old_version]
        try:
            parts = line.split()
            name_source = parts[0]  # e.g. "nodejs/noble-updates"
            new_version = parts[1]
            source = parts[0].split("/")[1] if "/" in parts[0] else "unknown"
            name = name_source.split("/")[0]

            old_version = ""
            if "upgradable from:" in line:
                old_version = line.split("upgradable from:")[-1].strip().rstrip("]")

            is_security = "-security" in source

            packages.append(PackageUpdate(
                name=name,
                current_version=old_version,
                new_version=new_version,
                source=source,
                is_security=is_security,
            ))
        except (IndexError, ValueError):
            continue

    return packages


def fetch_changelog_summary(package: str, max_lines: int = 40) -> str:
    """
    Fetch the most recent changelog entry for a package via `apt changelog`.
    Returns the first entry (most recent version block) only.
    """
    raw = run(["apt", "changelog", package], timeout=60)
    if not raw:
        return "No changelog available."

    lines = raw.splitlines()
    entry_lines: list[str] = []
    in_entry = False

    for line in lines:
        # Debian changelog entries start with "package (version) suite;"
        if not in_entry and line and not line.startswith(" ") and "(" in line:
            in_entry = True
            entry_lines.append(line)
            continue
        if in_entry:
            # A new top-level entry (next version block) ends the first entry
            if line and not line.startswith(" ") and "(" in line and entry_lines:
                break
            entry_lines.append(line)
            if len(entry_lines) >= max_lines:
                break

    summary = "\n".join(entry_lines).strip()
    return summary if summary else "No changelog available."


def classify_risk(pkg: PackageUpdate) -> str:
    """Return a human-readable risk label."""
    if pkg.is_security:
        return "🔴 security"
    name_lower = pkg.name.lower()
    critical_pkgs = {"linux-image", "linux-kernel", "openssh", "openssl", "libc", "glibc"}
    if any(c in name_lower for c in critical_pkgs):
        return "🟡 moderate"
    return "🟢 low"


def format_text(packages: list[PackageUpdate]) -> str:
    """Format results as human-readable text."""
    if not packages:
        return "✅ System is up to date — no packages to upgrade."

    security = [p for p in packages if p.is_security]
    standard = [p for p in packages if not p.is_security]

    lines: list[str] = [
        f"📦 {len(packages)} package(s) upgradable"
        + (f" — ⚠️ {len(security)} security update(s)" if security else ""),
        "",
    ]

    for pkg in packages:
        risk = classify_risk(pkg)
        lines.append(f"**{pkg.name}** {pkg.current_version} → {pkg.new_version}")
        lines.append(f"  Source: {pkg.source}  |  Risk: {risk}")
        lines.append(f"  Changelog:")
        for cl in pkg.changelog_summary.splitlines()[:12]:
            lines.append(f"    {cl}")
        lines.append("")

    return "\n".join(lines)


def format_json(packages: list[PackageUpdate]) -> str:
    """Format results as JSON."""
    data = {
        "total": len(packages),
        "security_count": sum(1 for p in packages if p.is_security),
        "packages": [
            {
                "name": p.name,
                "current_version": p.current_version,
                "new_version": p.new_version,
                "source": p.source,
                "is_security": p.is_security,
                "risk": classify_risk(p),
                "changelog_summary": p.changelog_summary,
            }
            for p in packages
        ],
    }
    return json.dumps(data, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check for apt package updates with changelog summaries."
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--no-changelog",
        action="store_true",
        help="Skip fetching changelogs (faster, less detail)",
    )
    args = parser.parse_args()

    packages = get_upgradable_packages()

    if not args.no_changelog:
        for pkg in packages:
            pkg.changelog_summary = fetch_changelog_summary(pkg.name)

    if args.format == "json":
        print(format_json(packages))
    else:
        print(format_text(packages))


if __name__ == "__main__":
    main()
