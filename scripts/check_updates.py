#!/usr/bin/env python3
"""
os-update-checker: Check for available apt package updates and fetch changelogs.

Outputs a summary of upgradable packages with per-package changelog summaries
and risk level (security vs standard). Read-only — no packages are installed
or modified. subprocess is used with shell=False to call read-only apt commands;
package names are validated against an allowlist pattern before use.
"""

import argparse
import json
import re
import subprocess
from dataclasses import dataclass


# Allowlist: apt package names are lowercase alphanumeric plus hyphen, dot, plus.
_SAFE_PACKAGE_NAME = re.compile(r"^[a-z0-9][a-z0-9.+\-]*$")

# Packages whose names indicate higher operational risk if something goes wrong.
_MODERATE_RISK_SUBSTRINGS: tuple[str, ...] = (
    "linux-image",
    "linux-kernel",
    "openssh",
    "openssl",
    "libc",
    "glibc",
)


@dataclass
class PackageUpdate:
    """Represents a single apt package that has an available upgrade."""

    name: str
    current_version: str
    new_version: str
    source: str
    is_security: bool
    changelog_summary: str = ""


def _run_command(cmd: list[str], timeout: int = 30) -> str:
    """
    Run a command with shell=False and return stdout as a string.

    shell=False is required — arguments are passed as a list, never
    interpolated into a shell string, preventing injection. Returns an
    empty string on any error rather than raising.
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,  # explicit: never interpret cmd as a shell string
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return ""
    except FileNotFoundError:
        return ""
    except OSError:
        return ""


def _sanitize_package_name(name: str) -> str | None:
    """
    Validate a package name against the Debian naming allowlist.

    Returns the name unchanged if valid, or None if it contains unexpected
    characters. This is a defence-in-depth measure; shell=False already
    prevents injection, but we reject obviously malformed names early.
    """
    if _SAFE_PACKAGE_NAME.match(name):
        return name
    return None


def get_upgradable_packages() -> list[PackageUpdate]:
    """
    Return a list of packages that have available upgrades.

    Calls `apt list --upgradable` (read-only) and parses each line.
    Lines that cannot be parsed are silently skipped.
    """
    output = _run_command(["apt", "list", "--upgradable"])
    packages: list[PackageUpdate] = []

    for line in output.splitlines():
        if line.startswith("Listing") or not line.strip():
            continue

        try:
            parts = line.split()
            if len(parts) < 2:
                continue

            # apt format: "name/source new_version arch [upgradable from: old]"
            name_field = parts[0]  # e.g. "nodejs/nodesource"
            new_version = parts[1]
            name = name_field.split("/")[0]
            source = name_field.split("/")[1] if "/" in name_field else "unknown"

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


def fetch_changelog_summary(package_name: str, max_lines: int = 40) -> str:
    """
    Return the most recent changelog entry for a package via `apt changelog`.

    The package name is validated before use. Returns a plain-text string
    containing the first version block from the Debian changelog format,
    truncated to max_lines lines.
    """
    safe_name = _sanitize_package_name(package_name)
    if safe_name is None:
        return "Skipped: package name failed validation."

    raw = _run_command(["apt", "changelog", safe_name], timeout=60)
    if not raw:
        return "No changelog available."

    entry_lines: list[str] = []
    in_entry = False

    for line in raw.splitlines():
        # Debian changelog top-level entries start with a non-indented line
        # containing a parenthesised version, e.g. "nodejs (22.22.1) ..."
        is_header = bool(line) and not line.startswith(" ") and "(" in line

        if not in_entry and is_header:
            in_entry = True
            entry_lines.append(line)
            continue

        if in_entry:
            if is_header:
                break  # second entry starts — we only want the first
            entry_lines.append(line)
            if len(entry_lines) >= max_lines:
                break

    summary = "\n".join(entry_lines).strip()
    return summary if summary else "No changelog available."


def classify_risk(pkg: PackageUpdate) -> str:
    """
    Return a risk label string for a package.

    - security: source repo contains '-security'
    - moderate: package name matches a known high-impact substring
    - low: everything else
    """
    if pkg.is_security:
        return "🔴 security"
    name_lower = pkg.name.lower()
    if any(substr in name_lower for substr in _MODERATE_RISK_SUBSTRINGS):
        return "🟡 moderate"
    return "🟢 low"


def format_text(packages: list[PackageUpdate]) -> str:
    """Format the package list as a human-readable text report."""
    if not packages:
        return "✅ System is up to date — no packages to upgrade."

    security_count = sum(1 for p in packages if p.is_security)
    header = f"📦 {len(packages)} package(s) upgradable"
    if security_count:
        header += f" — ⚠️ {security_count} security update(s)"

    lines: list[str] = [header, ""]

    for pkg in packages:
        risk = classify_risk(pkg)
        lines.append(f"**{pkg.name}** {pkg.current_version} → {pkg.new_version}")
        lines.append(f"  Source: {pkg.source}  |  Risk: {risk}")
        lines.append("  Changelog:")
        for cl_line in pkg.changelog_summary.splitlines()[:12]:
            lines.append(f"    {cl_line}")
        lines.append("")

    return "\n".join(lines)


def format_json(packages: list[PackageUpdate]) -> str:
    """Format the package list as a JSON string."""
    data: dict = {
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
    """Parse arguments, fetch updates, and print the report."""
    parser = argparse.ArgumentParser(
        description="Check for apt package updates with per-package changelog summaries.",
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
        help="Skip fetching changelogs for faster output",
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
