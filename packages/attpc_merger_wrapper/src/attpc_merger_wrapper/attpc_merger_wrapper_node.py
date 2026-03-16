"""ATTPC merger workflow node."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from atflow.node import Node
from atflow.node_manager import auto_register_node

from .api import merge_attpc

class AttpcMergerParameters(BaseModel):
    model_config = ConfigDict(extra="ignore")

    execution_id: str
    task_id: int
    workspace: str
    graw: str
    evt: str
    map: str
    run: int


@auto_register_node
class AttpcMergerNode(Node):
    _name = "attpc_merger"
    _version = "1.1.1"
    _description = "Merge graw and evt files into hdf5 file through libattpc_merger"
    _category = "merger"
    _type = "batch"
    _inputs = {}
    _outputs = {}
    _properties = {
        "graw": "str",
        "evt": "str",
        "map": "str",
    }
    _parameters = AttpcMergerParameters

    def execute(self, **kwargs: Any) -> list[Any]:
        result = merge_attpc(**kwargs)
        return [result]
