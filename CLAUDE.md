# CLAUDE.md

## What this is

MCP server for the Release Service team. It indexes the release-service-catalog (pipelines + tasks), four supporting repos, and doc pages at container build time.
At runtime it exposes tools, prompts, and resources over MCP stdio so AI assistants can search, trace, compare, and debug release pipelines without network access.

## How it works

1. `config.yaml` defines every repo, catalog environment SHA, and doc URL
2. At container build, `scripts/clone_repos.py` clones repos at pinned SHAs and `scripts/crawl-docs.py` caches doc pages as text
3. At startup, `indexer.py` parses all Tekton YAML into an in-memory `Index` (tasks, pipelines, params, steps, resources, timeouts)
4. Tools query the index and return compact text with GitHub permalink URLs
5. Renovate bumps the SHAs in `config.yaml` daily and auto-merges, so the MCP stays current without manual work

## Commands

```bash
# setup
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# test and lint
pytest tests/ -v
ruff check src/ tests/
ruff format src/ tests/
yamllint .github/ config.yaml

# build and test container
podman build -t release-mcp:latest -f Containerfile .
.github/scripts/container-test.sh localhost/release-mcp:latest
```

## Structure

```
config.yaml                    Single source of truth for repos, SHAs, docs
src/release_mcp/
  server.py                    Entry point, registers all modules
  config.py                    Loads and parses config.yaml
  indexer.py                   Parses Tekton YAML into Index dataclass
  models.py                    Dataclasses: Step, Param, TektonTask, TektonPipeline
  tools/
    search.py                  search, grep
    pipeline.py                show_pipeline, trace_pipeline, diff_pipelines
    task.py                    show_task, list_tasks, list_pipelines, search_by_image, unused_tasks
    validate.py                validate, schema
    ops.py                     timeouts, resources, diff_envs, secrets
    testing.py                 test_coverage, show_tests, e2e_tests, test_gaps
    docs.py                    docs, list_docs
  resources/docs.py            MCP resources (schema, catalog structure, index summary)
  prompts/templates.py         9 prompt templates for common workflows
scripts/
  clone_repos.py               Clones repos at pinned SHAs (build time)
  crawl-docs.py                Caches doc pages as plain text (build time)
tests/
  conftest.py                  Fixtures: builds a sample index from YAML fixtures
  test_indexer.py              Index building, task/pipeline parsing, schema loading
  test_tools.py                Tool output: search, show_pipeline, show_task, validate
  test_docs.py                 Doc search and listing
  test_urls.py                 GitHub permalink URL building
  fixtures/                    Sample Tekton YAML and schema for tests
.github/
  workflows/ci.yaml            Test + lint + renovate check + container build + smoke test
  scripts/container-test.sh    Sends MCP initialize request, verifies response
  renovate.json                Renovate config, auto-bumps SHAs in config.yaml
.yamllint                      YAML lint rules (matches release-service-catalog style)
```

## Design principles

- **Config-driven.** Add a repo or doc page by editing `config.yaml`. No code changes.
- **No runtime network.** Everything baked in at build. The container runs fully offline.
- **Pinned and auto-updated.** Every repo SHA is pinned. Renovate bumps them daily.
- **Flat and simple.** No abstractions for one-time operations. No class hierarchies.
- **Compact output.** Tools return the minimum text needed. GitHub URLs, not full file contents. Short previews, not full scripts.
- **Follow release-service-utils style.** Plain Python, no type annotations on internal functions, no over-engineering.

## Conventions

- Python 3.12, `mcp` SDK (FastMCP)
- Ruff for lint and format (line-length 100)
- `config.yaml` is the single source of truth for all external data
- Catalog indexed per environment (development, staging, production)
- Tool names are short and human: `search`, `grep`, `show_pipeline`, `show_task`
- No `from __future__ import annotations`, no frozen dataclasses, no slots

## Test design

Tests use a sample index built from YAML fixtures in `tests/fixtures/`. The fixtures contain a minimal task (`apply-mapping`) and pipeline (`rh-push-to-registry`) with realistic structure.

Tests verify:
- **Indexer**: tasks and pipelines parsed correctly, params/steps/workspaces/results populated, schema loaded, empty dir handled
- **Tools**: search finds by name, grep returns URLs with line numbers, pipeline graph shows DAG, task explain shows steps, validation catches bad JSON and schema violations
- **Docs**: doc search returns matches with context, list shows cached pages
- **URLs**: permalink builder uses commit SHAs, falls back to HEAD

To add a test for a new tool: add it to `test_tools.py`, register it in `_build_mcp()`, call it with `_call(mcp, "tool_name", ...)`, assert on the output string.

## Adding a new tool

1. Add the function inside the `register_*_tools(mcp, index)` function in the right file
2. Decorate with `@mcp.tool()`
3. Add a docstring with `Args:` section (MCP uses this for the tool description)
4. Query `index.tasks`, `index.pipelines`, or `index.walk_files()` as needed
5. Return a string. Use `index.url_for()` for GitHub links
6. Add a test in `test_tools.py`

## Adding a new repo or doc page

Edit `config.yaml`. That's it. The clone script, crawl script, indexer, and search tools all read from config.

## Running checks locally

Run everything CI runs before pushing:

```bash
# python tests
pytest tests/ -v

# lint and format
ruff check src/ tests/
ruff format --check src/ tests/

# yaml lint
yamllint .github/ config.yaml

# container build and smoke test
podman build -t release-mcp:latest -f Containerfile .
.github/scripts/container-test.sh localhost/release-mcp:latest
```

The container test sends an MCP `initialize` request and checks that the server responds with the correct name. It needs a named pipe to keep stdin open while the server boots and loads the index.

## CI jobs

| Job | What it does |
|-----|-------------|
| `test` | Installs deps, runs pytest |
| `lint` | Runs ruff format check and ruff lint |
| `check-renovate-config` | Validates `.github/renovate.json` |
| `build-container` | Logs into registry.redhat.io, builds the image, runs smoke test |

The `build-container` job needs two repo secrets:
- `REGISTRY_REDHAT_IO_USER` — Red Hat registry service account username
- `REGISTRY_REDHAT_IO_PASSWORD` — Red Hat registry service account token

Create the service account at https://access.redhat.com/terms-based-registry/
