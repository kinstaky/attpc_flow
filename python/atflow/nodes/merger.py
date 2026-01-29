from pydantic import BaseModel

from .. import check_graw_event_id
from ..node_registry import NodeRegistry, NodeInfo

class CheckGrawEventIdParameters(BaseModel):
	execution_id: str
	task_id: int
	workspace_dir: str
	graw_dir: str
	run: int

@NodeRegistry.register(
	name="check_graw_event_id",
	info=NodeInfo(
		inputs=None,
		outputs={"run": "int"},
		properties={"graw_dir": "str", "run": "int"},
		parameters=CheckGrawEventIdParameters,
	)
)
class CheckGrawEventIdNode():
	def execute(self, execution_id, task_id, workspace_dir, graw_dir, run):
		result = check_graw_event_id(
			execution_id=execution_id,
			task_id=task_id,
			graw_dir=graw_dir,
			workspace_dir=workspace_dir,
			run=run,
		)
		if result:
			return [run]
		else:
			return [None]