"""
Run tag database utilities.
Initialize run tag database from CSV and provide methods for querying runs by tags.
"""

import csv
import sqlite3
from io import StringIO
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta


# Columns that are part of the core schema, not user-defined tag groups.
_CORE_COLUMNS = {"run", "start", "stop", "duration"}


class RunTagDB:
    """Database for a single workspace backed by SQLite."""

    def __init__(self):
        self._conn_map: Dict[str, sqlite3.Connection] = {}

    def _db_path(self, workspace: Path) -> Path:
        return Path(workspace) / "run/run_tags.db"

    def _conn(self, workspace: Path) -> sqlite3.Connection:
        """Return (and cache) a sqlite3 connection for *workspace*."""
        key = str(workspace)
        if key not in self._conn_map:
            db_path = self._db_path(workspace)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            self._conn_map[key] = conn
            self._ensure_table(conn)
            # Auto-import from CSV when the table is empty and a CSV exists
            if self._row_count(conn) == 0 and (workspace / "run/run.csv").exists():
                self._import_csv(conn, workspace / "run/run.csv")
        return self._conn_map[key]

    @staticmethod
    def _ensure_table(conn: sqlite3.Connection):
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run     INTEGER PRIMARY KEY,
                start   TEXT,
                stop    TEXT,
                duration TEXT,
                experiment TEXT
            )
        """)
        conn.commit()

    @staticmethod
    def _row_count(conn: sqlite3.Connection) -> int:
        return conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]

    # ------------------------------------------------------------------
    # CSV import
    # ------------------------------------------------------------------
    def _import_csv(self, conn: sqlite3.Connection, csv_path: Path):
        """Populate the database from a CSV file."""
        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                run_val = row.get("run")
                if run_val is None or run_val.strip() == "":
                    continue
                run = int(run_val)

                date_s = row.get("date", "").strip()
                start_s = row.get("start", "").strip()
                stop_s = row.get("stop", "").strip()
                experiment = row.get("experiment")

                # Replace "#N/A" / empty with None
                date_s = None if date_s in ("#N/A", "") else date_s
                start_s = None if start_s in ("#N/A", "") else start_s
                stop_s = None if stop_s in ("#N/A", "") else stop_s

                start_dt: Optional[datetime] = None
                stop_dt: Optional[datetime] = None
                duration_s: Optional[str] = None

                if date_s and start_s:
                    try:
                        start_dt = datetime.strptime(f"{date_s} {start_s}", "%m/%d/%Y %H:%M")
                    except ValueError:
                        pass
                if date_s and stop_s:
                    try:
                        stop_dt = datetime.strptime(f"{date_s} {stop_s}", "%m/%d/%Y %H:%M")
                    except ValueError:
                        pass

                # Handle overnight runs
                if start_dt and stop_dt and stop_dt < start_dt:
                    stop_dt += timedelta(days=1)

                if start_dt and stop_dt:
                    duration_s = str(stop_dt - start_dt)

                conn.execute(
                    "INSERT OR REPLACE INTO runs (run, start, stop, duration, experiment) VALUES (?, ?, ?, ?, ?)",
                    (
                        run,
                        start_dt.isoformat() if start_dt else None,
                        stop_dt.isoformat() if stop_dt else None,
                        duration_s,
                        experiment,
                    ),
                )
        conn.commit()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _columns(self, conn: sqlite3.Connection) -> List[str]:
        """Return the column names of the runs table."""
        cur = conn.execute("PRAGMA table_info(runs)")
        return [row[1] for row in cur.fetchall()]

    def _rows_to_dicts(self, rows) -> List[Dict]:
        if not rows:
            return []
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def refresh(self, workspace: Path) -> int:
        """Force refresh: close cached connection so next access re-opens the DB.

        Returns the number of rows in the database.
        """
        key = str(workspace)
        if key in self._conn_map:
            self._conn_map[key].close()
            del self._conn_map[key]
        conn = self._conn(workspace)
        return self._row_count(conn)

    def init_from_csv(self, workspace: Path):
        """
        Initialize database from CSV file.
        """
        csv_path = workspace / "run/run.csv"
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        conn = self._conn(workspace)
        conn.execute("DELETE FROM runs")
        self._import_csv(conn, csv_path)

    def list_runs(self, workspace) -> List[int]:
        """Return list of all run numbers."""
        conn = self._conn(workspace)
        rows = conn.execute("SELECT run FROM runs ORDER BY run").fetchall()
        return [r[0] for r in rows]

    def list_tag_groups(self, workspace: Path) -> List[str]:
        """Return list of all tag group names (column names except 'run', 'start', 'stop', 'duration')."""
        conn = self._conn(workspace)
        return [c for c in self._columns(conn) if c not in _CORE_COLUMNS]

    def list_tags(self, workspace: Path, tag_group: str) -> List[str]:
        """Return list of unique tag values for a given tag group."""
        conn = self._conn(workspace)
        if tag_group not in self._columns(conn):
            return []
        rows = conn.execute(
            f"SELECT DISTINCT [{tag_group}] FROM runs WHERE [{tag_group}] IS NOT NULL"
        ).fetchall()
        return [r[0] for r in rows]

    def list_all_tags(self, workspace: Path) -> Dict[str, List[str]]:
        """Return all tag groups with their unique values."""
        conn = self._conn(workspace)
        cols = [c for c in self._columns(conn) if c not in _CORE_COLUMNS]
        result: Dict[str, List[str]] = {}
        for col in cols:
            rows = conn.execute(
                f"SELECT DISTINCT [{col}] FROM runs WHERE [{col}] IS NOT NULL"
            ).fetchall()
            result[col] = [r[0] for r in rows]
        return result

    def list_runs_by_tag(self, workspace: Path, tag: str) -> List[int]:
        """Return run numbers that have the specified tag.

        Args:
            workspace: Workspace path
            tag: Tag in format 'tag_group:tag_value'
        """
        if ':' not in tag:
            raise ValueError(f"Invalid tag format: {tag}. Expected format: 'tag_group:tag_value'")

        tag_group, tag_value = tag.split(':', 1)
        conn = self._conn(workspace)
        if tag_group not in self._columns(conn):
            return []
        rows = conn.execute(
            f"SELECT run FROM runs WHERE [{tag_group}] = ? ORDER BY run", (tag_value,)
        ).fetchall()
        return [r[0] for r in rows]

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
        conn = self._conn(workspace)
        clauses: List[str] = []
        params: List = []

        if runs is not None:
            placeholders = ",".join("?" for _ in runs)
            clauses.append(f"run IN ({placeholders})")
            params.extend(runs)

        if tags:
            columns = self._columns(conn)
            for tag in tags:
                if ':' not in tag:
                    raise ValueError(f"Invalid tag format: {tag}. Expected format: 'tag_group:tag_value'")
                tag_group, tag_value = tag.split(':', 1)
                if tag_group in columns:
                    clauses.append(f"[{tag_group}] = ?")
                    params.append(tag_value)

        sql = "SELECT run FROM runs"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY run"
        rows = conn.execute(sql, params).fetchall()
        return [r[0] for r in rows]

    def get_run_info(self, workspace: Path, run: int) -> Optional[Dict]:
        """Get all information for a specific run."""
        conn = self._conn(workspace)
        row = conn.execute("SELECT * FROM runs WHERE run = ?", (run,)).fetchone()
        if row is None:
            return None
        return dict(row)

    def get_runs_info(self, workspace: Path, runs: Optional[List[int]] = None) -> List[Dict]:
        """Get information for multiple runs."""
        conn = self._conn(workspace)
        if runs is not None:
            placeholders = ",".join("?" for _ in runs)
            rows = conn.execute(
                f"SELECT * FROM runs WHERE run IN ({placeholders}) ORDER BY run", runs
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM runs ORDER BY run").fetchall()
        return self._rows_to_dicts(rows)

    def to_csv(self, workspace: Path, output_path: Optional[Path] = None) -> str:
        """Export database to CSV format. Returns CSV string if no path provided."""
        conn = self._conn(workspace)
        columns = self._columns(conn)
        rows = conn.execute("SELECT * FROM runs ORDER BY run").fetchall()

        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow(columns)
        for row in rows:
            writer.writerow(list(row))

        csv_text = buf.getvalue()
        if output_path:
            output_path.write_text(csv_text)
            return str(output_path)
        return csv_text

    def add_tag_group(self, workspace: Path, name: str, default_value: str = ""):
        """Add a new tag group column."""
        conn = self._conn(workspace)
        if name not in self._columns(conn):
            conn.execute(f"ALTER TABLE runs ADD COLUMN [{name}] TEXT NOT NULL DEFAULT '{default_value}'")
            conn.commit()

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
        conn = self._conn(workspace)
        if tag_group not in self._columns(conn):
            self.add_tag_group(workspace, tag_group)

        conn.execute(f"UPDATE runs SET [{tag_group}] = ? WHERE run = ?", (tag_value, run))
        conn.commit()