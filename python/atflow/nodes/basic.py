"""Basic nodes for ATTPC Flow."""

from typing import Any, Dict, List, Type

from pydantic import BaseModel

from ..node import Node
from ..node_manager import auto_register_node


class ConstIntParameters(BaseModel):
    value: int


@auto_register_node
class ConstIntNode(Node):
    @property
    def name(self) -> str:
        return "const_int"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Outputs a constant integer value"

    @property
    def category(self) -> str:
        return "basic"

    @property
    def type(self) -> str:
        return "instant"

    @property
    def inputs(self) -> Dict[str, str]:
        return {}

    @property
    def outputs(self) -> Dict[str, str]:
        return {"value": "int"}

    @property
    def properties(self) -> Dict[str, str]:
        return {"value": "int"}

    @property
    def parameters_model(self) -> Type[BaseModel]:
        return ConstIntParameters

    def execute(self, **kwargs: Any) -> List[Any]:
        value = kwargs.get("value")
        return [value]


class ConstListIntParameters(BaseModel):
    value: List[int]


@auto_register_node
class ConstListIntNode(Node):
    @property
    def name(self) -> str:
        return "const_list_int"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Outputs a constant list of integers"

    @property
    def category(self) -> str:
        return "basic"

    @property
    def type(self) -> str:
        return "instant"

    @property
    def inputs(self) -> Dict[str, str]:
        return {}

    @property
    def outputs(self) -> Dict[str, str]:
        return {"value": "int[]"}

    @property
    def properties(self) -> Dict[str, str]:
        return {"value": "int[]"}

    @property
    def parameters_model(self) -> Type[BaseModel]:
        return ConstListIntParameters

    def execute(self, **kwargs: Any) -> List[Any]:
        value = kwargs.get("value")
        return [value]


class LoadRunParameters(BaseModel):
    run: int


@auto_register_node
class LoadRunNode(Node):
    @property
    def name(self) -> str:
        return "load_run"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Loads a single run"

    @property
    def category(self) -> str:
        return "basic"

    @property
    def type(self) -> str:
        return "instant"

    @property
    def inputs(self) -> Dict[str, str]:
        return {}

    @property
    def outputs(self) -> Dict[str, str]:
        return {"run": "int"}

    @property
    def properties(self) -> Dict[str, str]:
        return {}

    @property
    def parameters_model(self) -> Type[BaseModel]:
        return LoadRunParameters

    def execute(self, **kwargs: Any) -> List[Any]:
        run = kwargs.get("run")
        return [run]


class LoadRunListParameters(BaseModel):
    run_list: List[int]
    run: int


@auto_register_node
class LoadRunListNode(Node):
    @property
    def name(self) -> str:
        return "load_run_list"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Loads a list of runs, filtering by a specific run value"

    @property
    def category(self) -> str:
        return "basic"

    @property
    def type(self) -> str:
        return "instant"

    @property
    def inputs(self) -> Dict[str, str]:
        return {}

    @property
    def outputs(self) -> Dict[str, str]:
        return {"run": "int[]"}

    @property
    def properties(self) -> Dict[str, str]:
        return {}

    @property
    def parameters_model(self) -> Type[BaseModel]:
        return LoadRunListParameters

    def execute(self, **kwargs: Any) -> List[Any]:
        run_list = kwargs.get("run_list")
        run = kwargs.get("run")
        if run == run_list[0]:
            return [run_list]
        else:
            return [None]