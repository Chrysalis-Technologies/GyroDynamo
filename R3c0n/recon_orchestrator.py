#!/usr/bin/env python3
"""
Run recon.sh (all modules) then summarize its output with recon_step2.py.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import shutil
from pathlib import Path


def _safe_stem(target: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", target.strip())
    return cleaned or "target"


def _to_msys_path(path: Path) -> str:
    posix = path.as_posix()
    if os.name != "nt":
        return posix
    if len(posix) > 1 and posix[1] == ":":
        drive = posix[0].lower()
        return f"/{drive}{posix[2:]}"
    return posix


def _summary_ext(fmt: str) -> str:
    fmt = fmt.lower()
    if fmt in ("text", "txt"):
        return "txt"
    if fmt == "md":
        return "md"
    if fmt == "json":
        return "json"
    return "txt"


def _parse_txt_report(path: Path) -> dict:
    text = path.read_text(errors="ignore")
    target = ""
    header_match = re.search(r"^Reconnaissance Report for\\s+(.+)$", text, re.MULTILINE)
    if header_match:
        target = header_match.group(1).strip()

    sections = {"Scan": "", "DNS": "", "Subdomains": "", "Web": "", "SSL": ""}
    current = None
    for line in text.splitlines():
        m = re.match(r"^===\\s*(\\w+)\\s*===$", line.strip())
        if m and m.group(1) in sections:
            current = m.group(1)
            continue
        if current:
            sections[current] += line + "\n"

    return {
        "target": target,
        "scan": sections["Scan"].strip(),
        "dns": sections["DNS"].strip(),
        "subdomains": sections["Subdomains"].strip(),
        "web": sections["Web"].strip(),
        "ssl": sections["SSL"].strip(),
    }


def _run_recon_direct(target: str, json_out: Path, txt_out: Path) -> dict:
    recon_dir = Path(__file__).resolve().parent
    tmp_dir = Path(os.environ.get("TEMP", os.environ.get("TMP", ""))) or recon_dir
    scan_file = tmp_dir / f"recon_scan_{_safe_stem(target)}.txt"
    dns_file = tmp_dir / f"recon_dns_{_safe_stem(target)}.txt"
    sub_file = tmp_dir / f"recon_sub_{_safe_stem(target)}.txt"
    web_file = tmp_dir / f"recon_web_{_safe_stem(target)}.txt"
    ssl_file = tmp_dir / f"recon_ssl_{_safe_stem(target)}.txt"

    def run_cmd(cmd, outfile: Path):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            content = result.stdout if result.stdout else result.stderr
        except FileNotFoundError:
            content = f"{cmd[0]} not installed"
        outfile.write_text(content)

    # Port scan
    if shutil.which("nmap"):
        run_cmd(["nmap", "-T4", "-F", "-sV", target], scan_file)
    elif shutil.which("masscan"):
        run_cmd(["masscan", "-p1-65535", target, "--rate=1000"], scan_file)
    else:
        scan_file.write_text("nmap/masscan not installed")

    # DNS
    dns_lines = []
    def dig(label, *args):
        if shutil.which("dig"):
            run_cmd(["dig", "+noall", "+answer", *args], dns_file)
            return dns_file.read_text()
        return "dig not installed\n"

    dns_lines.append("# dig A\n" + dig("A", target))
    dns_lines.append("# dig MX\n" + dig("MX", "MX", target))
    dns_lines.append("# dig NS\n" + dig("NS", "NS", target))
    dns_lines.append("# dig TXT\n" + dig("TXT", "TXT", target))
    dns_lines.append("# Reverse PTR\n" + (dig("-x", "-x", target) if shutil.which("dig") else "dig not installed\n"))
    if shutil.which("whois"):
        run_cmd(["whois", target], dns_file)
        whois_out = "\n".join(dns_file.read_text().splitlines()[:100])
    else:
        whois_out = "whois not installed"
    dns_lines.append("# whois\n" + whois_out + "\n")
    dns_file.write_text("\n".join(dns_lines))

    # Subdomains
    if shutil.which("subfinder"):
        run_cmd(["subfinder", "-silent", "-d", target], sub_file)
    elif shutil.which("amass"):
        run_cmd(["amass", "enum", "-d", target], sub_file)
    else:
        sub_file.write_text("subfinder/amass not installed")

    # Web
    web_lines = []
    urls = [f"http://{target}", f"https://{target}"]
    for url in urls:
        if not shutil.which("curl"):
            web_lines.append("curl not installed")
            break
        web_lines.append(f"# Headers for {url}")
        run_cmd(["curl", "-I", "-s", url], web_file)
        web_lines.append(web_file.read_text())
        web_lines.append("")
        web_lines.append(f"# Wayback URLs for {url}")
        if shutil.which("waybackurls"):
            try:
                proc = subprocess.run(
                    ["waybackurls"],
                    input=url,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                web_lines.append(proc.stdout if proc.stdout else proc.stderr)
            except FileNotFoundError:
                web_lines.append("waybackurls not installed")
        else:
            web_lines.append("waybackurls not installed")
        web_lines.append("")
    web_file.write_text("\n".join(web_lines))

    # SSL
    if shutil.which("openssl"):
        s_client = subprocess.run(
            ["openssl", "s_client", "-connect", f"{target}:443", "-servername", target],
            input="",
            text=True,
            capture_output=True,
            check=False,
        )
        x509 = subprocess.run(
            ["openssl", "x509", "-noout", "-issuer", "-subject", "-dates"],
            input=s_client.stdout,
            text=True,
            capture_output=True,
            check=False,
        )
        ssl_file.write_text(x509.stdout if x509.stdout else x509.stderr)
    else:
        ssl_file.write_text("openssl not installed")

    # Compose txt output similar to recon.sh
    txt_lines = [
        f"Reconnaissance Report for {target}",
        "=== Scan ===",
        scan_file.read_text(),
        "=== DNS ===",
        dns_file.read_text(),
        "=== Subdomains ===",
        sub_file.read_text(),
        "=== Web ===",
        web_file.read_text(),
        "=== SSL ===",
        ssl_file.read_text(),
    ]
    txt_out.write_text("\n".join(txt_lines))

    return _parse_txt_report(txt_out)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run recon.sh then summarize with recon_step2.py."
    )
    parser.add_argument("target", help="IP or domain to scan")
    parser.add_argument(
        "-o",
        "--output",
        help="Output JSON path (default: R3c0n/recon_<target>.json)",
    )
    parser.add_argument(
        "--summary",
        help="Summary output path (default: R3c0n/recon_<target>_summary.<ext>)",
    )
    parser.add_argument(
        "--summary-format",
        default="text",
        choices=["text", "txt", "md", "json"],
        help="recon_step2 output format (default: text)",
    )
    parser.add_argument(
        "--summary-pretty",
        action="store_true",
        help="Pretty-print JSON summary output",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    step2 = script_dir / "recon_step2.py"
    if not step2.exists():
        print(f"Missing step2 script: {step2}", file=sys.stderr)
        return 1

    output_path = Path(args.output) if args.output else script_dir / f"recon_{_safe_stem(args.target)}.json"
    summary_path = (
        Path(args.summary)
        if args.summary
        else script_dir
        / f"recon_{_safe_stem(args.target)}_summary.{_summary_ext(args.summary_format)}"
    )

    txt_output = output_path.with_suffix(".txt")
    data = _run_recon_direct(args.target, output_path, txt_output)
    output_path.write_text(json.dumps(data, indent=2))

    sys.path.insert(0, str(script_dir))
    import recon_step2  # type: ignore

    report = recon_step2.load_report(output_path)
    summary = recon_step2.serialize_reports(
        [report],
        args.summary_format,
        args.summary_pretty,
    )
    summary_path.write_text(summary)
    emit_stdout = args.summary is None and args.summary_format in ("text", "txt", "md")
    if emit_stdout:
        print("\n[recon_step2] Summary:\n")
        print(summary)
    print(f"\n[recon_step2] Summary written to: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
