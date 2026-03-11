"""Shared test fixtures."""

import json
import shutil
from pathlib import Path

import pytest

from release_mcp.config import CatalogConfig, Config
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
