"""Merger nodes for ATTPC Flow."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from attpc_flow_cpp import check_graw_event_id

from ..node import Node
from ..node_manager import auto_register_node
from ..run_tag_db import RunTagDB


class CheckGrawEventIdParameters(BaseModel):
    model_config = ConfigDict(extra="ignore")

    execution_id: str
    task_id: int
    workspace: str
    graw: str
    run: int


@auto_register_node
class CheckGrawEventIdNode(Node):
    _name = "check_graw_event_id"
    _version = "1.0.0"
    _description = "Checks GRAW event ID for a given run"
    _category = "merger"
    _type = "batch"
    _inputs = {}
    _outputs = {}
    _properties = {"graw": "str"}
    _parameters = CheckGrawEventIdParameters

    def execute(self, **kwargs: Any) -> list[Any]:
        execution_id = kwargs.get("execution_id")
        task_id = kwargs.get("task_id")
        workspace = kwargs.get("workspace")
        graw = kwargs.get("graw")
        run = kwargs.get("run")

        result = check_graw_event_id(
            execution_id=execution_id,
            task_id=task_id,
            graw=graw,
            workspace=workspace,
            run=run,
        )
        db = RunTagDB()
        db.set_run_tag(workspace=workspace, run=run, tag=f"evtid:{result}", default_value="unchecked")

        if result == "pass" or result == "missing" or result == "incomplete":
            return [run]
        else:
            return [None]
