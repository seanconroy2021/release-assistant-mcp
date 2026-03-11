"""Indexes Tekton resources from cloned repos."""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .config import Config, load_config
from .models import Param, PipelineTaskRef, Result, Step, TektonPipeline, TektonTask, Workspace

LOGGER = logging.getLogger(__name__)

GITHUB_ORG = "https://github.com/konflux-ci"
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".tox", "vendor"}
PYTHON_DEF = re.compile(r"^def\s+([a-z_]\w*)\s*\(", re.MULTILINE)

DEFAULT_MARKERS = {
    "internal-services",
    "InternalServicesConfig",
    "create_internal_request",
    "internal-request",
    "InternalRequest",
}


@dataclass
class Index:
    tasks: dict = field(default_factory=dict)
    pipelines: dict = field(default_factory=dict)
    schema: dict = None
    data_dir: Path = field(default_factory=lambda: Path("/data"))
    commits: dict = field(default_factory=dict)
    utils_helpers: set = field(default_factory=set)
    internal_markers: set = field(default_factory=set)
    config: Config = field(default_factory=Config)
    catalog_envs: list = field(default_factory=list)

    @property
    def task_list(self):
        return list(self.tasks.values())

    @property
    def pipeline_list(self):
        return list(self.pipelines.values())

    def find_task(self, name, category):
        return self.tasks.get(f"{category}/{name}") or next(
            (t for t in self.task_list if t.name == name and t.category == category), None
        )

    def find_pipeline(self, name, category):
        return self.pipelines.get(f"{category}/{name}") or next(
            (p for p in self.pipeline_list if p.name == name and p.category == category), None
        )

    def suggest(self, items, name, category):
        q = name.lower()
        return [
            x.name
            for x in items
            if (category == "all" or x.category == category)
            and (q in x.name.lower() or x.name.lower() in q)
        ][:10]

    def url_for(self, repo, path, line=None):
        ref = self.commits.get(repo, "HEAD")
        url = f"{GITHUB_ORG}/{repo}/blob/{ref}/{path}"
        if line:
            url += f"#L{line}"
        return url

    def catalog_dir(self, env):
        return f"{self.config.catalog.repo}-{env}"

    @property
    def searchable_repos(self):
        return self.config.repo_names + [self.catalog_dir(e) for e in self.catalog_envs]

    def walk_files(self, repo_name, file_pattern=""):
        repo_path = self.data_dir / repo_name
        if not repo_path.exists():
            return []
        files = []
        for dirpath, dirnames, filenames in os.walk(repo_path):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            dp = Path(dirpath)
            for f in filenames:
                if file_pattern and not _glob_match(f, file_pattern):
                    continue
                files.append(dp / f)
        return files


def build_index(data_dir=None, config=None):
    if config is None:
        config = load_config()
    root = Path(data_dir or os.environ.get("RELEASE_MCP_DATA_DIR", "/data"))
    index = Index(data_dir=root, config=config)

    if not root.exists():
        LOGGER.warning("Data directory %s not found", root)
        return index

    # Load commits
    commits_path = root / "commits.json"
    if commits_path.exists():
        try:
            index.commits = json.loads(commits_path.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    # Index catalogs
    envs = config.catalog.environments
    if envs:
        for env_name in envs:
            catalog = root / f"{config.catalog.repo}-{env_name}"
            if catalog.exists():
                _index_catalog(catalog, f"{config.catalog.repo}-{env_name}", index)
                index.catalog_envs.append(env_name)
    else:
        catalog = root / config.catalog.repo
        if catalog.exists():
            _index_catalog(catalog, config.catalog.repo, index)

    # Load schema from first available catalog
    schema_rel = config.catalog.schema_path
    for env_name in index.catalog_envs or [""]:
        dir_name = f"{config.catalog.repo}-{env_name}" if env_name else config.catalog.repo
        schema_path = root / dir_name / schema_rel
        if schema_path.exists():
            try:
                index.schema = json.loads(schema_path.read_text())
            except (json.JSONDecodeError, OSError):
                pass
            break

    # Discover utils helpers
    utils_dir = root / "release-service-utils"
    if utils_dir.exists():
        for py_file in utils_dir.rglob("*.py"):
            try:
                text = py_file.read_text(errors="replace")
            except OSError:
                continue
            for m in PYTHON_DEF.finditer(text):
                if not m.group(1).startswith("_"):
                    index.utils_helpers.add(m.group(1))
        LOGGER.info("Discovered %d utils helpers", len(index.utils_helpers))

    # Discover internal markers
    internal_dir = root / "internal-services"
    index.internal_markers = set(DEFAULT_MARKERS)
    if internal_dir.exists():
        kind_re = re.compile(r'Kind:\s*"(\w+)"')
        type_re = re.compile(r"type\s+(\w*(?:Internal|Request)\w*)\s+struct")
        for go_file in internal_dir.rglob("*.go"):
            try:
                text = go_file.read_text(errors="replace")
            except OSError:
                continue
            for m in kind_re.finditer(text):
                index.internal_markers.add(m.group(1))
            for m in type_re.finditer(text):
                index.internal_markers.add(m.group(1))
        LOGGER.info("Discovered %d internal markers", len(index.internal_markers))

    LOGGER.info(
        "Indexed %d tasks, %d pipelines across %d catalog env(s)",
        len(index.tasks),
        len(index.pipelines),
        len(index.catalog_envs),
    )
    return index


def _index_catalog(catalog, repo_name, index):
    for path in catalog.rglob("*.yaml"):
        _parse_yaml(path, catalog, repo_name, index)
    for path in catalog.rglob("*.yml"):
        _parse_yaml(path, catalog, repo_name, index)


def _parse_yaml(path, repo_root, repo_name, index):
    try:
        docs = list(yaml.safe_load_all(path.read_text()))
    except (OSError, yaml.YAMLError):
        return

    for doc in docs:
        if not isinstance(doc, dict):
            continue
        kind = doc.get("kind", "")
        if kind == "Task":
            _parse_task(doc, path, repo_root, repo_name, index)
        elif kind == "Pipeline":
            _parse_pipeline(doc, path, repo_root, repo_name, index)


def _category(path):
    parts = {p.lower() for p in path.parts}
    if "internal" in parts:
        return "internal"
    if parts & {"collector", "collectors"}:
        return "collector"
    return "managed"


def _parse_param(raw):
    default = raw.get("default")
    if default is not None and not isinstance(default, str):
        default = str(default)
    return Param(
        name=raw.get("name", ""),
        type=raw.get("type", "string"),
        description=raw.get("description", ""),
        default=default,
    )


def _parse_task(doc, path, repo_root, repo_name, index):
    meta = doc.get("metadata", {})
    spec = doc.get("spec", {})
    name = meta.get("name", path.stem)

    steps = []
    for s in spec.get("steps", []):
        env = {e["name"]: str(e["value"]) for e in s.get("env", []) if "name" in e and "value" in e}
        steps.append(
            Step(
                name=s.get("name", ""),
                image=s.get("image", ""),
                script=s.get("script", ""),
                command=s.get("command", []),
                env=env,
                resources=s.get("computeResources", {}),
            )
        )

    task = TektonTask(
        name=name,
        path=str(path.relative_to(repo_root)),
        repo=repo_name,
        category=_category(path),
        steps=steps,
        params=[_parse_param(p) for p in spec.get("params", [])],
        workspaces=[
            Workspace(
                name=w.get("name", ""),
                description=w.get("description", ""),
                optional=w.get("optional", False),
            )
            for w in spec.get("workspaces", [])
        ],
        results=[
            Result(name=r.get("name", ""), description=r.get("description", ""))
            for r in spec.get("results", [])
        ],
        description=spec.get("description", meta.get("description", "")),
    )
    index.tasks[f"{task.category}/{task.name}"] = task


def _parse_task_ref(raw):
    ref = raw.get("taskRef", {})
    return PipelineTaskRef(
        name=raw.get("name", ""),
        task_ref=ref.get("name") if isinstance(ref, dict) else None,
        run_after=tuple(raw.get("runAfter", [])),
        has_when=bool(raw.get("when")),
        timeout=raw.get("timeout", ""),
    )


def _parse_pipeline(doc, path, repo_root, repo_name, index):
    meta = doc.get("metadata", {})
    spec = doc.get("spec", {})
    name = meta.get("name", path.stem)

    pipeline = TektonPipeline(
        name=name,
        path=str(path.relative_to(repo_root)),
        repo=repo_name,
        category=_category(path),
        task_refs=[_parse_task_ref(t) for t in spec.get("tasks", [])],
        params=[_parse_param(p) for p in spec.get("params", [])],
        workspaces=[
            Workspace(
                name=w.get("name", ""),
                description=w.get("description", ""),
                optional=w.get("optional", False),
            )
            for w in spec.get("workspaces", [])
        ],
        finally_refs=[_parse_task_ref(t) for t in spec.get("finally", [])],
        description=spec.get("description", meta.get("description", "")),
    )
    index.pipelines[f"{pipeline.category}/{pipeline.name}"] = pipeline


def _glob_match(filename, pattern):
    if pattern.startswith("*."):
        return filename.endswith(pattern[1:])
    return pattern in filename
