"""Setup script for ATTPC Flow frontend that builds with pnpm."""

import subprocess
import os
import sys
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py


class build_py(_build_py):
    """Custom build command that runs pnpm build first."""

    def run(self):
        """Run pnpm build then standard Python build."""
        # Build frontend first
        frontend_dir = Path(__file__).parent
        dist_dir = frontend_dir / "dist"

        # Only build if dist doesn't exist
        if not dist_dir.exists():
            print("Building frontend with pnpm...")
            try:
                result = subprocess.run(
                    ["pnpm", "build"],
                    cwd=str(frontend_dir),
                    capture_output=True,
                    text=True,
                    check=True
                )
                print("Frontend build completed successfully.")
            except subprocess.CalledProcessError as e:
                print(f"Frontend build failed: {e.stderr}", file=sys.stderr)
                raise RuntimeError(f"Frontend build failed: {e.stderr}")
            except FileNotFoundError:
                print("pnpm not found. Please install pnpm to build the frontend.", file=sys.stderr)
                raise RuntimeError("pnpm not found. Please install pnpm to build the frontend.")
        else:
            print("Frontend dist already exists, skipping build.")

        # Run standard build
        super().run()


# Include dist directory as package data
setup(
    cmdclass={"build_py": build_py},
    package_data={"": ["dist/**/*"]},
    include_package_data=True,
)
