"""
BVH → FBX converter (Blender-only, external process)

- No bpy import
- Safe for FastAPI / Poetry / Uvicorn
- Uses absolute paths to avoid CWD issues
"""

import subprocess
import sys
from pathlib import Path
from typing import Union

import config
BLENDER_PATH = config.BLENDER_PATH

# Blender-side script (runs INSIDE Blender)
BLENDER_SCRIPT = (
    Path(__file__).parent / "convert_bvh_to_fbx.py"
).resolve()


def _resolve_path(path: Union[str, Path]) -> Path:
    """
    Resolve to absolute path (critical for cross-process safety)
    """
    return Path(path).expanduser().resolve()


def convert_bvh_to_fbx(bvh_path: str, fbx_path: str) -> bool:
    """
    Convert BVH → FBX using an external Blender process.

    This function is SAFE to call from FastAPI.
    It does NOT require bpy in the Python environment.

    Args:
        bvh_path: input .bvh path (relative or absolute)
        fbx_path: output .fbx path (relative or absolute)

    Returns:
        True if conversion successful, False otherwise

    Raises:
        RuntimeError if Blender fails or FBX is not created
    """
    bvh_path = _resolve_path(bvh_path)
    fbx_path = _resolve_path(fbx_path)

    # Ensure output directory exists
    fbx_path.parent.mkdir(parents=True, exist_ok=True)

    if not bvh_path.exists():
        raise FileNotFoundError(f"BVH file not found: {bvh_path}")

    if not BLENDER_SCRIPT.exists():
        raise FileNotFoundError(f"Blender script not found: {BLENDER_SCRIPT}")

    cmd = [
        BLENDER_PATH,
        "--background",
        "--factory-startup",
        "--python",
        str(BLENDER_SCRIPT),
        "--",
        str(bvh_path),
        str(fbx_path),
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Blender process failed
    if result.returncode != 0:
        print("========== Blender STDOUT ==========")
        print(result.stdout)
        print("========== Blender STDERR ==========", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise RuntimeError("Blender BVH → FBX conversion failed")

    # Final safety check (this is what fixes your FastAPI crash)
    if not fbx_path.exists():
        raise RuntimeError(
            f"FBX not created by Blender: {fbx_path}"
        )

    return True
