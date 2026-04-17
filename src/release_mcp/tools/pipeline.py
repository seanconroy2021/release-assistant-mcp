"""Pipeline tools."""


def register_pipeline_tools(mcp, index):
    @mcp.tool()
    def show_pipeline(name: str, category: str = "managed", env: str = "") -> str:
        """Show a pipeline: task DAG, params, workspaces.

        Args:
            name: Pipeline name.
            category: 'managed', 'internal', or 'collector'.
            env: Catalog environment: 'development', 'staging', or 'production'. Empty for latest.
        """
        p = index.find_pipeline(name, category, env)
        if not p:
            return _not_found(index, name, category)

        lines = [f"{p.category}/{p.name}", index.url_for(p.repo, p.path)]
        if p.description:
            lines.append(p.description)

        if p.params:
            lines.append(f"\nParams ({len(p.params)}):")
            for param in p.params:
                default = f"={param.default}" if param.default is not None else ""
                lines.append(f"  {param.name} ({param.type}){default}")

        if p.workspaces:
            ws = ", ".join(w.name + (" (opt)" if w.optional else "") for w in p.workspaces)
            lines.append(f"\nWorkspaces: {ws}")

        lines.append(f"\nDAG ({len(p.task_refs)} tasks):")
        lines.append(_render_dag(p))

        if p.finally_refs:
            names = [f"{t.name}:{t.task_ref}" if t.task_ref else t.name for t in p.finally_refs]
            lines.append(f"\nFinally: {', '.join(names)}")

        return "\n".join(lines)

    @mcp.tool()
    def trace_pipeline(name: str, env: str = "") -> str:
        """Trace a managed pipeline through tasks and internal service calls.

        Args:
            name: Managed pipeline name.
            env: Catalog environment: 'development', 'staging', or 'production'. Empty for latest.
        """
        p = index.find_pipeline(name, "managed", env)
        if not p:
            return _not_found(index, name, "managed")

        lines = [f"Flow: {p.name}", index.url_for(p.repo, p.path), "=" * 50]

        for ref in p.task_refs:
            ref_name = ref.task_ref or ref.name
            after = f" (after: {', '.join(ref.run_after)})" if ref.run_after else ""
            lines.append(f"\n  {ref.name}{after}")

            task = index.find_task(ref_name, "managed", env)
            if task:
                lines.append(f"    {index.url_for(task.repo, task.path)}")
                for step in task.steps:
                    lines.append(f"    step: {step.name} [{step.image}]")
                    if step.script:
                        for call in _internal_calls(step.script, index.internal_markers):
                            lines.append(f"      INTERNAL: {call}")

        if p.finally_refs:
            lines.append("\n  [finally]")
            for t in p.finally_refs:
                lines.append(f"    {t.name}: {t.task_ref or '?'}")

        return "\n".join(lines)

    @mcp.tool()
    def diff_pipelines(name_a: str, name_b: str, category: str = "managed", env: str = "") -> str:
        """Compare two pipelines: shared tasks, unique tasks, param diffs.

        Args:
            name_a: First pipeline.
            name_b: Second pipeline.
            category: Category for both.
            env: Catalog environment: 'development', 'staging', or 'production'. Empty for latest.
        """
        a = index.find_pipeline(name_a, category, env)
        b = index.find_pipeline(name_b, category, env)
        if not a:
            return _not_found(index, name_a, category)
        if not b:
            return _not_found(index, name_b, category)

        refs_a = {(t.task_ref or t.name) for t in a.task_refs}
        refs_b = {(t.task_ref or t.name) for t in b.task_refs}

        lines = [
            f"{a.name} vs {b.name} ({category})",
            f"Tasks: {len(a.task_refs)} vs {len(b.task_refs)}",
            f"Params: {len(a.params)} vs {len(b.params)}",
        ]

        shared = sorted(refs_a & refs_b)
        only_a = sorted(refs_a - refs_b)
        only_b = sorted(refs_b - refs_a)

        if shared:
            lines.append(f"\nShared ({len(shared)}): {', '.join(shared)}")
        if only_a:
            lines.append(f"\nOnly in {a.name}: {', '.join(only_a)}")
        if only_b:
            lines.append(f"\nOnly in {b.name}: {', '.join(only_b)}")

        params_a = {p.name for p in a.params} - {p.name for p in b.params}
        params_b = {p.name for p in b.params} - {p.name for p in a.params}
        if params_a:
            lines.append(f"\nParams only in {a.name}: {', '.join(sorted(params_a))}")
        if params_b:
            lines.append(f"\nParams only in {b.name}: {', '.join(sorted(params_b))}")

        return "\n".join(lines)


def _not_found(index, name, category):
    msg = f"Pipeline '{name}' not found (category={category})."
    suggestions = index.suggest(index.pipeline_list, name, category)
    if suggestions:
        msg += "\nDid you mean: " + ", ".join(suggestions)
    return msg


def _render_dag(pipeline):
    lines = []
    by_name = {t.name: t for t in pipeline.task_refs}
    visited = set()

    def walk(name, depth):
        if name in visited:
            return
        visited.add(name)
        t = by_name.get(name)
        if not t:
            return
        ref = f" -> {t.task_ref}" if t.task_ref else ""
        cond = " [when]" if t.has_when else ""
        lines.append(f"{'  ' * depth}|- {t.name}{ref}{cond}")
        for child in pipeline.task_refs:
            if name in child.run_after:
                walk(child.name, depth + 1)

    for root in pipeline.task_refs:
        if not root.run_after:
            walk(root.name, 1)
    for t in pipeline.task_refs:
        if t.name not in visited:
            walk(t.name, 1)

    return "\n".join(lines)


def _internal_calls(script, markers):
    calls = []
    for line in script.splitlines():
        stripped = line.strip()
        if any(m in stripped for m in markers):
            calls.append(stripped[:150])
    return calls
