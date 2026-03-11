"""Docs tools."""

import json
import re

MAX_RESULTS = 15
CONTEXT_LINES = 2


def register_docs_tools(mcp, index):

    docs_dir = index.data_dir / "docs"
    manifest = _load_manifest(docs_dir)

    @mcp.tool()
    def docs(query: str, doc: str = "all") -> str:
        """Search cached Release Service and Tekton documentation.

        Args:
            query: Text or regex to search for.
            doc: Doc name or 'all'.
        """
        if not docs_dir.exists():
            return "No docs cached."

        pattern = re.compile(query, re.IGNORECASE)
        matches = []

        for doc_name in [doc] if doc != "all" else list(manifest):
            info = manifest.get(doc_name)
            if not info or "error" in info:
                continue

            doc_path = docs_dir / info["file"]
            if not doc_path.exists():
                continue

            try:
                lines = doc_path.read_text().splitlines()
            except OSError:
                continue

            url = info["url"]
            for i, line in enumerate(lines):
                if pattern.search(line):
                    start = max(0, i - CONTEXT_LINES)
                    end = min(len(lines), i + CONTEXT_LINES + 1)
                    context = "\n".join(
                        f"  {'>' if j == i else ' '} {lines[j]}" for j in range(start, end)
                    )
                    matches.append(f"[{doc_name}] line {i + 1} ({url})\n{context}")
                    if len(matches) >= MAX_RESULTS:
                        break
            if len(matches) >= MAX_RESULTS:
                break

        if not matches:
            return f"No matches for '{query}'"

        header = f"{len(matches)} match(es)"
        if len(matches) == MAX_RESULTS:
            header += " (limit reached)"
        return header + ":\n\n" + "\n\n".join(matches)

    @mcp.tool()
    def list_docs() -> str:
        """List cached documentation pages."""
        if not manifest:
            return "No docs cached."

        lines = [f"{len(manifest)} cached doc(s):\n"]
        for name, info in manifest.items():
            if "error" in info:
                lines.append(f"  {name}: FAILED ({info['error']})")
            else:
                lines.append(f"  {name} ({info.get('size', 0) / 1024:.1f}KB)")
                lines.append(f"    {info['url']}")
        return "\n".join(lines)


def _load_manifest(docs_dir):
    path = docs_dir / "manifest.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}
