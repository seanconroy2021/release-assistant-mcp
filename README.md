# release-assistant-mcp

> 🤖 Built entirely through Claude prompting with minimal human review.

MCP server for Release Service

## Setup

### Claude Code

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "release": {
      "command": "podman",
      "args": ["run", "--rm", "-i", "--pull=always", "quay.io/rh-ee-sconroy/release-assistant-mcp:latest"]
    }
  }
}
```

`--pull=always` is optional but recommended. It ensures you always get the latest catalog data instead of a stale cached image.

### Cursor

Add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "release": {
      "command": "podman",
      "args": ["run", "--rm", "-i", "--pull=always", "quay.io/rh-ee-sconroy/release-assistant-mcp:latest"]
    }
  }
}
```
`--pull=always` is optional but recommended. It ensures you always get the latest catalog data instead of a stale cached image.

## Tools

Most tools accept an `env` parameter (`development`, `staging`, or `production`). When omitted, tools default to the development catalog and deduplicate results across environments.

| Tool | What it does |
|------|-------------|
| `search` | Find pipelines or tasks by name |
| `grep` | Search file contents across all repos |
| `docs` | Search cached documentation |
| `list_docs` | List cached doc pages |
| `show_pipeline` | Show pipeline DAG, params, workspaces |
| `trace_pipeline` | Trace a pipeline through tasks and internal calls |
| `diff_pipelines` | Compare two pipelines side by side |
| `show_task` | Show task steps, images, params, helpers |
| `list_tasks` | List all tasks |
| `list_pipelines` | List all pipelines |
| `search_by_image` | Find tasks using a container image |
| `unused_tasks` | Find tasks no pipeline references |
| `validate` | Validate JSON against the dataKeys schema |
| `schema` | Browse the dataKeys schema |
| `timeouts` | Show timeout settings across pipelines |
| `resources` | Show compute limits on task steps |
| `diff_envs` | Compare dev vs staging vs production catalog |
| `secrets` | Find tasks referencing Kubernetes secrets |
| `test_coverage` | Show which tasks have tests |
| `show_tests` | List tests for a specific task |
| `e2e_tests` | List integration test pipelines |
| `test_gaps` | Suggest missing test cases for a task |

## Prompts

Use these to start common workflows:

| Prompt | When to use |
|--------|------------|
| `troubleshoot` | Pipeline run failed, need to find the root cause |
| `investigate_timeout` | A task is timing out or running slow |
| `review_tests` | Check test coverage, find gaps |
| `compare_environments` | See what changed between dev/staging/prod |
| `understand_pipeline` | Learn how a pipeline works end to end |
| `audit` | Check resource limits, secrets, test coverage |
| `image_update` | Assess impact of bumping a container image |
| `new_task` | Adding a new task to the catalog |
| `onboard` | First time working on a pipeline |

## Configuration

Everything is in `config.yaml`.

```yaml
repos:
  - name: release-service
    url: https://github.com/konflux-ci/release-service
    ref: abc123... # main

catalog:
  environments:
    development:
      branch: development
      ref: def456...
    staging:
      branch: staging
      ref: ghi789...
    production:
      branch: production
      ref: jkl012...

docs:
  - name: releasing
    url: https://konflux-ci.dev/docs/releasing/
```

To add a new repo: add it to `config.yaml`. To add a new doc page: add it to `config.yaml`.

## Repos indexed

| Repo | What it is |
|------|-----------|
| [release-service](https://github.com/konflux-ci/release-service) | Operator |
| [internal-services](https://github.com/konflux-ci/internal-services) | Internal cluster controller |
| [release-service-utils](https://github.com/konflux-ci/release-service-utils) | Base image with helper functions |
| [release-service-collectors](https://github.com/konflux-ci/release-service-collectors) | Collector scripts |
| [release-service-catalog](https://github.com/konflux-ci/release-service-catalog) | Tekton pipelines and tasks |

## Docs indexed

| Page | Source |
|------|--------|
| [Releasing](https://konflux-ci.dev/docs/releasing/) | konflux-ci.dev |
| [Release Service architecture](https://konflux-ci.dev/architecture/core/release-service/) | konflux-ci.dev |
| [Internal Services architecture](https://konflux-ci.dev/architecture/add-ons/internal-services/) | konflux-ci.dev |
| [Tekton Pipelines](https://tekton.dev/docs/pipelines/pipelines/) | tekton.dev |
| [Tekton Tasks](https://tekton.dev/docs/pipelines/tasks/) | tekton.dev |

## Examples

**Show the rh-push-to-registry-redhat-io pipeline DAG:**

```
show_pipeline(name="rh-push-to-registry-redhat-io")

managed/rh-push-to-registry-redhat-io
DAG (16 tasks):
  |- verify-access-to-resources
    |- collect-data
      |- collect-task-params
        |- verify-conforma
          |- rh-sign-image
            |- push-snapshot [when]
              |- rh-sign-image-cosign [when]
              |- create-pyxis-image
                |- push-rpm-data-to-pyxis
                  |- run-file-updates
                    |- update-cr-status
        |- publish-pyxis-repository
      |- check-data-keys
      |- reduce-snapshot
        |- apply-mapping
    |- extract-requester-from-release
Finally: cleanup-internal-requests
```

**Compare rh-advisories vs rh-rpm-advisories:**

```
diff_pipelines(name_a="rh-advisories", name_b="rh-rpm-advisories")

rh-advisories vs rh-rpm-advisories (managed)
Tasks: 26 vs 6
Shared (6): collect-data, collect-task-params, create-advisory, reduce-snapshot,
            verify-access-to-resources, verify-conforma
Only in rh-advisories: apply-mapping, check-data-keys, check-labels, ...
```

**Compare dev vs production to see what hasn't been promoted:**

```
diff_envs(env_a="development", env_b="production")

development vs production
Shared: 82, only development: 4, only production: 0

Only in development (4):
  managed/collect-signing-params
  managed/sign-image-cosign-keyless
  ...
```

**Find all tasks with timeouts:**

```
timeouts(category="managed")

36 task(s) with timeouts:
  managed/fbc-release/verify-conforma: 4h00m0s
  managed/fbc-release/rh-sign-index-image-cosign: 6h00m0s
  managed/push-disk-images-to-marketplaces/marketplacesvm-push-disk-images: 12h00m0s
  ...
```

**Find orphaned tasks:**

```
unused_tasks()

4 unreferenced task(s):
  internal/create-advisory-oci-artifact-task
  managed/kubernetes-actions
  managed/prepare-validation
  managed/push-oot-kmods-to-git
```

**Internal test coverage:**

```
test_coverage(category="internal")

No tests (1):
  internal/create-advisory-oci-artifact-task
Low coverage, 1-2 tests (5):
  internal/check-fbc-opt-in: 1 test(s)
  internal/check-signing-certificates: 1 test(s)
  ...
Covered, 3+ tests (11):
  internal/push-artifacts-to-cdn-task: 23 test(s)
  internal/create-advisory-task: 12 test(s)
  ...
```

**Find tasks referencing secrets:**

```
secrets(category="managed")

42 secret reference(s):
  managed/rh-sign-image/sign-image: script references secrets
  managed/push-rpms-to-pulp/push-rpms-to-pulp: script references secrets
  ...
```

**Browse the dataKeys schema:**

```
schema(path="properties")

{
  "systems": { ... },
  "fbc": { ... },
  "releaseNotes": { ... },
  "sign": { ... },
  "cdn": { ... },
  ...
}
```

**Diff two pipelines:**

```
diff_pipelines(name_a="rh-advisories", name_b="rh-rpm-advisories")

Tasks: 26 vs 6, Params: 17 vs 17
Shared (6): collect-data, collect-task-params, create-advisory, ...
Only in rh-advisories: apply-mapping, check-labels, embargo-check, ...
```

## Local development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v
ruff check src/ tests/
```

Build locally:

```bash
podman build -t release-mcp:latest -f Containerfile .
```
