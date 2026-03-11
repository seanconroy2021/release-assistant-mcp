#!/usr/bin/env python3
"""Crawls documentation websites at build time and caches them as plain text.

Reads doc URLs from config.yaml. No external dependencies beyond pyyaml.
"""

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

USER_AGENT = "release-mcp-crawler/1.0 (build-time docs caching)"

CONFIG_SEARCH_PATHS = [
    Path("/app/config.yaml"),
    Path(__file__).resolve().parent.parent / "config.yaml",
]

_DEFAULT_DOCS = {
    "releasing": "https://konflux-ci.dev/docs/releasing/",
    "release-service-architecture": ("https://konflux-ci.dev/architecture/core/release-service/"),
    "internal-services-architecture": (
        "https://konflux-ci.dev/architecture/add-ons/internal-services/"
    ),
    "tekton-pipelines": "https://tekton.dev/docs/pipelines/pipelines/",
    "tekton-tasks": "https://tekton.dev/docs/pipelines/tasks/",
}


def load_docs_config() -> dict[str, str]:
    """Load doc pages from config.yaml, falling back to defaults."""
    try:
        import yaml
    except ImportError:
        return _DEFAULT_DOCS

    for path in CONFIG_SEARCH_PATHS:
        if path.exists():
            raw = yaml.safe_load(path.read_text())
            if isinstance(raw, dict) and "docs" in raw:
                return {d["name"]: d["url"] for d in raw["docs"]}

    return _DEFAULT_DOCS


class HTMLToText(HTMLParser):
    """Strips HTML tags and extracts readable text content."""

    def __init__(self):
        super().__init__()
        self._text: list[str] = []
        self._skip = False
        self._skip_tags = {"script", "style", "nav", "footer", "header"}

    def handle_starttag(self, tag, attrs):
        if tag in self._skip_tags:
            self._skip = True
        if tag in ("p", "br", "div", "h1", "h2", "h3", "h4", "li", "tr"):
            self._text.append("\n")

    def handle_endtag(self, tag):
        if tag in self._skip_tags:
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            self._text.append(data)

    def get_text(self) -> str:
        raw = "".join(self._text)
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in raw.splitlines()]
        result: list[str] = []
        blank_count = 0
        for line in lines:
            if not line:
                blank_count += 1
                if blank_count <= 2:
                    result.append("")
            else:
                blank_count = 0
                result.append(line)
        return "\n".join(result).strip()


def fetch_page(url: str) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=30) as resp:  # noqa: S310
        return resp.read().decode("utf-8", errors="replace")


def html_to_text(html: str) -> str:
    parser = HTMLToText()
    parser.feed(html)
    return parser.get_text()


def main():
    output_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/data/docs")
    output_dir.mkdir(parents=True, exist_ok=True)

    docs_pages = load_docs_config()
    manifest: dict[str, dict] = {}

    for name, url in docs_pages.items():
        print(f"Crawling {name}: {url}")
        try:
            html = fetch_page(url)
            text = html_to_text(html)

            doc_path = output_dir / f"{name}.txt"
            doc_path.write_text(text)

            manifest[name] = {"url": url, "file": f"{name}.txt", "size": len(text)}
            print(f"  Saved {len(text)} chars")
        except Exception as exc:
            print(f"  Failed: {exc}", file=sys.stderr)
            manifest[name] = {"url": url, "error": str(exc)}

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\nManifest written to {manifest_path}")


if __name__ == "__main__":
    main()
