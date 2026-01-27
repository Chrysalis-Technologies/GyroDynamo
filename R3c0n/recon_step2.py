#!/usr/bin/env python3
"""
Post-recon summarizer for recon.sh outputs.

Reads recon_*.json files and produces a human-readable checklist
based on the captured surface-level data (no new scanning).
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


HEADER_NAMES = [
    "strict-transport-security",
    "content-security-policy",
    "x-frame-options",
    "x-content-type-options",
    "referrer-policy",
    "permissions-policy",
]


@dataclass
class ReconReport:
    path: Path
    target: str
    scan: str
    dns: str
    subdomains: str
    web: str
    ssl: str


def _parse_ports(scan_text: str) -> List[Tuple[str, str, str, str]]:
    ports = []
    for line in scan_text.splitlines():
        line = line.strip()
        # Nmap style: 80/tcp open http Microsoft IIS httpd 10.0
        m = re.match(r"^(\d+/\w+)\s+(\w+)\s+([-/\w]+)\s*(.*)$", line)
        if m:
            ports.append((m.group(1), m.group(2), m.group(3), m.group(4).strip()))
            continue
        # Masscan style: Discovered open port 80/tcp on 1.2.3.4
        m = re.match(r"^Discovered open port (\d+/\w+)", line)
        if m:
            ports.append((m.group(1), "open", "unknown", ""))
    return ports


def _section_after(label: str, text: str) -> str:
    pattern = re.compile(rf"^# {re.escape(label)}\s*$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return ""
    start = match.end()
    following = text[start:]
    next_header = re.search(r"^# .+$", following, re.MULTILINE)
    end = start + (next_header.start() if next_header else len(following))
    return text[start:end].strip()


def _parse_dns(dns_text: str) -> Dict[str, List[str]]:
    records = {}
    for label in ["dig A", "dig MX", "dig NS", "dig TXT", "Reverse PTR"]:
        body = _section_after(label, dns_text)
        lines = [ln.strip() for ln in body.splitlines() if ln.strip() and not ln.strip().startswith("#")]
        records[label] = lines
    return records


def _parse_subdomains(sub_text: str) -> List[str]:
    lines = []
    for ln in sub_text.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        if "not installed" in ln.lower():
            continue
        lines.append(ln)
    return lines


def _parse_web_headers(web_text: str) -> Dict[str, Dict[str, str]]:
    headers_by_url: Dict[str, Dict[str, str]] = {}
    blocks = re.split(r"^# Headers for (.+)$", web_text, flags=re.MULTILINE)
    if len(blocks) <= 1:
        return headers_by_url
    it = iter(blocks)
    _ = next(it, None)  # preamble
    for url, rest in zip(it, it):
        header_block = rest.split("# Wayback URLs for", 1)[0]
        headers: Dict[str, str] = {}
        for line in header_block.splitlines():
            if ":" not in line:
                continue
            key, val = line.split(":", 1)
            headers[key.strip().lower()] = val.strip()
        headers_by_url[url.strip()] = headers
    return headers_by_url


def _parse_wayback_counts(web_text: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    blocks = re.split(r"^# Wayback URLs for (.+)$", web_text, flags=re.MULTILINE)
    if len(blocks) <= 1:
        return counts
    it = iter(blocks)
    _ = next(it, None)
    for url, rest in zip(it, it):
        lines = [ln.strip() for ln in rest.splitlines() if ln.strip() and not ln.startswith("#")]
        # Wayback section might include "waybackurls not installed"
        if lines and "not installed" in lines[0].lower():
            counts[url.strip()] = 0
        else:
            counts[url.strip()] = len(lines)
    return counts


def _parse_ssl(ssl_text: str) -> Dict[str, str]:
    data = {}
    for line in ssl_text.splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        key, val = line.split("=", 1)
        data[key.strip()] = val.strip()
    return data


def _days_until(date_str: str) -> Optional[int]:
    for fmt in ("%b %d %H:%M:%S %Y %Z", "%b %d %H:%M:%S %Y GMT"):
        try:
            dt = datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            return int((dt - now).total_seconds() // 86400)
        except ValueError:
            continue
    return None


def load_report(path: Path) -> ReconReport:
    data = json.loads(path.read_text())
    return ReconReport(
        path=path,
        target=data.get("target", path.stem),
        scan=data.get("scan", ""),
        dns=data.get("dns", ""),
        subdomains=data.get("subdomains", ""),
        web=data.get("web", ""),
        ssl=data.get("ssl", ""),
    )


def iter_reports(paths: Iterable[Path]) -> Iterable[ReconReport]:
    for path in paths:
        if path.is_dir():
            for item in sorted(path.glob("recon_*.json")):
                yield load_report(item)
        else:
            yield load_report(path)


def summarize_structured(report: ReconReport) -> Dict[str, Any]:
    ports = _parse_ports(report.scan)
    dns_records = _parse_dns(report.dns)
    subdomains = _parse_subdomains(report.subdomains)
    headers_by_url = _parse_web_headers(report.web)
    wayback_counts = _parse_wayback_counts(report.web)
    ssl = _parse_ssl(report.ssl)

    open_services = [
        {
            "port": port,
            "state": state,
            "service": service,
            "version": version,
        }
        for port, state, service, version in ports
    ]

    missing_headers_by_url: Dict[str, List[str]] = {}
    server_banners: Dict[str, str] = {}
    for url, headers in headers_by_url.items():
        missing = [h for h in HEADER_NAMES if h not in headers]
        if missing:
            missing_headers_by_url[url] = missing
        server = headers.get("server")
        if server:
            server_banners[url] = server

    not_after = ssl.get("notAfter")
    days_until_expiry = _days_until(not_after) if not_after else None

    checklist: List[str] = []
    if ports:
        for port, _state, service, version in ports:
            version_str = f" ({version})" if version else ""
            checklist.append(f"Review exposed service: {port} {service}{version_str}")

    for label, recs in dns_records.items():
        if label in ("dig MX", "dig NS", "dig TXT") and not recs:
            checklist.append(f"DNS: {label.replace('dig ', '')} records not present in output.")

    for url, missing in missing_headers_by_url.items():
        missing_list = ", ".join(missing)
        checklist.append(f"Web headers for {url}: missing {missing_list}")

    for url, server in server_banners.items():
        checklist.append(f"Web headers for {url}: Server banner is '{server}' (consider minimizing).")

    for url, wb_count in wayback_counts.items():
        if wb_count:
            checklist.append(f"Wayback URLs for {url}: {wb_count} samples found (review for exposed endpoints).")

    subject = ssl.get("subject")
    issuer = ssl.get("issuer")
    if subject:
        checklist.append(f"SSL subject: {subject}")
    if issuer:
        checklist.append(f"SSL issuer: {issuer}")

    return {
        "target": report.target,
        "source": str(report.path),
        "open_services": open_services,
        "subdomains": subdomains,
        "subdomain_count": len(subdomains),
        "dns_records": dns_records,
        "web": {
            "headers_by_url": headers_by_url,
            "missing_headers_by_url": missing_headers_by_url,
            "server_banners": server_banners,
            "wayback_counts": wayback_counts,
        },
        "ssl": ssl,
        "ssl_days_until_expiry": days_until_expiry,
        "checklist": checklist,
    }


def summarize(report: ReconReport) -> str:
    ports = _parse_ports(report.scan)
    dns_records = _parse_dns(report.dns)
    subdomains = _parse_subdomains(report.subdomains)
    headers_by_url = _parse_web_headers(report.web)
    wayback_counts = _parse_wayback_counts(report.web)
    ssl = _parse_ssl(report.ssl)

    lines: List[str] = []
    lines.append(f"Target: {report.target}")
    lines.append(f"Source: {report.path}")

    if ports:
        port_list = ", ".join(f"{p[0]} {p[2]}" for p in ports)
        lines.append(f"Open services: {port_list}")
    else:
        lines.append("Open services: (none detected in scan output)")

    if subdomains:
        lines.append(f"Subdomains found: {len(subdomains)}")
    else:
        lines.append("Subdomains found: none / tool missing")

    if headers_by_url:
        lines.append(f"Web endpoints with headers: {len(headers_by_url)}")
    else:
        lines.append("Web endpoints with headers: none / tool missing")

    if ssl:
        not_after = ssl.get("notAfter")
        days = _days_until(not_after) if not_after else None
        if days is not None:
            lines.append(f"SSL cert expiry: {not_after} ({days} days)")
        elif not_after:
            lines.append(f"SSL cert expiry: {not_after}")

    lines.append("\nChecklist:")

    if ports:
        lines.append("- Review exposed services and confirm they should be public:")
        for port, state, service, version in ports:
            version_str = f" ({version})" if version else ""
            lines.append(f"  - {port} {service}{version_str}")

    # DNS checks
    for label, recs in dns_records.items():
        if label in ("dig MX", "dig NS", "dig TXT") and not recs:
            lines.append(f"- DNS: {label.replace('dig ', '')} records not present in output.")

    # Web headers
    for url, headers in headers_by_url.items():
        missing = [h for h in HEADER_NAMES if h not in headers]
        if missing:
            missing_list = ", ".join(missing)
            lines.append(f"- Web headers for {url}: missing {missing_list}")

        server = headers.get("server")
        if server:
            lines.append(f"- Web headers for {url}: Server banner is '{server}' (consider minimizing).")

        wb_count = wayback_counts.get(url)
        if wb_count:
            lines.append(f"- Wayback URLs for {url}: {wb_count} samples found (review for exposed endpoints).")

    # SSL checks
    if ssl:
        subject = ssl.get("subject")
        issuer = ssl.get("issuer")
        if subject:
            lines.append(f"- SSL subject: {subject}")
        if issuer:
            lines.append(f"- SSL issuer: {issuer}")

    if not lines[-1].startswith("- ") and len(lines) > 3:
        lines.append("- (No additional checklist items detected from output.)")

    return "\n".join(lines)


def serialize_reports(reports: List[ReconReport], fmt: str, pretty: bool = False) -> str:
    fmt = fmt.lower()
    if fmt in ("text", "txt", "md"):
        chunks: List[str] = []
        for idx, report in enumerate(reports):
            if idx:
                chunks.append("\n" + "=" * 72 + "\n")
            chunks.append(summarize(report))
        return "".join(chunks)
    if fmt == "json":
        payload: Any = [summarize_structured(report) for report in reports]
        if len(reports) == 1:
            payload = payload[0]
        return json.dumps(payload, indent=2 if pretty else None)
    raise ValueError(f"Unsupported format: {fmt}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize recon.sh outputs into a checklist.")
    parser.add_argument(
        "paths",
        nargs="*",
        default=["."],
        help="Recon JSON file(s) or directories (default: .)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output file (default: stdout)",
    )
    parser.add_argument(
        "-f",
        "--format",
        default="text",
        choices=["text", "txt", "md", "json"],
        help="Output format: text, md, json (default: text)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    args = parser.parse_args()

    paths = [Path(p) for p in args.paths]
    reports = list(iter_reports(paths))
    if not reports:
        print("No recon_*.json files found.")
        return 1

    output = serialize_reports(reports, args.format, args.pretty)
    if args.output:
        Path(args.output).write_text(output)
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
