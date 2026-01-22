from pydantic import BaseModel

from .. import check_graw_event_id
from ..node_registry import NodeRegistry, NodeInfo

class CheckGrawEventIdParameters(BaseModel):
	task_id: int
	workspace_dir: str
	graw_dir: str
	run: int

@NodeRegistry.register(
	name="check_graw_event_id",
	info=NodeInfo(
		inputs=None,
		outputs={"result": "bool"},
		properties={"graw_dir": "str", "run": "int"},
		parameters=CheckGrawEventIdParameters,
	)
)
class CheckGrawEventIdNode():
	def execute(self, task_id, workspace_dir, graw_dir, run):
		result = check_graw_event_id(
			task_id=task_id,
			graw_dir=graw_dir,
			workspace_dir=workspace_dir,
			run=run,
		)
		return [result]