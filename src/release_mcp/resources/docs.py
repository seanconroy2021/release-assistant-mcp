"""MCP resources."""

import json


def register_resources(mcp, index):

    @mcp.resource("schema://dataKeys")
    def data_keys_schema():
        """The dataKeys.json schema."""
        if index.schema is None:
            return "Schema not loaded."
        return json.dumps(index.schema, indent=2)

    @mcp.resource("docs://catalog-structure")
    def catalog_structure():
        """Catalog repo structure."""
        lines = []
        for env in index.catalog_envs or [""]:
            dir_name = index.catalog_dir(env) if env else index.config.catalog.repo
            catalog_path = index.data_dir / dir_name
            if not catalog_path.exists():
                continue
            if env:
                lines.append(f"--- {env} ---")
            for d in sorted(catalog_path.iterdir()):
                if not d.is_dir() or d.name.startswith("."):
                    continue
                lines.append(f"{d.name}/")
                for sub in sorted(d.iterdir()):
                    if sub.is_dir():
                        count = sum(1 for _ in sub.rglob("*.yaml"))
                        count += sum(1 for _ in sub.rglob("*.yml"))
                        lines.append(f"  {sub.name}/ ({count} yaml)")
                    else:
                        lines.append(f"  {sub.name}")
            lines.append("")
        return "\n".join(lines) if lines else "Catalog not found."

    @mcp.resource("docs://index-summary")
    def index_summary():
        """Index summary."""
        lines = [f"{len(index.pipelines)} pipelines, {len(index.tasks)} tasks", ""]

        for label, items in [("Pipelines", index.pipeline_list), ("Tasks", index.task_list)]:
            cats = {}
            for x in items:
                cats[x.category] = cats.get(x.category, 0) + 1
            if cats:
                lines.append(f"{label}:")
                for cat, count in sorted(cats.items()):
                    lines.append(f"  {cat}: {count}")

        if index.catalog_envs:
            lines.append(f"\nEnvironments: {', '.join(index.catalog_envs)}")

        return "\n".join(lines)
