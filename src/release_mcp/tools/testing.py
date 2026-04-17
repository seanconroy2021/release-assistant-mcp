"""Testing tools for coverage and gap analysis."""


def register_testing_tools(mcp, index):
    @mcp.tool()
    def test_coverage(category: str = "managed", env: str = "") -> str:
        """Show which tasks have unit tests and how many.

        Args:
            category: 'managed', 'internal', 'collector', or 'all'.
            env: Catalog environment: 'development', 'staging', or 'production'. Empty for latest.
        """
        task_tests = {}
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
            task_tests[key] = []

        seen_tests = set()
        for key, pipeline in index.pipelines.items():
            if "test" not in pipeline.path.lower():
                continue
            if pipeline.path in seen_tests:
                continue
            seen_tests.add(pipeline.path)
            for task_key in task_tests:
                task = index.tasks[task_key]
                task_dir = task.path.rsplit("/", 1)[0]
                if pipeline.path.startswith(task_dir + "/tests/"):
                    task_tests[task_key].append(pipeline.name)

        no_tests = []
        few_tests = []
        covered = []

        for key, tests in sorted(task_tests.items()):
            url = index.url_for(index.tasks[key].repo, index.tasks[key].path)
            if not tests:
                no_tests.append(f"  {key}  {url}")
            elif len(tests) <= 2:
                few_tests.append(f"  {key}: {len(tests)} test(s)")
            else:
                covered.append(f"  {key}: {len(tests)} test(s)")

        lines = [f"Test coverage for {category} tasks:\n"]

        if no_tests:
            lines.append(f"No tests ({len(no_tests)}):")
            lines.extend(no_tests)
            lines.append("")
        if few_tests:
            lines.append(f"Low coverage, 1-2 tests ({len(few_tests)}):")
            lines.extend(few_tests)
            lines.append("")
        if covered:
            lines.append(f"Covered, 3+ tests ({len(covered)}):")
            lines.extend(covered)

        return "\n".join(lines)

    @mcp.tool()
    def show_tests(name: str, category: str = "managed", env: str = "") -> str:
        """List all unit tests for a task.

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

        task_dir = task.path.rsplit("/", 1)[0]
        tests = []
        seen_paths = set()
        for key, pipeline in sorted(index.pipelines.items()):
            if pipeline.path in seen_paths:
                continue
            if pipeline.path.startswith(task_dir + "/tests/"):
                seen_paths.add(pipeline.path)
                url = index.url_for(pipeline.repo, pipeline.path)
                task_names = [t.name for t in pipeline.task_refs]
                tests.append(f"  {pipeline.name}\n    tasks: {', '.join(task_names)}\n    {url}")

        if not tests:
            return f"No tests found for {category}/{name}."

        lines = [
            f"Tests for {category}/{name} ({len(tests)}):",
            index.url_for(task.repo, task.path),
            "",
        ]
        lines.extend(tests)
        return "\n".join(lines)

    @mcp.tool()
    def e2e_tests(env: str = "") -> str:
        """List all integration/e2e test pipelines.

        Args:
            env: Catalog environment: 'development', 'staging', or 'production'. Empty for latest.
        """
        tests = []
        seen = set()
        for key, pipeline in sorted(index.pipelines.items()):
            if env and pipeline.env != env:
                continue
            dedup_key = f"{pipeline.category}/{pipeline.name}"
            if not env and dedup_key in seen:
                continue
            seen.add(dedup_key)
            path_lower = pipeline.path.lower()
            if "integration-test" in path_lower or "e2e" in path_lower:
                url = index.url_for(pipeline.repo, pipeline.path)
                tests.append(f"  {pipeline.name} ({len(pipeline.task_refs)} tasks)\n    {url}")

        if not tests:
            return "No e2e tests found."
        return f"{len(tests)} e2e test(s):\n\n" + "\n\n".join(tests)

    @mcp.tool()
    def test_gaps(name: str, category: str = "managed", env: str = "") -> str:
        """Suggest missing test cases for a task.

        Checks for missing failure tests, untested boolean params,
        HTTP calls without network failure tests, and conditional usage.

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

        task_dir = task.path.rsplit("/", 1)[0]
        existing = set()
        seen_paths = set()
        for pipeline in index.pipeline_list:
            if pipeline.path in seen_paths:
                continue
            if pipeline.path.startswith(task_dir + "/tests/"):
                seen_paths.add(pipeline.path)
                existing.add(pipeline.name.lower())

        suggestions = []

        if not any("fail" in t for t in existing):
            suggestions.append("No failure tests. Consider testing:")
            suggestions.append("  - missing required params")
            suggestions.append("  - invalid input data")
            suggestions.append("  - missing workspace files")

        for param in task.params:
            if param.default and param.default.lower() in ("true", "false"):
                test_name = f"test-{name}-{param.name}".lower().replace("_", "-")
                if test_name not in existing:
                    suggestions.append(
                        f"Param '{param.name}' (default={param.default}) has no toggle test"
                    )

        for step in task.steps:
            if step.script:
                if "curl" in step.script or "http" in step.script.lower():
                    if not any("fail" in t and "network" in t for t in existing):
                        suggestions.append(f"Step '{step.name}' makes HTTP calls, no failure test")
                if "retry" in step.script.lower():
                    if not any("retry" in t for t in existing):
                        suggestions.append(
                            f"Step '{step.name}' has retry logic, no exhaustion test"
                        )

        for pipeline in index.pipeline_list:
            for ref in pipeline.task_refs:
                if (ref.task_ref == name or ref.name == name) and ref.has_when:
                    if not any("skip" in t or "when" in t for t in existing):
                        suggestions.append(f"Conditional in {pipeline.name}, no test for skip case")
                    break

        if not suggestions:
            return f"{category}/{name} has {len(existing)} test(s). No obvious gaps."

        url = index.url_for(task.repo, task.path)
        lines = [f"Gaps for {category}/{name} ({len(existing)} existing tests):", url, ""]
        lines.extend(f"  {s}" for s in suggestions)
        return "\n".join(lines)
