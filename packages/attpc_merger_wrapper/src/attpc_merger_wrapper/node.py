"""ATTPC merger node wrapper."""

from email.policy import default
from pathlib import Path
from typing import Any, Dict, List, Type
import logging
from datetime import datetime

from pydantic import BaseModel

from atflow.node import Node
from atflow.node_manager import auto_register_node
from atflow.run_tag_db import RunTagDB

from ._lib import merge_attpc


class AttpcMergerParameters(BaseModel):
    execution_id: str
    task_id: int
    workspace: str
    graw: str
    evt: str
    map: str
    run: int

@auto_register_node
class AttpcMergerNode(Node):
    @property
    def name(self) -> str:
        return "attpc_merger"

    @property
    def version(self) -> str:
        return "1.1.1"

    @property
    def description(self) -> str:
        return "Merge graw and evt files into hdf5 file through libattpc_merger"

    @property
    def category(self) -> str:
        return "merger"

    @property
    def inputs(self) -> Dict[str, str]:
        return {}

    @property
    def outputs(self) -> Dict[str, str]:
        return {"run": "int"}

    @property
    def properties(self) -> Dict[str, str]:
        return {
            "graw": "str",
            "evt": "str",
            "map": "str",
            "run": "int",
        }

    @property
    def parameters_model(self) -> Type[BaseModel]:
        return AttpcMergerParameters

    def execute(self, **kwargs: Any) -> List[Any]:
        run = kwargs["run"]
        workspace = kwargs["workspace"]
        db = RunTagDB()
        evtid_tag = db.get_run_tag(Path(workspace), run, "evtid")
        allowed_tags = {"missing", "pass", "incomplete"}
        if evtid_tag is None or evtid_tag not in allowed_tags:
            db.set_run_tag(workspace=workspace, run=run, tag=f"merger:unchecked", default_value="unmerged")
            return [None]
        merger_tag = db.get_run_tag(Path(workspace), run, "merger")

        # Log to the same file as Rust merger
        log_path = Path(workspace) / "log" / "attpc_merger" / f"{run}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        with open(log_path, "w") as f:
            f.write(
                f"[{timestamp}] - [Python] - [INFO] - Pre-merge check: evtid tag is '{evtid_tag}'\n"
                f"[{timestamp}] - [Python] - [INFO] - Pre-merge check: merger tag is '{merger_tag}'\n"
            )

        result = merge_attpc(
            execution_id=kwargs["execution_id"],
            task_id=kwargs["task_id"],
            workspace=workspace,
            graw=kwargs["graw"],
            evt=kwargs["evt"],
            map=kwargs["map"],
            run=run,
            merger_tag=merger_tag,
        )
        db.set_run_tag(workspace=workspace, run=run, tag=f"merger:{result}", default_value="unmerged")

        return [run] if result == "success" else [None]
