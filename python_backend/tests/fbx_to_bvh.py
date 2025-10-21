import bpy
import numpy as np
import os
import sys

# Usage:
#   blender -b -P ./fbx_to_bvh.py -- [fbx_directory]
# Example:
#   blender -b -P ./fbx_to_bvh.py -- ./fbx

import contextlib
import io

@contextlib.contextmanager
def suppress_bpy_warnings():
    """Temporarily suppress Blender FBX warnings."""
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    try:
        yield
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

def clear_scene():
    """Remove all existing objects, meshes, and armatures to avoid conflicts."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.outliner.orphans_purge(do_recursive=True)


def fbx_to_bvh(fbx_dir: str, filename: str):
    """Convert a single FBX file to BVH."""
    src_path = os.path.join(fbx_dir, filename)
    dst_path = os.path.splitext(src_path)[0] + ".bvh"

    print(f"Processing: {src_path}")

    clear_scene()


    try:
        with suppress_bpy_warnings():
            bpy.ops.import_scene.fbx(filepath=src_path)
        # bpy.ops.import_scene.fbx(filepath=src_path)
    except Exception as e:
        print(f"❌ Failed to import {filename}: {e}")
        return

    # Find frame range
    frame_start, frame_end = sys.maxsize, -sys.maxsize
    for action in bpy.data.actions:
        start, end = action.frame_range
        frame_start = min(frame_start, int(start))
        frame_end = max(frame_end, int(end))

    if frame_end < 1:
        frame_end = 60  # fallback

    # Export as BVH
    try:
        bpy.ops.export_anim.bvh(
            filepath=dst_path,
            frame_start=frame_start,
            frame_end=frame_end,
            root_transform_only=True
        )
        print(f"✅ Exported: {dst_path}")
    except Exception as e:
        print(f"❌ Failed to export BVH for {filename}: {e}")
    finally:
        # Cleanup
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        bpy.ops.outliner.orphans_purge(do_recursive=True)


def batch_convert(base_dir: str):
    """Recursively convert all FBX files under base_dir to BVH."""
    if not os.path.isdir(base_dir):
        print(f"Error: Directory not found — {base_dir}")
        return

    for root, _, files in os.walk(base_dir):
        for file in sorted(files):
            if file.lower().endswith(".fbx"):
                fbx_to_bvh(root, file)


if __name__ == "__main__":
    # Allow command-line override: blender -b -P script.py -- <dir>
    if "--" in sys.argv:
        data_path = sys.argv[sys.argv.index("--") + 1]
    else:
        data_path = "./fbx"

    batch_convert(os.path.abspath(data_path))
