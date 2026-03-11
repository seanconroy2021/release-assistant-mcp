"""Load configuration from config.yaml."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml

CONFIG_PATHS = [
    Path("/app/config.yaml"),
    Path(__file__).resolve().parent.parent.parent / "config.yaml",
]


@dataclass
class RepoConfig:
    name: str
    url: str
    ref: str = ""
    description: str = ""


@dataclass
class DocConfig:
    name: str
    url: str


@dataclass
class CatalogEnv:
    branch: str
    ref: str


@dataclass
class CatalogConfig:
    repo: str = "release-service-catalog"
    url: str = "https://github.com/konflux-ci/release-service-catalog"
    schema_path: str = "schema/dataKeys.json"
    environments: dict = field(default_factory=dict)


@dataclass
class Config:
    repos: list = field(default_factory=list)
    catalog: CatalogConfig = field(default_factory=CatalogConfig)
    docs: list = field(default_factory=list)

    @property
    def repo_names(self):
        return [r.name for r in self.repos]


def load_config(config_path=None):
    if config_path:
        path = Path(config_path)
        if path.exists():
            return _parse(path)

    for path in CONFIG_PATHS:
        if path.exists():
            return _parse(path)

    return Config()


def _parse(path):
    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict):
        return Config()

    repos = [
        RepoConfig(name=r.get("name", ""), url=r.get("url", ""), ref=r.get("ref", ""))
        for r in raw.get("repos", [])
    ]

    docs = [DocConfig(name=d.get("name", ""), url=d.get("url", "")) for d in raw.get("docs", [])]

    raw_catalog = raw.get("catalog", {})
    envs = {}
    for name, data in raw_catalog.get("environments", {}).items():
        envs[name] = CatalogEnv(branch=data.get("branch", name), ref=data.get("ref", ""))

    catalog = CatalogConfig(
        repo=raw_catalog.get("repo", "release-service-catalog"),
        url=raw_catalog.get("url", "https://github.com/konflux-ci/release-service-catalog"),
        schema_path=raw_catalog.get("schema_path", "schema/dataKeys.json"),
        environments=envs,
    )

    return Config(repos=repos, catalog=catalog, docs=docs)
