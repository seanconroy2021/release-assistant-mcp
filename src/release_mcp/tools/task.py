"""Task tools."""

SCRIPT_PREVIEW = 8


def register_task_tools(mcp, index):

    @mcp.tool()
    def show_task(name: str, category: str = "managed") -> str:
        """Show a task: steps, images, params, helpers, GitHub link.

        Args:
            name: Task name.
            category: 'managed', 'internal', or 'collector'.
        """
        task = index.find_task(name, category)
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
    def list_tasks(category: str = "all") -> str:
        """List all tasks with GitHub links.

        Args:
            category: 'managed', 'internal', 'collector', or 'all'.
        """
        items = index.task_list
        if category != "all":
            items = [t for t in items if t.category == category]
        if not items:
            return f"No tasks (category={category})"
        return _listing(items, "tasks", index)

    @mcp.tool()
    def list_pipelines(category: str = "all") -> str:
        """List all pipelines with GitHub links.

        Args:
            category: 'managed', 'internal', 'collector', or 'all'.
        """
        items = index.pipeline_list
        if category != "all":
            items = [p for p in items if p.category == category]
        if not items:
            return f"No pipelines (category={category})"
        return _listing(items, "pipelines", index)

    @mcp.tool()
    def search_by_image(image: str) -> str:
        """Find tasks using a specific container image.

        Args:
            image: Image name or fragment.
        """
        q = image.lower()
        matches = []
        for key, task in index.tasks.items():
            for step in task.steps:
                if q in step.image.lower():
                    matches.append(
                        f"{key}/{step.name} [{step.image}]\n  {index.url_for(task.repo, task.path)}"
                    )
        if not matches:
            return f"No tasks use '{image}'"
        return f"{len(matches)} step(s) match '{image}':\n\n" + "\n\n".join(matches)

    @mcp.tool()
    def unused_tasks() -> str:
        """Find tasks not referenced by any pipeline."""
        referenced = set()
        for p in index.pipeline_list:
            for t in p.task_refs + p.finally_refs:
                referenced.add(t.task_ref or t.name)

        unused = []
        for key, task in sorted(index.tasks.items()):
            if task.name not in referenced:
                unused.append(f"  {key}  {index.url_for(task.repo, task.path)}")

        if not unused:
            return "All tasks are referenced."
        return f"{len(unused)} unreferenced task(s):\n\n" + "\n".join(unused)


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
