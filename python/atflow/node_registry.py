from typing import Type, Dict, List, Optional
from dataclasses import dataclass, field
from pydantic import BaseModel

@dataclass
class NodeInfo:
	inputs: List[str] = field(default_factory=list)
	outputs: List[str] = field(default_factory=list)
	properties: Optional[type[BaseModel]] = None
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
		environment: dict,
		inputs: dict,
		properties: dict,
	):
		# get entry
		entry = cls._registry.get(name)
		if not entry:
			raise ValueError(f"Node {name} is not registered.")
		info = entry.info

		print(environment, inputs, properties)

		# validate properties
		if info.properties:
			try:
				validated_properties = info.properties(**properties).model_dump()
			except Exception as e:
				raise ValueError(f"Properties for node {name} are invalid: {e}")
		validated_properties = properties

		# combine data
		params = {**environment, **inputs, **validated_properties}
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