"""Tests for the indexer."""

from release_mcp.indexer import Index


class TestIndexer:
    def test_tasks_indexed(self, sample_index):
        assert len(sample_index.tasks) > 0
        assert "managed/apply-mapping" in sample_index.tasks

    def test_task_has_steps(self, sample_index):
        task = sample_index.tasks["managed/apply-mapping"]
        assert len(task.steps) == 1
        assert task.steps[0].name == "apply"
        assert "release-service-utils" in task.steps[0].image

    def test_task_has_params(self, sample_index):
        task = sample_index.tasks["managed/apply-mapping"]
        assert len(task.params) == 2
        param_names = [p.name for p in task.params]
        assert "dataPath" in param_names
        assert "snapshotPath" in param_names

    def test_task_has_workspaces(self, sample_index):
        task = sample_index.tasks["managed/apply-mapping"]
        assert len(task.workspaces) == 1
        assert task.workspaces[0].name == "data"

    def test_task_has_results(self, sample_index):
        task = sample_index.tasks["managed/apply-mapping"]
        assert len(task.results) == 1
        assert task.results[0].name == "mapped"

    def test_pipelines_indexed(self, sample_index):
        assert len(sample_index.pipelines) > 0
        assert "managed/rh-push-to-registry" in sample_index.pipelines

    def test_pipeline_has_task_refs(self, sample_index):
        pipeline = sample_index.pipelines["managed/rh-push-to-registry"]
        assert len(pipeline.task_refs) == 3
        names = [t.name for t in pipeline.task_refs]
        assert "collect-data" in names
        assert "apply-mapping" in names
        assert "push-to-registry" in names

    def test_pipeline_has_finally(self, sample_index):
        pipeline = sample_index.pipelines["managed/rh-push-to-registry"]
        assert len(pipeline.finally_refs) == 1
        assert pipeline.finally_refs[0].name == "cleanup"

    def test_pipeline_run_after(self, sample_index):
        pipeline = sample_index.pipelines["managed/rh-push-to-registry"]
        apply = next(t for t in pipeline.task_refs if t.name == "apply-mapping")
        assert "collect-data" in apply.run_after

    def test_schema_loaded(self, sample_index):
        assert sample_index.schema is not None
        assert "properties" in sample_index.schema

    def test_empty_data_dir(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        index = Index(data_dir=empty)
        assert len(index.tasks) == 0
        assert len(index.pipelines) == 0
