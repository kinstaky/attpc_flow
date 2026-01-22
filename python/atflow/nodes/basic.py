from ..node_registry import NodeRegistry, NodeInfo
from typing import List
from pydantic import BaseModel


class ConstIntParameters(BaseModel):
	task_id: int
	value: List[int]

@NodeRegistry.register(
	name="const_int",
	info=NodeInfo(
		inputs=None,
		outputs={"value": "int[]"},
		properties={"value": "int[]"},
		parameters=ConstIntParameters,
	)
)
class ConstIntNode():
	def execute(self, task_id, value):
		return [value]