"""Merger nodes for ATTPC Flow."""

from typing import Any, Dict, List, Type

from pydantic import BaseModel

from attpc_flow_cpp import check_graw_event_id

from ..node import Node
from ..node_manager import auto_register_node
from ..run_tag_db import RunTagDB

class CheckGrawEventIdParameters(BaseModel):
    execution_id: str
    task_id: int
    workspace: str
    graw: str
    run: int


@auto_register_node
class CheckGrawEventIdNode(Node):
    @property
    def name(self) -> str:
        return "check_graw_event_id"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Checks GRAW event ID for a given run"

    @property
    def category(self) -> str:
        return "merger"

    @property
    def type(self) -> str:
        return "run"

    @property
    def inputs(self) -> Dict[str, str]:
        return {}

    @property
    def outputs(self) -> Dict[str, str]:
        return {"run": "int"}

    @property
    def properties(self) -> Dict[str, str]:
        return {"graw": "str", "run": "int"}

    @property
    def parameters_model(self) -> Type[BaseModel]:
        return CheckGrawEventIdParameters

    def execute(self, **kwargs: Any) -> List[Any]:
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