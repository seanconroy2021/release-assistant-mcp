"""Tests for URL building."""

from release_mcp.indexer import Index


class TestUrlFor:
    def test_basic_url(self):
        index = Index()
        url = index.url_for(
            "release-service-catalog", "pipelines/managed/fbc-release/fbc-release.yaml"
        )
        assert (
            url == "https://github.com/konflux-ci/release-service-catalog/blob/HEAD/"
            "pipelines/managed/fbc-release/fbc-release.yaml"
        )

    def test_with_line(self):
        index = Index()
        url = index.url_for(
            "release-service-catalog", "pipelines/managed/fbc-release/fbc-release.yaml", line=9
        )
        assert url.endswith("#L9")

    def test_with_commit_sha(self):
        commits = {"release-service-catalog": "085dbcb90c5eef6641e89a27336d50133dc39605"}
        index = Index(commits=commits)
        url = index.url_for(
            "release-service-catalog", "pipelines/managed/fbc-release/fbc-release.yaml", line=9
        )
        assert "085dbcb90c5eef6641e89a27336d50133dc39605" in url
        assert url.endswith("#L9")

    def test_fallback_without_commit(self):
        index = Index(commits={"other": "abc"})
        url = index.url_for("some-repo", "file.yaml")
        assert "/blob/HEAD/" in url
