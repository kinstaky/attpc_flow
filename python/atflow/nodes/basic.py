"""Basic nodes for ATTPC Flow."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from ..node import Node
from ..node_manager import auto_register_node



class ConstIntParameters(BaseModel):
    model_config = ConfigDict(extra="ignore")

    value: int


@auto_register_node
class ConstIntNode(Node):
    _name = "const_int"
    _version = "1.0.0"
    _description = "Outputs a constant integer value."
    _category = "basic"
    _type = "instant"
    _inputs = {}
    _outputs = {"value": "int"}
    _properties = {"value": "int"}
    _parameters = ConstIntParameters

    def execute(self, **kwargs: Any) -> list[Any]:
        value = kwargs.get("value")
        return [value]


class ConstListIntParameters(BaseModel):
    model_config = ConfigDict(extra="ignore")

    value: list[int]


@auto_register_node
class ConstListIntNode(Node):
    _name = "const_list_int"
    _version = "1.0.0"
    _description = "Outputs a constant list of integers."
    _category = "basic"
    _type = "instant"
    _inputs = {}
    _outputs = {"value": "int[]"}
    _properties = {"value": "int[]"}
    _parameters = ConstListIntParameters

    def execute(self, **kwargs: Any) -> list[Any]:
        value = kwargs.get("value")
        return [value]