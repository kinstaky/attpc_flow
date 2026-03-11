"""High-level Python API for ATTPC merger execution."""

from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path

from atflow.progress.progress_store import progress_store
from atflow.run_tag_db import RunTagDB

try:
    from ._lib import merger_attpc_binding
except ImportError:
    # Compatibility with an unrebuilt local extension that still exports the old name.
    from ._lib import merge_attpc as merger_attpc_binding


def _write_premerge_log(
    *,
    log_path: Path,
    evtid_tag: str | None,
    merger_tag: str | None,
) -> None:
    """Write the Python-side pre-merge gate summary to the merger log."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    with log_path.open("w", encoding="utf-8") as handle:
        handle.write(
            f"[{timestamp}] - [Python] - [INFO] - Pre-merge check: evtid tag is '{evtid_tag}'\n"
            f"[{timestamp}] - [Python] - [INFO] - Pre-merge check: merger tag is '{merger_tag}'\n"
        )


def merge_attpc(
    *,
    execution_id: str,
    task_id: int,
    workspace: str,
    graw: str,
    evt: str,
    map: str,
    run: int,
) -> int | None:
    """Run the ATTPC merger with workflow-level gating and tag updates."""
    workspace_path = Path(workspace)
    db = RunTagDB()
    evtid_tag = db.get_run_tag(workspace_path, run, "evtid")
    allowed_tags = {"missing", "pass", "incomplete"}
    if evtid_tag is None or evtid_tag not in allowed_tags:
        db.set_run_tag(
            workspace=workspace_path,
            run=run,
            tag="merger:unchecked",
            default_value="unmerged",
        )
        progress_store.discard_task(execution_id, str(task_id))
        return None

    merger_tag = db.get_run_tag(workspace_path, run, "merger")
    _write_premerge_log(
        log_path=workspace_path / "log" / "attpc_merger" / f"{run}.log",
        evtid_tag=evtid_tag,
        merger_tag=merger_tag,
    )

    result = merger_attpc_binding(
        execution_id=execution_id,
        task_id=-1 if os.getenv("ATFLOW_NATIVE_PROGRESS", "1") == "0" else task_id,
        workspace=workspace,
        graw=graw,
        evt=evt,
        map=map,
        run=run,
        merger_tag=merger_tag,
    )
    db.set_run_tag(
        workspace=workspace_path,
        run=run,
        tag=f"merger:{result}",
        default_value="unmerged",
    )
    return run if result == "success" else None
