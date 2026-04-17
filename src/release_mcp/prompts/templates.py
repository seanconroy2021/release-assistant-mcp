"""Prompt templates for common release service workflows."""


def register_prompts(mcp):
    @mcp.prompt()
    def troubleshoot(pipeline_name: str = "", error_message: str = "", step_name: str = ""):
        """Troubleshoot a failed release pipeline run."""
        parts = [
            "A release pipeline has failed. Walk through the problem step by step.",
            "",
            "First: ask which environment the failure is in (development, staging,",
            "or production) and pass env= to all tool calls so you're looking at",
            "the right version of each task and pipeline.",
            "",
            "1. Run show_pipeline to see the full DAG and identify where the failure sits",
            "2. Run show_task on the failing task to see its steps, params, and script",
            "3. Run grep to search for the error message across all repos",
            "4. Run trace_pipeline to check if internal service calls are involved",
            "5. If the error mentions data keys, run schema to check the expected format",
            "6. If the task exists in dev but not prod, check diff_envs for promotion status",
            "",
            "Focus on the root cause. Check if the issue is in the task script,",
            "a missing param, a wrong image version, or an internal service failure.",
            "",
        ]
        if pipeline_name:
            parts.append(f"Pipeline: {pipeline_name}")
        if step_name:
            parts.append(f"Failed step: {step_name}")
        if error_message:
            parts.append(f"Error: {error_message}")
        if not any([pipeline_name, step_name, error_message]):
            parts.append("Ask for: pipeline name, failing step, error message, and environment.")
        return "\n".join(parts)

    @mcp.prompt()
    def investigate_timeout(pipeline_name: str = "", step_name: str = ""):
        """Investigate a timeout or slow task in a pipeline run."""
        parts = [
            "A pipeline task is timing out or running too long.",
            "",
            "1. Run timeouts to see what timeout values are configured",
            "2. Run show_pipeline to see the DAG and find the critical path",
            "3. Run show_task on the slow task to check the script for:",
            "   - retry loops that could be retrying too many times",
            "   - external HTTP calls that could be hanging",
            "   - large data processing without streaming",
            "4. Run resources to check if CPU or memory limits are too low",
            "   (OOM kills look like timeouts)",
            "5. Check if the timeout value itself needs increasing",
            "",
        ]
        if pipeline_name:
            parts.append(f"Pipeline: {pipeline_name}")
        if step_name:
            parts.append(f"Slow step: {step_name}")
        return "\n".join(parts)

    @mcp.prompt()
    def review_tests(task_name: str = "", category: str = "managed", env: str = "development"):
        """Review test coverage and find gaps for a task or the whole catalog."""
        if task_name:
            return "\n".join(
                [
                    f"Review test coverage for the {task_name} task in {env}.",
                    "",
                    f"1. Run show_tests(name='{task_name}', env='{env}') to see existing tests",
                    f"2. Run test_gaps(name='{task_name}', env='{env}') to find what's missing",
                    f"3. Run show_task(name='{task_name}', env='{env}') to understand"
                    " the task logic",
                    "4. For each gap found, describe what the test should verify",
                    "   and what mock data it would need",
                ]
            )
        return "\n".join(
            [
                f"Review test coverage across {category} tasks in {env}.",
                "",
                f"1. Run test_coverage(category='{category}', env='{env}') for the overview",
                "2. Start with tasks that have zero tests",
                "3. Run test_gaps on each to understand what's missing",
                "4. Run e2e_tests to check integration coverage",
                "5. Prioritize tasks that handle signing, pushing, or advisory creation",
            ]
        )

    @mcp.prompt()
    def compare_environments(env_a: str = "development", env_b: str = "production"):
        """Compare what changed between catalog environments."""
        return "\n".join(
            [
                f"Compare the {env_a} and {env_b} catalog environments.",
                "",
                f"1. Run diff_envs(env_a='{env_a}', env_b='{env_b}') to see the differences",
                f"2. For items only in {env_a}, run show_task or show_pipeline with env='{env_a}'",
                f"3. For shared pipelines, compare them with env='{env_a}' then env='{env_b}'",
                "   to see if the task count or params differ between environments",
                "4. Flag anything in development that looks ready for promotion",
            ]
        )

    @mcp.prompt()
    def understand_pipeline(name: str = "", env: str = "development"):
        """Understand how a release pipeline works end to end."""
        parts = [
            f"Walk through a release pipeline from start to finish (using {env} catalog).",
            "",
            f"1. Run show_pipeline with env='{env}' to see the DAG, params, and workspaces",
            f"2. Run trace_pipeline with env='{env}' to see each task, its steps,"
            " and internal calls",
            "3. For key tasks, run show_task for the full script and helpers used",
            "4. Run schema to check what data keys the pipeline expects",
            "5. Run diff_envs to check if this pipeline differs across environments",
            "6. Summarize: what this pipeline does, what it signs, where it pushes,",
            "   and what internal services it calls",
            "",
        ]
        if name:
            parts.append(f"Pipeline: {name}")
        else:
            parts.append("Which pipeline?")
        return "\n".join(parts)

    @mcp.prompt()
    def audit(category: str = "managed", env: str = "development"):
        """Audit tasks for resource limits, secrets, and test coverage."""
        return "\n".join(
            [
                f"Audit {category} tasks in {env} for operational readiness.",
                "",
                f"Pass env='{env}' to all tool calls below.",
                "",
                "1. Run resources(mode='missing') to find steps without CPU/memory limits",
                "2. Run secrets to find tasks referencing Kubernetes secrets",
                "3. Run test_coverage to find tasks without tests",
                "4. Run unused_tasks to find orphaned tasks",
                "5. Run timeouts to check timeout configuration",
                "",
                "For each issue found, explain the risk and suggest a fix.",
            ]
        )

    @mcp.prompt()
    def image_update(image: str = "release-service-utils", env: str = "development"):
        """Assess the impact of updating a container image."""
        return "\n".join(
            [
                f"Assess the impact of updating the {image} image in {env}.",
                "",
                f"1. Run search_by_image(image='{image}', env='{env}') to find all affected tasks",
                "2. For each affected task, run show_task to check what it does",
                "3. Run show_tests on affected tasks to check test coverage",
                "4. Check if different tasks pin different image versions",
                "5. List which pipelines would be affected via those tasks",
                "6. Run diff_envs to check if the image change has been promoted",
                "",
                "Flag any tasks that use an old digest vs the majority.",
            ]
        )

    @mcp.prompt()
    def new_task(task_name: str = "", similar_to: str = ""):
        """Guide for adding a new task to the catalog."""
        parts = [
            "Adding a new task to the release-service-catalog.",
            "",
            "1. Run list_tasks to see existing tasks and naming patterns",
        ]
        if similar_to:
            parts.append(f"2. Run show_task(name='{similar_to}') as a reference")
            parts.append(f"3. Run show_tests(name='{similar_to}') to see its test patterns")
        else:
            parts.append("2. Find a similar task with search and use show_task as a reference")
            parts.append("3. Run show_tests on that task to see test patterns")
        parts.extend(
            [
                "4. Run schema to check if the task needs to read data keys",
                "5. Check the contributing guide for naming, params, and test requirements",
                "",
                "Every task needs:",
                "  - At least one unit test in tasks/<category>/<name>/tests/",
                "  - computeResources on every step",
                "  - A description on the task and every param",
            ]
        )
        if task_name:
            parts.append(f"\nTask name: {task_name}")
        return "\n".join(parts)

    @mcp.prompt()
    def onboard(pipeline_name: str = ""):
        """Onboard to a release pipeline you haven't worked with before."""
        parts = [
            "Getting up to speed on a release pipeline.",
            "",
        ]
        if pipeline_name:
            parts.extend(
                [
                    f"1. Run show_pipeline(name='{pipeline_name}') to see the structure",
                    f"2. Run trace_pipeline(name='{pipeline_name}') to see the full flow",
                    "3. Run show_task on 2-3 key tasks (collect-data, the signing task,",
                    "   the push task) to understand the logic",
                    "4. Run docs(query='<pipeline-type>') for related documentation",
                    "5. Run show_tests on the tasks you'll be changing",
                    f"\nPipeline: {pipeline_name}",
                ]
            )
        else:
            parts.extend(
                [
                    "1. Run list_pipelines(category='managed') to see all pipelines",
                    "2. Pick the pipeline and run show_pipeline on it",
                    "3. Run trace_pipeline to see the end-to-end flow",
                    "4. Focus on: what it signs, where it pushes, what internal services it calls",
                ]
            )
        return "\n".join(parts)
