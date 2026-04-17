"""Shared test fixtures."""

import json
import shutil
from pathlib import Path

import pytest

from release_mcp.config import CatalogConfig, CatalogEnv, Config
from release_mcp.indexer import build_index

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR


@pytest.fixture
def sample_index(tmp_path):
    """Build an index from test fixtures arranged like a real catalog repo."""
    catalog = tmp_path / "release-service-catalog"
    managed_tasks = catalog / "tasks" / "managed"
    managed_pipelines = catalog / "pipelines" / "managed"
    schema_dir = catalog / "schema"

    managed_tasks.mkdir(parents=True)
    managed_pipelines.mkdir(parents=True)
    schema_dir.mkdir(parents=True)

    shutil.copy(FIXTURES_DIR / "sample-task.yaml", managed_tasks / "apply-mapping.yaml")
    shutil.copy(
        FIXTURES_DIR / "sample-pipeline.yaml",
        managed_pipelines / "rh-push-to-registry.yaml",
    )
    shutil.copy(FIXTURES_DIR / "sample-schema.json", schema_dir / "dataKeys.json")

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "releasing.txt").write_text(
        "Releasing overview\n"
        "The release service handles managed pipelines.\n"
        "ReleasePlanAdmission controls which pipelines run.\n"
        "Data keys define the schema for pipeline parameters.\n"
    )
    manifest = {
        "releasing": {
            "url": "https://konflux-ci.dev/docs/releasing/",
            "file": "releasing.txt",
            "size": 180,
        }
    }
    (docs_dir / "manifest.json").write_text(json.dumps(manifest))

    config = Config(catalog=CatalogConfig())
    return build_index(str(tmp_path), config=config)


@pytest.fixture
def multi_env_index(tmp_path):
    """Build an index with development and production catalogs.

    Development has an extra task (collect-signing-params) and an extra
    pipeline task ref that production lacks — reproducing the
    scenario where dev is ahead of prod.
    """
    schema_dir = tmp_path / "release-service-catalog-development" / "schema"
    schema_dir.mkdir(parents=True)
    shutil.copy(FIXTURES_DIR / "sample-schema.json", schema_dir / "dataKeys.json")

    for env_name in ("development", "production"):
        catalog = tmp_path / f"release-service-catalog-{env_name}"
        managed_tasks = catalog / "tasks" / "managed"
        managed_pipelines = catalog / "pipelines" / "managed"
        managed_tasks.mkdir(parents=True)
        managed_pipelines.mkdir(parents=True)

        # apply-mapping task + a test pipeline for it (in both envs)
        am_dir = managed_tasks / "apply-mapping"
        am_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(FIXTURES_DIR / "sample-task.yaml", am_dir / "apply-mapping.yaml")
        test_dir = am_dir / "tests"
        test_dir.mkdir(parents=True, exist_ok=True)
        (test_dir / "test-apply-mapping-good.yaml").write_text(
            "apiVersion: tekton.dev/v1\n"
            "kind: Pipeline\n"
            "metadata:\n"
            "  name: test-apply-mapping-good\n"
            "spec:\n"
            "  tasks:\n"
            "    - name: run-test\n"
            "      taskRef:\n"
            "        name: apply-mapping\n"
        )

        if env_name == "development":
            # Dev has an extra task not yet in production
            extra_task = managed_tasks / "collect-signing-params.yaml"
            extra_task.write_text(
                "apiVersion: tekton.dev/v1\n"
                "kind: Task\n"
                "metadata:\n"
                "  name: collect-signing-params\n"
                "spec:\n"
                "  steps:\n"
                "    - name: collect\n"
                "      image: quay.io/konflux-ci/release-service-utils:latest\n"
                "      script: echo collect\n"
            )
            # Dev pipeline has 4 task refs (extra one)
            dev_pipeline = managed_pipelines / "rh-push-to-registry.yaml"
            dev_pipeline.write_text(
                "apiVersion: tekton.dev/v1\n"
                "kind: Pipeline\n"
                "metadata:\n"
                "  name: rh-push-to-registry\n"
                "spec:\n"
                "  tasks:\n"
                "    - name: collect-data\n"
                "      taskRef:\n"
                "        name: collect-release-data\n"
                "    - name: apply-mapping\n"
                "      taskRef:\n"
                "        name: apply-mapping\n"
                "      runAfter: [collect-data]\n"
                "    - name: collect-signing-params\n"
                "      taskRef:\n"
                "        name: collect-signing-params\n"
                "      runAfter: [collect-data]\n"
                "    - name: push-to-registry\n"
                "      taskRef:\n"
                "        name: push-container-image\n"
                "      runAfter: [apply-mapping, collect-signing-params]\n"
                "  finally:\n"
                "    - name: cleanup\n"
                "      taskRef:\n"
                "        name: release-cleanup\n"
            )
        else:
            # Production pipeline has only 3 task refs (no collect-signing-params)
            shutil.copy(
                FIXTURES_DIR / "sample-pipeline.yaml",
                managed_pipelines / "rh-push-to-registry.yaml",
            )

    config = Config(
        catalog=CatalogConfig(
            environments={
                "development": CatalogEnv(branch="development", ref="dev123"),
                "production": CatalogEnv(branch="production", ref="prod456"),
            }
        )
    )
    return build_index(str(tmp_path), config=config)
