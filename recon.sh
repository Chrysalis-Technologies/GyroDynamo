#!/bin/bash
# Reconnaissance utility for surface level information gathering

set -euo pipefail

OUTPUT_FILE="recon_output.json"
VERBOSE=false
FORMAT="json"

usage() {
  cat <<USAGE
Usage: $(basename "$0") [command] [options]
Commands:
  scan <target>       Scan open ports and services
  dns <target>        Retrieve DNS records
  subdomain <target>  Discover subdomains
  web <target>        Analyze web server info
  ssl <target>        Retrieve SSL/TLS certificate info
  all <target>        Run all modules
  help                Show this help
Options:
  -o <file>           Output file (default: recon_output.json)
  -v                  Verbose mode
  -f <format>         Output format: json, md, txt (default: json)
USAGE
}

log() { [ "$VERBOSE" = true ] && echo "$1" >&2; }

command_exists() { command -v "$1" >/dev/null 2>&1; }

# temp files for module outputs
tmp_dir=$(mktemp -d)
SCAN_FILE="$tmp_dir/scan.txt"; : > "$SCAN_FILE"
DNS_FILE="$tmp_dir/dns.txt"; : > "$DNS_FILE"
SUB_FILE="$tmp_dir/subdomain.txt"; : > "$SUB_FILE"
WEB_FILE="$tmp_dir/web.txt"; : > "$WEB_FILE"
SSL_FILE="$tmp_dir/ssl.txt"; : > "$SSL_FILE"

scan_ports() {
  local target=$1
  log "Scanning ports on $target"
  if command_exists nmap; then
    nmap -T4 -F -sV "$target" > "$SCAN_FILE" 2>&1 || echo "nmap scan failed" > "$SCAN_FILE"
  elif command_exists masscan; then
    masscan -p1-65535 "$target" --rate=1000 > "$SCAN_FILE" 2>&1 || echo "masscan scan failed" > "$SCAN_FILE"
  else
    echo "nmap/masscan not installed" > "$SCAN_FILE"
  fi
}

gather_dns() {
  local target=$1
  log "Gathering DNS information for $target"
  {
    echo "# dig A"
    if command_exists dig; then dig +noall +answer "$target"; else echo "dig not installed"; fi
    echo
    echo "# dig MX"
    if command_exists dig; then dig +noall +answer MX "$target"; fi
    echo
    echo "# dig NS"
    if command_exists dig; then dig +noall +answer NS "$target"; fi
    echo
    echo "# dig TXT"
    if command_exists dig; then dig +noall +answer TXT "$target"; fi
    echo
    echo "# Reverse PTR"
    if command_exists dig; then dig +noall +answer -x "$target"; fi
    echo
    echo "# whois"
    if command_exists whois; then (whois "$target" | head -n 100) || true; else echo "whois not installed"; fi
  } > "$DNS_FILE" 2>&1
}

discover_subdomains() {
  local target=$1
  log "Discovering subdomains for $target"
  if command_exists subfinder; then
    subfinder -silent -d "$target" > "$SUB_FILE" 2>&1 || echo "subfinder failed" > "$SUB_FILE"
  elif command_exists amass; then
    amass enum -d "$target" > "$SUB_FILE" 2>&1 || echo "amass failed" > "$SUB_FILE"
  else
    echo "subfinder/amass not installed" > "$SUB_FILE"
  fi
}

analyze_web_server() {
  local target=$1
  log "Analyzing web server for $target"
  {
    local urls="http://$target https://$target"
    for u in $urls; do
      if command_exists httprobe; then
        echo "$u" | httprobe 2>/dev/null | while read -r live; do
          echo "# Headers for $live"
          curl -I -s "$live"
          echo
          echo "# Wayback URLs for $live"
          if command_exists waybackurls; then
            echo "$live" | waybackurls | head -n 20
          else
            echo "waybackurls not installed"
          fi
        done
      else
        echo "httprobe not installed"
      fi
    done
  } > "$WEB_FILE" 2>&1
}

gather_ssl() {
  local target=$1
  log "Gathering SSL/TLS info for $target"
  if command_exists openssl; then
    echo | openssl s_client -connect "$target:443" -servername "$target" 2>/dev/null | openssl x509 -noout -issuer -subject -dates > "$SSL_FILE" 2>&1 || echo "SSL fetch failed" > "$SSL_FILE"
  else
    echo "openssl not installed" > "$SSL_FILE"
  fi
}

write_output() {
  case "$FORMAT" in
    json)
      python3 - <<PY
import json, pathlib
out = {
  "target": "$target",
  "scan": pathlib.Path("$SCAN_FILE").read_text(),
  "dns": pathlib.Path("$DNS_FILE").read_text(),
  "subdomains": pathlib.Path("$SUB_FILE").read_text(),
  "web": pathlib.Path("$WEB_FILE").read_text(),
  "ssl": pathlib.Path("$SSL_FILE").read_text(),
}
pathlib.Path("$OUTPUT_FILE").write_text(json.dumps(out, indent=2))
PY
      ;;
    md)
      {
        echo "# Reconnaissance Report for $target"
        echo "## Scan"
        cat "$SCAN_FILE"
        echo "## DNS"
        cat "$DNS_FILE"
        echo "## Subdomains"
        cat "$SUB_FILE"
        echo "## Web"
        cat "$WEB_FILE"
        echo "## SSL"
        cat "$SSL_FILE"
      } > "$OUTPUT_FILE"
      ;;
    txt|text)
      {
        echo "Reconnaissance Report for $target"
        echo "=== Scan ==="
        cat "$SCAN_FILE"
        echo "=== DNS ==="
        cat "$DNS_FILE"
        echo "=== Subdomains ==="
        cat "$SUB_FILE"
        echo "=== Web ==="
        cat "$WEB_FILE"
        echo "=== SSL ==="
        cat "$SSL_FILE"
      } > "$OUTPUT_FILE"
      ;;
    *)
      echo "Unknown format: $FORMAT" >&2
      exit 1
      ;;
  esac
  echo "Output written to $OUTPUT_FILE"
}

if [ $# -lt 1 ]; then
  usage; exit 1
fi

cmd="$1"; shift

# parse options after command
while getopts ":o:vf:" opt; do
  case $opt in
    o) OUTPUT_FILE="$OPTARG";;
    v) VERBOSE=true;;
    f) FORMAT="$OPTARG";;
    \?) echo "Invalid option: -$OPTARG" >&2; usage; exit 1;;
    :) echo "Option -$OPTARG requires an argument" >&2; usage; exit 1;;
  esac
done
shift $((OPTIND-1))

target="${1:-}"

case "$cmd" in
  scan)
    [ -z "$target" ] && { echo "scan requires target" >&2; exit 1; }
    scan_ports "$target"
    ;;
  dns)
    [ -z "$target" ] && { echo "dns requires target" >&2; exit 1; }
    gather_dns "$target"
    ;;
  subdomain)
    [ -z "$target" ] && { echo "subdomain requires target" >&2; exit 1; }
    discover_subdomains "$target"
    ;;
  web)
    [ -z "$target" ] && { echo "web requires target" >&2; exit 1; }
    analyze_web_server "$target"
    ;;
  ssl)
    [ -z "$target" ] && { echo "ssl requires target" >&2; exit 1; }
    gather_ssl "$target"
    ;;
  all)
    [ -z "$target" ] && { echo "all requires target" >&2; exit 1; }
    scan_ports "$target"
    gather_dns "$target"
    discover_subdomains "$target"
    analyze_web_server "$target"
    gather_ssl "$target"
    ;;
  help)
    usage
    exit 0
    ;;
  *)
    echo "Unknown command: $cmd" >&2
    usage
    exit 1
    ;;
esac

write_output
