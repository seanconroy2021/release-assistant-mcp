"""MCP server entry point."""

import logging

from mcp.server.fastmcp import FastMCP

from .config import load_config
from .indexer import build_index
from .prompts.templates import register_prompts
from .resources.docs import register_resources
from .tools.docs import register_docs_tools
from .tools.ops import register_ops_tools
from .tools.pipeline import register_pipeline_tools
from .tools.search import register_search_tools
from .tools.task import register_task_tools
from .tools.testing import register_testing_tools
from .tools.validate import register_validate_tools

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
LOGGER = logging.getLogger(__name__)


def create_server():
    mcp = FastMCP("Release Assistant MCP")
    config = load_config()

    LOGGER.info("Building index...")
    index = build_index(config=config)
    LOGGER.info("Index ready.")

    LOGGER.info("Release Assistant MCP")
    catalog = config.catalog
    if catalog.environments:
        LOGGER.info("Catalog:")
        for name, env in catalog.environments.items():
            loaded = "*" if name in index.catalog_envs else " "
            LOGGER.info("  %s %-12s %s", loaded, name, env.ref[:12])
    if config.repos:
        LOGGER.info("Repos:")
        for repo in config.repos:
            sha = index.commits.get(repo.name, repo.ref)
            LOGGER.info("  %-30s %s", repo.name, sha[:12])
    LOGGER.info(
        "%d tasks, %d pipelines, %d helpers",
        len(index.tasks),
        len(index.pipelines),
        len(index.utils_helpers),
    )

    register_search_tools(mcp, index)
    register_pipeline_tools(mcp, index)
    register_task_tools(mcp, index)
    register_validate_tools(mcp, index)
    register_ops_tools(mcp, index)
    register_testing_tools(mcp, index)
    register_docs_tools(mcp, index)
    register_resources(mcp, index)
    register_prompts(mcp)

    return mcp


def main():
    server = create_server()
    server.run()


if __name__ == "__main__":
    main()
