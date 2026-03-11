from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path


def _load_package(monkeypatch, binding_result: str = "success"):
    src_path = Path(__file__).resolve().parents[1] / "src"
    monkeypatch.syspath_prepend(str(src_path))

    fake_lib = types.ModuleType("attpc_merger_wrapper._lib")
    fake_lib.calls = []

    def merger_attpc_binding(**kwargs):
        fake_lib.calls.append(kwargs)
        return binding_result

    fake_lib.merger_attpc_binding = merger_attpc_binding
    monkeypatch.setitem(sys.modules, "attpc_merger_wrapper._lib", fake_lib)

    for module_name in [
        "attpc_merger_wrapper",
        "attpc_merger_wrapper.api",
        "attpc_merger_wrapper.attpc_merger_wrapper_node",
    ]:
        sys.modules.pop(module_name, None)

    package = importlib.import_module("attpc_merger_wrapper")
    api = importlib.import_module("attpc_merger_wrapper.api")
    node_module = importlib.import_module("attpc_merger_wrapper.attpc_merger_wrapper_node")
    return package, api, node_module, fake_lib


def test_merge_attpc_discards_when_evtid_tag_not_allowed(monkeypatch, tmp_path):
    _, api, _, fake_lib = _load_package(monkeypatch)

    class FakeDB:
        def __init__(self):
            self.tags = []

        def get_run_tag(self, workspace, run, group):
            return "failed" if group == "evtid" else None

        def set_run_tag(self, workspace, run, tag, default_value=None):
            self.tags.append((Path(workspace), run, tag, default_value))

    discarded = []
    monkeypatch.setattr(api, "RunTagDB", FakeDB)
    monkeypatch.setattr(
        api.progress_store,
        "discard_task",
        lambda execution_id, task_id: discarded.append((execution_id, task_id)),
    )

    result = api.merge_attpc(
        execution_id="exec",
        task_id=7,
        workspace=str(tmp_path),
        graw="graw",
        evt="evt",
        map="map",
        run=42,
    )

    assert result is None
    assert fake_lib.calls == []
    assert discarded == [("exec", "7")]


def test_merge_attpc_returns_run_and_updates_tag(monkeypatch, tmp_path):
    _, api, _, fake_lib = _load_package(monkeypatch, binding_result="success")

    class FakeDB:
        instances = []

        def __init__(self):
            self.tags = []
            FakeDB.instances.append(self)

        def get_run_tag(self, workspace, run, group):
            if group == "evtid":
                return "pass"
            if group == "merger":
                return "failed"
            return None

        def set_run_tag(self, workspace, run, tag, default_value=None):
            self.tags.append((Path(workspace), run, tag, default_value))

    monkeypatch.setattr(api, "RunTagDB", FakeDB)

    result = api.merge_attpc(
        execution_id="exec",
        task_id=3,
        workspace=str(tmp_path),
        graw="graw",
        evt="evt",
        map="map",
        run=12,
    )

    assert result == 12
    assert fake_lib.calls == [
        {
            "execution_id": "exec",
            "task_id": 3,
            "workspace": str(tmp_path),
            "graw": "graw",
            "evt": "evt",
            "map": "map",
            "run": 12,
            "merger_tag": "failed",
        }
    ]
    assert FakeDB.instances[0].tags[-1] == (tmp_path, 12, "merger:success", "unmerged")
    log_path = tmp_path / "log" / "attpc_merger" / "12.log"
    assert log_path.exists()


def test_node_execute_delegates_to_merge_attpc(monkeypatch):
    _, _, node_module, _ = _load_package(monkeypatch)

    called = []
    monkeypatch.setattr(node_module, "merge_attpc", lambda **kwargs: called.append(kwargs) or 9)

    node = node_module.AttpcMergerNode()
    result = node.execute(
        execution_id="exec",
        task_id=1,
        workspace="/tmp/workspace",
        graw="graw",
        evt="evt",
        map="map",
        run=9,
    )

    assert result == [9]
    assert called == [
        {
            "execution_id": "exec",
            "task_id": 1,
            "workspace": "/tmp/workspace",
            "graw": "graw",
            "evt": "evt",
            "map": "map",
            "run": 9,
        }
    ]
