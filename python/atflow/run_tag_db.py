"""
Run tag database utilities.
Initialize run tag database from CSV and provide methods for querying runs by tags.
"""

import polars as pl
import os
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
import time

@dataclass
class RunDBInfo:
    db_path: Path
    df: pl.DataFrame
    last_modified: float


class RunTagDB:
    """Database for a single workspace."""
    def __init__(self):
        self._db_map: Dict[str, RunDBInfo] = {}

    def _load(self, workspace: Path) -> pl.DataFrame:
        path = str(workspace)
        """Load the database from parquet file with auto-reload on modification."""
        if path not in self._db_map:
            self._db_map[path] = RunDBInfo(
                db_path=Path(path) / "run/run_tags.parquet",
                df=None,
                last_modified=None
            )
        db_info = self._db_map[path]
        if db_info.df is None:
            if db_info.db_path.exists():
                db_info.df = pl.read_parquet(db_info.db_path)
                db_info.last_modified = db_info.db_path.stat().st_mtime
            elif (workspace / "run/run.csv").exists():
                self.init_from_csv(workspace)
            else:
                db_info.df = pl.DataFrame({
                    "run": pl.Series([], dtype=pl.Int64),
                    "start": pl.Series([], dtype=pl.Datetime),
                    "stop": pl.Series([], dtype=pl.Datetime),
                    "duration": pl.Series([], dtype=pl.Duration),
                    "experiment": pl.Series([], dtype=pl.Utf8),
                })
                self._save(workspace)
        else:
            current_mtime = db_info.db_path.stat().st_mtime
            if current_mtime > db_info.last_modified:
                db_info.df = pl.read_parquet(db_info.db_path)
                db_info.last_modified = current_mtime
        return self._db_map[path].df

    def _save(self, workspace: Path):
        """Save the database to parquet file."""
        if str(workspace) not in self._db_map:
            return
        db_info = self._db_map[str(workspace)]
        if db_info.df is not None:
            # Ensure data directory exists
            db_info.db_path.parent.mkdir(parents=True, exist_ok=True)
            db_info.df.write_parquet(db_info.db_path)
            db_info.last_modified = db_info.db_path.stat().st_mtime

    def refresh(self, workspace: Path):
        """Force refresh the database from disk."""
        self._load(workspace)

    def init_from_csv(self, workspace: Path):
        """
        Initialize database from CSV file.
        """
        csv_path = workspace / "run/run.csv"
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        df = pl.read_csv(csv_path)
        df = df.filter(pl.col("run").is_not_null())

        # Replace "#N/A" and empty strings with null
        df = df.with_columns([
            pl.col("date").fill_null(""),
            pl.col("start").fill_null(""),
            pl.col("stop").fill_null(""),
        ])
        df = df.with_columns([
            pl.col("date").replace("#N/A", None).replace("", None),
            pl.col("start").replace("#N/A", None).replace("", None),
            pl.col("stop").replace("#N/A", None).replace("", None),
        ])

        # Parse date and time to start and stop columns
        df = df.with_columns([
            pl.concat_str(["date", "start"], separator=" ")
                .str.strptime(pl.Datetime, "%m/%d/%Y %H:%M", strict=False)
                .alias("start"),
            pl.concat_str(["date", "stop"], separator=" ")
                .str.strptime(pl.Datetime, "%m/%d/%Y %H:%M", strict=False)
                .alias("stop"),
        ])
        # Handle overnight runs (stop < start)
        df = df.with_columns([
            pl.when(pl.col("stop") < pl.col("start"))
            .then(pl.col("stop") + pl.duration(days=1))
            .otherwise(pl.col("stop"))
            .alias("stop")
        ])

        df = df.with_columns([
            (pl.col("stop") - pl.col("start")).alias("duration")
        ])

        # Select only the required columns
        df = df.select(["run", "start", "stop", "duration", "experiment"])

        # Store in db_map
        path = str(workspace)
        self._db_map[path] = RunDBInfo(
            db_path=Path(path) / "run/run_tags.parquet",
            df=df,
            last_modified=None
        )
        self._save(workspace)


    def list_runs(self, workspace) -> List[int]:
        """Return list of all run numbers."""
        df = self._load(workspace)
        return df["run"].to_list()

    def list_tag_groups(self, workspace: Path) -> List[str]:
        """Return list of all tag group names (column names except 'run', 'start', 'stop', 'duration')."""
        df = self._load(workspace)
        exclude_cols = {"run", "start", "stop", "duration"}
        return [col for col in df.columns if col not in exclude_cols]

    def list_tags(self, workspace: Path, tag_group: str) -> List[str]:
        """Return list of unique tag values for a given tag group."""
        df = self._load(workspace)
        if tag_group not in df.columns:
            return []
        return df[tag_group].unique().drop_nulls().to_list()

    def list_all_tags(self, workspace: Path) -> Dict[str, List[str]]:
        """Return all tag groups with their unique values."""
        df = self._load(workspace)
        exclude_cols = {"run", "start", "stop", "duration"}
        return {col: df[col].unique().drop_nulls().to_list() for col in df.columns if col not in exclude_cols}

    def list_runs_by_tag(self, workspace: Path, tag: str) -> List[int]:
        """Return run numbers that have the specified tag.

        Args:
            workspace: Workspace path
            tag: Tag in format 'tag_group:tag_value'
        """
        if ':' not in tag:
            raise ValueError(f"Invalid tag format: {tag}. Expected format: 'tag_group:tag_value'")

        tag_group, tag_value = tag.split(':', 1)
        df = self._load(workspace)
        if tag_group not in df.columns:
            return []
        filtered = df.filter(pl.col(tag_group) == tag_value)
        return filtered["run"].to_list()

    def filter_runs(
        self,
        workspace: Path,
        runs: Optional[List[int]] = None,
        tags: Optional[List[str]] = None
    ) -> List[int]:
        """
        Filter runs by tags.

        Args:
            workspace: Workspace path
            runs: Optional list of run numbers to filter. If None, use all runs.
            tags: List of tags in format 'tag_group:tag_value' to filter by.
                  Multiple tags use AND logic.

        Returns:
            List of run numbers matching all specified criteria.
        """
        df = self._load(workspace)

        if runs is not None:
            df = df.filter(pl.col("run").is_in(runs))

        if tags:
            for tag in tags:
                if ':' not in tag:
                    raise ValueError(f"Invalid tag format: {tag}. Expected format: 'tag_group:tag_value'")
                tag_group, tag_value = tag.split(':', 1)
                if tag_group in df.columns:
                    df = df.filter(pl.col(tag_group) == tag_value)

        return df["run"].to_list()

    def get_run_info(self, workspace: Path, run: int) -> Optional[Dict]:
        """Get all information for a specific run."""
        df = self._load(workspace)
        filtered = df.filter(pl.col("run") == run)
        if len(filtered) == 0:
            return None
        return filtered.to_dicts()[0]

    def get_runs_info(self, workspace: Path, runs: Optional[List[int]] = None) -> List[Dict]:
        """Get information for multiple runs."""
        df = self._load(workspace)
        if runs is not None:
            df = df.filter(pl.col("run").is_in(runs))
        return df.to_dicts()

    def to_csv(self, workspace: Path, output_path: Optional[Path] = None) -> str:
        """Export database to CSV format. Returns CSV string if no path provided."""
        df = self._load(workspace)
        if output_path:
            df.write_csv(output_path)
            return str(output_path)
        return df.write_csv()

    def add_tag_group(self, workspace: Path, name: str, default_value: str = ""):
        """Add a new tag group column."""
        df = self._load(workspace)
        if name not in df.columns:
            self._df = df.with_columns(pl.lit(default_value).alias(name))
            self._save(workspace)

    def set_run_tag(self, workspace: Path, run: int, tag: str):
        """Set a tag value for a specific run.

        Args:
            workspace: Workspace path
            run: Run number
            tag: Tag in format 'tag_group:tag_value'
        """
        if ':' not in tag:
            raise ValueError(f"Invalid tag format: {tag}. Expected format: 'tag_group:tag_value'")

        tag_group, tag_value = tag.split(':', 1)
        df = self._load(workspace)
        if tag_group not in df.columns:
            self.add_tag_group(workspace, tag_group)
            df = self._load(workspace)

        self._df = df.with_columns(
            pl.when(pl.col("run") == run)
            .then(pl.lit(tag_value))
            .otherwise(pl.col(tag_group))
            .alias(tag_group)
        )
        self._save(workspace)