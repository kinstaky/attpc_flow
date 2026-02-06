from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class WorkflowRun(BaseModel):
	runs: List[int] = Field(default_factory=list)
	tags: List[str] = Field(default_factory=list)

class WorkflowNode(BaseModel):
	id: int
	name: str
	position: Dict[str, float]
	inputs: List[Dict[str, Any]] = Field(default_factory=list)
	outputs: List[Dict[str, Any]] = Field(default_factory=list)
	properties: List[Dict[str, Any]] = Field(default_factory=list)

class WorkflowLink(BaseModel):
	id: int
	source: int
	sourceHandle: str
	target: int
	targetHandle: str

class Workflow(BaseModel):
	name: str
	workspace: Optional[str] = None
	workers: int = 2
	run: WorkflowRun
	nodes: List[WorkflowNode] = Field(default_factory=list)
	links: List[WorkflowLink] = Field(default_factory=list)
	last_node: int = Field(alias="lastNode")
	last_link: int = Field(alias="lastLink")