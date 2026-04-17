"""Operational tools for debugging and inspecting catalog contents."""


def register_ops_tools(mcp, index):
    @mcp.tool()
    def timeouts(category: str = "all", env: str = "") -> str:
        """Show all pipeline tasks that have a timeout set.

        Args:
            category: 'managed', 'internal', 'collector', or 'all'.
            env: Catalog environment: 'development', 'staging', or 'production'. Empty for latest.
        """
        results = []
        seen = set()
        for key, p in sorted(index.pipelines.items()):
            if category != "all" and p.category != category:
                continue
            if env and p.env != env:
                continue
            dedup_key = f"{p.category}/{p.name}"
            if not env and dedup_key in seen:
                continue
            seen.add(dedup_key)
            for t in p.task_refs + p.finally_refs:
                if t.timeout:
                    results.append(f"  {dedup_key}/{t.name}: {t.timeout}")

        if not results:
            return "No timeouts set."
        return f"{len(results)} task(s) with timeouts:\n\n" + "\n".join(results)

    @mcp.tool()
    def resources(mode: str = "missing", env: str = "") -> str:
        """Show compute resource limits on task steps.

        Args:
            mode: 'missing' for steps without limits, 'all' to show all.
            env: Catalog environment: 'development', 'staging', or 'production'. Empty for latest.
        """
        results = []
        seen = set()
        for key, task in sorted(index.tasks.items()):
            if env and task.env != env:
                continue
            dedup_key = f"{task.category}/{task.name}"
            if not env and dedup_key in seen:
                continue
            seen.add(dedup_key)
            for step in task.steps:
                limits = step.resources.get("limits", {})
                requests = step.resources.get("requests", {})

                if mode == "missing":
                    if not limits and not requests:
                        results.append(
                            f"  {dedup_key}/{step.name} [{step.image}]\n"
                            f"    {index.url_for(task.repo, task.path)}"
                        )
                elif mode == "all":
                    cpu = limits.get("cpu", "?")
                    mem = limits.get("memory", "?")
                    results.append(f"  {dedup_key}/{step.name}: cpu={cpu} mem={mem}")

        if not results:
            if mode == "missing":
                return "All steps have resource limits set."
            return "No steps found."
        return f"{len(results)} step(s):\n\n" + "\n".join(results)

    @mcp.tool()
    def diff_envs(env_a: str = "development", env_b: str = "production") -> str:
        """Compare tasks and pipelines between catalog environments.

        Args:
            env_a: First environment.
            env_b: Second environment.
        """
        if env_a not in index.catalog_envs:
            return f"Environment '{env_a}' not loaded."
        if env_b not in index.catalog_envs:
            return f"Environment '{env_b}' not loaded."

        def _names_for_env(env_name):
            names = set()
            for v in index.tasks.values():
                if v.env == env_name:
                    names.add(f"{v.category}/{v.name}")
            for v in index.pipelines.values():
                if v.env == env_name:
                    names.add(f"{v.category}/{v.name}")
            return names

        items_a = _names_for_env(env_a)
        items_b = _names_for_env(env_b)

        only_a = sorted(items_a - items_b)
        only_b = sorted(items_b - items_a)
        shared = sorted(items_a & items_b)

        lines = [
            f"{env_a} vs {env_b}",
            f"Shared: {len(shared)}, only {env_a}: {len(only_a)}, only {env_b}: {len(only_b)}",
        ]

        if only_a:
            lines.append(f"\nOnly in {env_a} ({len(only_a)}):")
            for item in only_a:
                lines.append(f"  {item}")
        if only_b:
            lines.append(f"\nOnly in {env_b} ({len(only_b)}):")
            for item in only_b:
                lines.append(f"  {item}")

        return "\n".join(lines)

    @mcp.tool()
    def secrets(category: str = "all", env: str = "") -> str:
        """Find tasks that reference Kubernetes secrets.

        Args:
            category: 'managed', 'internal', 'collector', or 'all'.
            env: Catalog environment: 'development', 'staging', or 'production'. Empty for latest.
        """
        results = []
        seen = set()
        for key, task in sorted(index.tasks.items()):
            if category != "all" and task.category != category:
                continue
            if env and task.env != env:
                continue
            dedup_key = f"{task.category}/{task.name}"
            if not env and dedup_key in seen:
                continue
            seen.add(dedup_key)
            for step in task.steps:
                for env_name, env_val in step.env.items():
                    if "secret" in env_name.lower() or "secret" in env_val.lower():
                        results.append(f"  {dedup_key}/{step.name}: env {env_name}")
                if step.script and "secret" in step.script.lower():
                    results.append(
                        f"  {dedup_key}/{step.name}: script references secrets\n"
                        f"    {index.url_for(task.repo, task.path)}"
                    )

        if not results:
            return "No secret references found."
        return f"{len(results)} secret reference(s):\n\n" + "\n".join(results)
