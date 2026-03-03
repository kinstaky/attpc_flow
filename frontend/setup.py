"""Setup script for ATTPC Flow frontend that builds with pnpm."""

import subprocess
import sys
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py


class build_py(_build_py):
    """Custom build command that runs pnpm build first."""

    @staticmethod
    def _iter_source_files(frontend_dir: Path):
        ignored_parts = {"node_modules", "dist", "__pycache__"}
        watched = [
            frontend_dir / "src",
            frontend_dir / "public",
            frontend_dir / "index.html",
            frontend_dir / "package.json",
            frontend_dir / "pnpm-lock.yaml",
            frontend_dir / "vite.config.mts",
            frontend_dir / "tsconfig.json",
            frontend_dir / "tsconfig.app.json",
            frontend_dir / "tsconfig.node.json",
        ]

        for path in watched:
            if not path.exists():
                continue
            if path.is_file():
                yield path
            else:
                for file in path.rglob("*"):
                    if (
                        file.is_file()
                        and not any(part in ignored_parts for part in file.parts)
                        and not any(part.endswith(".egg-info") for part in file.parts)
                    ):
                        yield file

    @staticmethod
    def _latest_mtime(path: Path) -> float:
        latest = 0.0
        for file in path.rglob("*"):
            if file.is_file():
                latest = max(latest, file.stat().st_mtime)
        return latest

    def _needs_build(self, frontend_dir: Path, dist_dir: Path) -> bool:
        if not dist_dir.exists():
            return True

        latest_dist_mtime = self._latest_mtime(dist_dir)
        if latest_dist_mtime == 0.0:
            return True

        latest_source_mtime = 0.0
        for source in self._iter_source_files(frontend_dir):
            latest_source_mtime = max(latest_source_mtime, source.stat().st_mtime)
            if latest_source_mtime > latest_dist_mtime:
                return True
        return False

    def run(self):
        """Run pnpm build then standard Python build."""
        frontend_dir = Path(__file__).parent
        dist_dir = frontend_dir / "dist"
        node_modules_dir = frontend_dir / "node_modules"

        if self._needs_build(frontend_dir, dist_dir):
            print("Frontend sources changed or dist is missing. Running pnpm build...")
            try:
                if not node_modules_dir.exists():
                    print("Installing frontend dependencies with pnpm...")
                    subprocess.run(
                        ["pnpm", "install", "--frozen-lockfile"],
                        cwd=str(frontend_dir),
                        check=True,
                    )

                subprocess.run(["pnpm", "build"], cwd=str(frontend_dir), check=True)
                print("Frontend build completed successfully.")
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Frontend build failed: {e}") from e
            except FileNotFoundError:
                print("pnpm not found. Please install pnpm to build the frontend.", file=sys.stderr)
                raise RuntimeError("pnpm not found. Please install pnpm to build the frontend.")
        else:
            print("Frontend dist is up to date. Skipping pnpm build.")

        super().run()


# Include dist directory as package data
setup(
    cmdclass={"build_py": build_py},
    package_data={"": ["dist/**/*"]},
    include_package_data=True,
)
