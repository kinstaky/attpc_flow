"""ATTPC merger workflow node."""

from typing import Any, Dict, List, Type

from pydantic import BaseModel

from atflow.node import Node
from atflow.node_manager import auto_register_node

from .api import merge_attpc


class AttpcMergerParameters(BaseModel):
    execution_id: str
    task_id: int
    workspace: str
    graw: str
    evt: str
    map: str
    run: int

@auto_register_node
class AttpcMergerNode(Node):
    @property
    def name(self) -> str:
        return "attpc_merger"

    @property
    def version(self) -> str:
        return "1.1.1"

    @property
    def description(self) -> str:
        return "Merge graw and evt files into hdf5 file through libattpc_merger"

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
        return {
            "graw": "str",
            "evt": "str",
            "map": "str",
            "run": "int",
        }

    @property
    def parameters_model(self) -> Type[BaseModel]:
        return AttpcMergerParameters

    def execute(self, **kwargs: Any) -> List[Any]:
        result = merge_attpc(**kwargs)
        return [result]
