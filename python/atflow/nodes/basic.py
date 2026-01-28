from ..node_registry import NodeRegistry, NodeInfo
from typing import List
from pydantic import BaseModel


class ConstIntParameters(BaseModel):
	value: int

@NodeRegistry.register(
	name="const_int",
	info=NodeInfo(
		inputs=None,
		outputs={"value": "int"},
		properties={"value": "int"},
		parameters=ConstIntParameters,
	)
)
class ConstIntNode():
	def execute(self, value):
		return [value]



class ConstListIntParameters(BaseModel):
	value: List[int]

@NodeRegistry.register(
	name="const_list_int",
	info=NodeInfo(
		inputs=None,
		outputs={"value": "int[]"},
		properties={"value": "int[]"},
		parameters=ConstListIntParameters,
	)
)
class ConstListIntNode():
	def execute(self, value):
		return value



class LoadRunParameters(BaseModel):
	run: int

@NodeRegistry.register(
	name="load_run",
	info=NodeInfo(
		inputs=None,
		outputs={"run": "int"},
		parameters=LoadRunParameters,
	)
)
class LoadRunNode():
	def execute(self, run):
		return run



class LoadRunListParameters(BaseModel):
	run_list: List[int]
	run: int

@NodeRegistry.register(
	name="load_run_list",
	info=NodeInfo(
		inputs=None,
		outputs={"run": "int[]"},
		parameters=LoadRunListParameters,
	)
)
class LoadRunListNode():
	def execute(self, run_list, run):
		if run == run_list[0]:
			return run_list
		else:
			return None