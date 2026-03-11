"""Tests for docs tools."""

from mcp.server.fastmcp import FastMCP

from release_mcp.tools.docs import register_docs_tools


def _build_mcp(index):
    mcp = FastMCP("test")
    register_docs_tools(mcp, index)
    return mcp


def _call(mcp, tool_name, **kwargs):
    tools = {n: fn for n, fn in mcp._tool_manager._tools.items()}
    return tools[tool_name].fn(**kwargs)


class TestDocs:
    def test_find(self, sample_index):
        mcp = _build_mcp(sample_index)
        result = _call(mcp, "docs", query="managed pipelines")
        assert "releasing" in result
        assert "match" in result

    def test_no_results(self, sample_index):
        mcp = _build_mcp(sample_index)
        result = _call(mcp, "docs", query="xyznonexistent123")
        assert "No matches" in result

    def test_filter_by_doc(self, sample_index):
        mcp = _build_mcp(sample_index)
        result = _call(mcp, "docs", query="release", doc="releasing")
        assert "konflux-ci.dev" in result

    def test_includes_url(self, sample_index):
        mcp = _build_mcp(sample_index)
        result = _call(mcp, "docs", query="ReleasePlanAdmission")
        assert "https://konflux-ci.dev/docs/releasing/" in result


class TestListDocs:
    def test_list(self, sample_index):
        mcp = _build_mcp(sample_index)
        result = _call(mcp, "list_docs")
        assert "releasing" in result
        assert "konflux-ci.dev" in result
