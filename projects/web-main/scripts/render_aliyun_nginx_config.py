from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "deploy" / "aliyun" / "nginx.single-origin.conf"
DEFAULT_OUTPUT = ROOT / "work" / "release_evidence" / "20260620-aliyun-staging" / "nginx.single-origin.rendered.conf"


def valid_host(host: str) -> bool:
    if not host or host in {"_", "localhost", "127.0.0.1", "0.0.0.0"}:
        return False
    if "/" in host or ":" in host:
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9.-]+", host))


def host_from_url_or_name(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme and parsed.netloc:
        return parsed.hostname or ""
    return value.strip()


def render(template: Path, output: Path, server_name: str, upstream: str) -> Path:
    host = host_from_url_or_name(server_name)
    if not valid_host(host):
        raise ValueError("server name must be a real staging host, not a wildcard, localhost, IP loopback, or placeholder")
    if not upstream or re.search(r"\s", upstream):
        raise ValueError("upstream must be host:port or address:port without whitespace")

    text = template.read_text(encoding="utf-8")
    text = re.sub(r"server_name\s+_;", f"server_name {host};", text)
    text = re.sub(r"server\s+127\.0\.0\.1:8001;", f"server {upstream};", text)
    if "server_name _;" in text:
        raise ValueError("rendered config still contains wildcard server_name")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Render Aliyun single-origin Nginx config for QLanalyser staging.")
    parser.add_argument("--server-name", required=True, help="Staging host or public base URL, for example qlanalyser-staging.example.com")
    parser.add_argument("--upstream", default="127.0.0.1:8001", help="Backend upstream address visible from Nginx")
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    path = render(args.template, args.output, args.server_name, args.upstream)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
