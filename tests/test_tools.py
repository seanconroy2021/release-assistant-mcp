"""Tests for MCP tools."""

import json

from mcp.server.fastmcp import FastMCP

from release_mcp.tools.pipeline import register_pipeline_tools
from release_mcp.tools.search import register_search_tools
from release_mcp.tools.task import register_task_tools
from release_mcp.tools.validate import register_validate_tools


def _build_mcp(index):
    mcp = FastMCP("test")
    register_search_tools(mcp, index)
    register_pipeline_tools(mcp, index)
    register_task_tools(mcp, index)
    register_validate_tools(mcp, index)
    return mcp


def _call(mcp, tool_name, **kwargs):
    tools = {n: fn for n, fn in mcp._tool_manager._tools.items()}
    return tools[tool_name].fn(**kwargs)


class TestSearch:
    def test_find_task(self, sample_index):
        mcp = _build_mcp(sample_index)
        result = _call(mcp, "search", query="apply-mapping")
        assert "apply-mapping" in result
        assert "result(s)" in result

    def test_no_results(self, sample_index):
        mcp = _build_mcp(sample_index)
        result = _call(mcp, "search", query="nonexistent-xyz-123")
        assert "No results" in result

    def test_filter_by_kind(self, sample_index):
        mcp = _build_mcp(sample_index)
        result = _call(mcp, "search", query="rh-push", kind="pipeline")
        assert "pipeline" in result
        assert "rh-push-to-registry" in result

    def test_includes_url(self, sample_index):
        mcp = _build_mcp(sample_index)
        result = _call(mcp, "search", query="apply-mapping")
        assert "github.com/konflux-ci" in result


class TestGrep:
    def test_includes_url(self, sample_index):
        mcp = _build_mcp(sample_index)
        result = _call(mcp, "grep", query="apply_mapping", repo="release-service-catalog")
        assert "github.com/konflux-ci" in result
        assert "#L" in result


class TestShowPipeline:
    def test_output(self, sample_index):
        mcp = _build_mcp(sample_index)
        result = _call(mcp, "show_pipeline", name="rh-push-to-registry")
        assert "rh-push-to-registry" in result
        assert "collect-data" in result
        assert "apply-mapping" in result
        assert "DAG" in result
        assert "github.com/konflux-ci" in result

    def test_not_found(self, sample_index):
        mcp = _build_mcp(sample_index)
        result = _call(mcp, "show_pipeline", name="nope")
        assert "not found" in result


class TestShowTask:
    def test_output(self, sample_index):
        mcp = _build_mcp(sample_index)
        result = _call(mcp, "show_task", name="apply-mapping")
        assert "apply-mapping" in result
        assert "release-service-utils" in result
        assert "github.com/konflux-ci" in result

    def test_not_found(self, sample_index):
        mcp = _build_mcp(sample_index)
        result = _call(mcp, "show_task", name="nope")
        assert "not found" in result


class TestListTasks:
    def test_list_all(self, sample_index):
        mcp = _build_mcp(sample_index)
        result = _call(mcp, "list_tasks")
        assert "apply-mapping" in result
        assert "github.com/konflux-ci" in result


class TestListPipelines:
    def test_list_all(self, sample_index):
        mcp = _build_mcp(sample_index)
        result = _call(mcp, "list_pipelines")
        assert "rh-push-to-registry" in result
        assert "github.com/konflux-ci" in result


class TestValidate:
    def test_valid(self, sample_index):
        mcp = _build_mcp(sample_index)
        data = json.dumps({"advisory": {"id": "RHSA-123"}, "images": []})
        result = _call(mcp, "validate", data_json=data)
        assert "passed" in result

    def test_invalid_json(self, sample_index):
        mcp = _build_mcp(sample_index)
        result = _call(mcp, "validate", data_json="not json")
        assert "Invalid JSON" in result

    def test_schema_violation(self, sample_index):
        mcp = _build_mcp(sample_index)
        data = json.dumps({"advisory": {"type": "INVALID"}})
        result = _call(mcp, "validate", data_json=data)
        assert "failed" in result or "Validation" in result
