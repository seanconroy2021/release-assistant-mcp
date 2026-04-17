"""Task tools."""

SCRIPT_PREVIEW = 8


def register_task_tools(mcp, index):
    @mcp.tool()
    def show_task(name: str, category: str = "managed", env: str = "") -> str:
        """Show a task: steps, images, params, helpers, GitHub link.

        Args:
            name: Task name.
            category: 'managed', 'internal', or 'collector'.
            env: Catalog environment: 'development', 'staging', or 'production'. Empty for latest.
        """
        task = index.find_task(name, category, env)
        if not task:
            msg = f"Task '{name}' not found (category={category})."
            suggestions = index.suggest(index.task_list, name, category)
            if suggestions:
                msg += "\nDid you mean: " + ", ".join(suggestions)
            return msg

        lines = [f"{task.category}/{task.name}", index.url_for(task.repo, task.path)]

        if task.description:
            lines.append(task.description)

        if task.params:
            lines.append(f"\nParams ({len(task.params)}):")
            for p in task.params:
                default = f"={p.default}" if p.default is not None else ""
                lines.append(f"  {p.name} ({p.type}){default}")

        if task.workspaces:
            ws = ", ".join(w.name + (" (opt)" if w.optional else "") for w in task.workspaces)
            lines.append(f"\nWorkspaces: {ws}")

        if task.results:
            lines.append(f"Results: {', '.join(r.name for r in task.results)}")

        if task.steps:
            lines.append(f"\nSteps ({len(task.steps)}):")
            for step in task.steps:
                lines.append(f"  {step.name} [{step.image}]")
                if step.command:
                    lines.append(f"    cmd: {' '.join(step.command)}")
                if step.script:
                    helpers = [h for h in sorted(index.utils_helpers) if h in step.script.lower()]
                    if helpers:
                        lines.append(f"    helpers: {', '.join(helpers)}")
                    script_lines = step.script.splitlines()
                    lines.append(f"    script ({len(script_lines)} lines):")
                    for sl in script_lines[:SCRIPT_PREVIEW]:
                        lines.append(f"      {sl}")
                    if len(script_lines) > SCRIPT_PREVIEW:
                        lines.append(f"      ... +{len(script_lines) - SCRIPT_PREVIEW} more")

        return "\n".join(lines)

    @mcp.tool()
    def list_tasks(category: str = "all", env: str = "") -> str:
        """List all tasks with GitHub links.

        Args:
            category: 'managed', 'internal', 'collector', or 'all'.
            env: Catalog environment: 'development', 'staging', or 'production'. Empty for latest.
        """
        items = _dedup(index.task_list, category, env, index)
        if not items:
            return f"No tasks (category={category})"
        return _listing(items, "tasks", index)

    @mcp.tool()
    def list_pipelines(category: str = "all", env: str = "") -> str:
        """List all pipelines with GitHub links.

        Args:
            category: 'managed', 'internal', 'collector', or 'all'.
            env: Catalog environment: 'development', 'staging', or 'production'. Empty for latest.
        """
        items = _dedup(index.pipeline_list, category, env, index)
        if not items:
            return f"No pipelines (category={category})"
        return _listing(items, "pipelines", index)

    @mcp.tool()
    def search_by_image(image: str, env: str = "") -> str:
        """Find tasks using a specific container image.

        Args:
            image: Image name or fragment.
            env: Catalog environment: 'development', 'staging', or 'production'. Empty for latest.
        """
        q = image.lower()
        matches = []
        seen = set()
        for key, task in index.tasks.items():
            if env and task.env != env:
                continue
            dedup_key = f"{task.category}/{task.name}"
            if not env and dedup_key in seen:
                continue
            seen.add(dedup_key)
            for step in task.steps:
                if q in step.image.lower():
                    matches.append(
                        f"{task.category}/{task.name}/{step.name} [{step.image}]\n"
                        f"  {index.url_for(task.repo, task.path)}"
                    )
        if not matches:
            return f"No tasks use '{image}'"
        return f"{len(matches)} step(s) match '{image}':\n\n" + "\n\n".join(matches)

    @mcp.tool()
    def unused_tasks(env: str = "") -> str:
        """Find tasks not referenced by any pipeline.

        Args:
            env: Catalog environment: 'development', 'staging', or 'production'. Empty for latest.
        """
        target_env = env or (index.catalog_envs[0] if index.catalog_envs else "")

        referenced = set()
        for p in index.pipeline_list:
            if p.env == target_env:
                for t in p.task_refs + p.finally_refs:
                    referenced.add(t.task_ref or t.name)

        unused = []
        seen = set()
        for key, task in sorted(index.tasks.items()):
            if task.env != target_env:
                continue
            if task.name not in referenced and task.name not in seen:
                seen.add(task.name)
                unused.append(
                    f"  {task.category}/{task.name}  {index.url_for(task.repo, task.path)}"
                )

        if not unused:
            return "All tasks are referenced."
        return f"{len(unused)} unreferenced task(s):\n\n" + "\n".join(unused)


def _dedup(items, category, env, index):
    seen = set()
    result = []
    for item in items:
        if category != "all" and item.category != category:
            continue
        if env and item.env != env:
            continue
        dedup_key = f"{item.category}/{item.name}"
        if not env and dedup_key in seen:
            continue
        seen.add(dedup_key)
        result.append(item)
    return result


def _listing(items, label, index):
    grouped = {}
    for item in items:
        grouped.setdefault(item.category, []).append(
            f"  {item.name}  {index.url_for(item.repo, item.path)}"
        )
    lines = [f"{len(items)} {label}\n"]
    for cat in sorted(grouped):
        entries = sorted(grouped[cat])
        lines.append(f"{cat} ({len(entries)}):")
        lines.extend(entries)
        lines.append("")
    return "\n".join(lines)
