from ..node_registry import NodeRegistry, NodeInfo
from typing import List
from pydantic import BaseModel

class ConstIntProperties(BaseModel):
	value: List[int]

class ConstIntParameters(ConstIntProperties):
	task_id: int

@NodeRegistry.register(
	name="const_int",
	info=NodeInfo(
		inputs=[],
		outputs=["ARRAY[INT]"],
		properties=ConstIntProperties,
		parameters=ConstIntParameters,
	)
)
class ConstIntNode():
	def execute(self, task_id, value):
		return [value]