"""Data models for parsed Tekton resources."""

from dataclasses import dataclass, field


@dataclass
class Step:
    name: str
    image: str
    script: str = ""
    command: list = field(default_factory=list)
    env: dict = field(default_factory=dict)
    # {limits: {cpu, memory}, requests: {cpu, memory}}
    resources: dict = field(default_factory=dict)


@dataclass
class Param:
    name: str
    type: str = "string"
    description: str = ""
    default: str = None


@dataclass
class Workspace:
    name: str
    description: str = ""
    optional: bool = False


@dataclass
class Result:
    name: str
    description: str = ""


@dataclass
class PipelineTaskRef:
    name: str
    task_ref: str = None
    run_after: tuple = ()
    has_when: bool = False
    timeout: str = ""


@dataclass
class TektonTask:
    name: str
    path: str
    repo: str
    category: str
    steps: list = field(default_factory=list)
    params: list = field(default_factory=list)
    workspaces: list = field(default_factory=list)
    results: list = field(default_factory=list)
    description: str = ""
    env: str = ""


@dataclass
class TektonPipeline:
    name: str
    path: str
    repo: str
    category: str
    task_refs: list = field(default_factory=list)
    params: list = field(default_factory=list)
    workspaces: list = field(default_factory=list)
    finally_refs: list = field(default_factory=list)
    description: str = ""
    env: str = ""
