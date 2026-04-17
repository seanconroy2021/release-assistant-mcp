"""Search tools."""

import re

MAX_RESULTS = 25
MAX_CODE_RESULTS = 15


def register_search_tools(mcp, index):
    @mcp.tool()
    def search(query: str, kind: str = "all", category: str = "all", env: str = "") -> str:
        """Search pipelines and tasks by name or description.

        Args:
            query: Search term.
            kind: 'task', 'pipeline', or 'all'.
            category: 'managed', 'internal', 'collector', or 'all'.
            env: Catalog environment: 'development', 'staging', or 'production'. Empty for latest.
        """
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        results = []
        seen = set()

        if kind in ("all", "pipeline"):
            for key, p in index.pipelines.items():
                if category != "all" and p.category != category:
                    continue
                if env and p.env != env:
                    continue
                dedup_key = f"pipeline/{p.category}/{p.name}"
                if not env and dedup_key in seen:
                    continue
                seen.add(dedup_key)
                if pattern.search(p.name) or pattern.search(p.description):
                    display = f"{p.category}/{p.name}"
                    tasks = ", ".join(t.name for t in p.task_refs[:5])
                    if len(p.task_refs) > 5:
                        tasks += f" (+{len(p.task_refs) - 5})"
                    results.append(
                        f"[pipeline] {display} | {tasks}\n  {index.url_for(p.repo, p.path)}"
                    )

        if kind in ("all", "task"):
            for key, t in index.tasks.items():
                if category != "all" and t.category != category:
                    continue
                if env and t.env != env:
                    continue
                dedup_key = f"task/{t.category}/{t.name}"
                if not env and dedup_key in seen:
                    continue
                seen.add(dedup_key)
                if pattern.search(t.name) or pattern.search(t.description):
                    display = f"{t.category}/{t.name}"
                    steps = ", ".join(s.name for s in t.steps)
                    results.append(f"[task] {display} | {steps}\n  {index.url_for(t.repo, t.path)}")

        if not results:
            return f"No results for '{query}'"
        return f"{len(results)} result(s):\n\n" + "\n\n".join(results[:MAX_RESULTS])

    @mcp.tool()
    def grep(query: str, repo: str = "all", file_pattern: str = "") -> str:
        """Search file contents across repos. Returns GitHub links with line numbers.

        Args:
            query: Text or regex pattern.
            repo: Repo name or 'all'.
            file_pattern: Filter like '*.go' or '*.yaml'.
        """
        try:
            pattern = re.compile(query, re.IGNORECASE)
        except re.error:
            return f"Invalid regex: '{query}'"

        repos = [repo] if repo != "all" else index.searchable_repos
        matches = []

        for repo_name in repos:
            for fp in index.walk_files(repo_name, file_pattern):
                try:
                    text = fp.read_text(errors="replace")
                except OSError:
                    continue

                rel = str(fp.relative_to(index.data_dir / repo_name))
                for i, line in enumerate(text.splitlines(), 1):
                    if pattern.search(line):
                        url = index.url_for(repo_name, rel, line=i)
                        matches.append(f"{url}\n  {line.strip()[:150]}")
                        if len(matches) >= MAX_CODE_RESULTS:
                            break
                if len(matches) >= MAX_CODE_RESULTS:
                    break
            if len(matches) >= MAX_CODE_RESULTS:
                break

        if not matches:
            return f"No matches for '{query}'"

        header = f"{len(matches)} match(es)"
        if len(matches) == MAX_CODE_RESULTS:
            header += " (limit reached)"
        return header + ":\n\n" + "\n\n".join(matches)
