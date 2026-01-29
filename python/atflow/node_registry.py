from typing import Type, Dict, Optional
from dataclasses import dataclass, field
from pydantic import BaseModel

@dataclass
class NodeInfo:
	inputs: Optional[Dict[str, str]] = None
	outputs: Optional[Dict[str, str]] = None
	properties: Optional[Dict[str, str]] = None
	parameters: Optional[type[BaseModel]] = None

@dataclass
class RegistryEntry:
	node_class: Type
	info: NodeInfo

class NodeRegistry:
	_registry: Dict[str, RegistryEntry] = {}

	@classmethod
	def register(cls, name: str, info: NodeInfo):
		def decorator(node_class: Type):
			cls._registry[name] = RegistryEntry(
				node_class=node_class,
				info=info
			)
			return cls
		return decorator

	@classmethod
	def dispatch(
		cls,
		name:str,
		execution_id: str,
		task_id: int,
		environment: dict,
		inputs: dict,
		properties: dict,
	):
		# get entry
		entry = cls._registry.get(name)
		if not entry:
			raise ValueError(f"Node {name} is not registered.")
		info = entry.info

		# print(environment, inputs, properties)

		# combine data
		params = {
			"execution_id": execution_id,
			"task_id": task_id,
			**environment,
			**inputs,
			**properties
		}
		if info.parameters:
			try:
				execution_kwargs = info.parameters(**params).model_dump()
			except Exception as e:
				raise ValueError(f"Parameters validation failed for {name}: {e}")
		else:
			execution_kwargs = params

		# execute node
		instance = entry.node_class()
		return instance.execute(**execution_kwargs)