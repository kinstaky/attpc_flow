"""Merger nodes for ATTPC Flow."""

from typing import Any, Dict, List, Type

from pydantic import BaseModel

from attpc_flow_cpp import check_graw_event_id

from ..node import Node
from ..node_manager import auto_register_node


class CheckGrawEventIdParameters(BaseModel):
    execution_id: str
    task_id: int
    workspace_dir: str
    graw_dir: str
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
    def inputs(self) -> Dict[str, str]:
        return {}

    @property
    def outputs(self) -> Dict[str, str]:
        return {"run": "int"}

    @property
    def properties(self) -> Dict[str, str]:
        return {"graw_dir": "str", "run": "int"}

    @property
    def parameters_model(self) -> Type[BaseModel]:
        return CheckGrawEventIdParameters

    def execute(self, **kwargs: Any) -> List[Any]:
        execution_id = kwargs.get("execution_id")
        task_id = kwargs.get("task_id")
        workspace_dir = kwargs.get("workspace_dir")
        graw_dir = kwargs.get("graw_dir")
        run = kwargs.get("run")

        result = check_graw_event_id(
            execution_id=execution_id,
            task_id=task_id,
            graw_dir=graw_dir,
            workspace_dir=workspace_dir,
            run=run,
        )
        if result:
            return [run]
        else:
            return [None]