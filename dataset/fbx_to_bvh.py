import bpy
import numpy as np
import os
import sys
import contextlib
import io

# Usage:
#   blender -b -P ./fbx_to_bvh.py -- [fbx_directory] [output_directory]
# Example:
#   blender -b -P ./fbx_to_bvh.py -- ./mixamo_downloads ./mixamo_bvh

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

def fbx_to_bvh(src_path: str, dst_path: str):
    """Convert a single FBX file to BVH."""
    if os.path.exists(dst_path):
        print(f"Skipping: {dst_path} (already exists)")
        return

    print(f"Processing: {src_path}")
    clear_scene()

    try:
        with suppress_bpy_warnings():
            bpy.ops.import_scene.fbx(filepath=src_path)
    except Exception as e:
        print(f"❌ Failed to import {src_path}: {e}")
        return

    # Find frame range
    frame_start, frame_end = sys.maxsize, -sys.maxsize
    has_action = False
    for action in bpy.data.actions:
        start, end = action.frame_range
        frame_start = min(frame_start, int(start))
        frame_end = max(frame_end, int(end))
        has_action = True

    if not has_action or frame_end < 1:
        frame_start = 0
        frame_end = 60  # fallback

    # Ensure we have an armature selected
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE']
    if not armatures:
        print(f"❌ No armature found in {src_path}")
        return
    
    # Select the first armature (usually only one in Mixamo)
    bpy.context.view_layer.objects.active = armatures[0]
    armatures[0].select_set(True)

    # Export as BVH
    try:
        # Create destination directory if it doesn't exist
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        
        bpy.ops.export_anim.bvh(
            filepath=dst_path,
            frame_start=frame_start,
            frame_end=frame_end,
            root_transform_only=True
        )
        print(f"✅ Exported: {dst_path}")
    except Exception as e:
        print(f"❌ Failed to export BVH for {src_path}: {e}")
    finally:
        # Cleanup
        clear_scene()

def batch_convert(base_dir: str, output_base_dir: str):
    """Recursively convert all FBX files under base_dir to BVH, maintaining structure."""
    if not os.path.isdir(base_dir):
        print(f"Error: Directory not found — {base_dir}")
        return

    for root, _, files in os.walk(base_dir):
        # Calculate relative path to maintain structure
        rel_path = os.path.relpath(root, base_dir)
        target_dir = os.path.join(output_base_dir, rel_path)
        
        for file in sorted(files):
            if file.lower().endswith(".fbx"):
                src_path = os.path.join(root, file)
                # Output filename is same but with .bvh extension
                dst_filename = os.path.splitext(file)[0] + ".bvh"
                dst_path = os.path.join(target_dir, dst_filename)
                fbx_to_bvh(src_path, dst_path)

if __name__ == "__main__":
    # Allow command-line override: blender -b -P script.py -- <input_dir> [output_dir]
    args = []
    if "--" in sys.argv:
        args = sys.argv[sys.argv.index("--") + 1:]
    
    if len(args) >= 2:
        input_path = args[0]
        output_path = args[1]
    elif len(args) == 1:
        input_path = args[0]
        output_path = os.path.join(os.path.dirname(input_path), "mixamo_bvh")
    else:
        input_path = "./fbx"
        output_path = "./bvh"

    print(f"Input: {os.path.abspath(input_path)}")
    print(f"Output: {os.path.abspath(output_path)}")
    
    batch_convert(os.path.abspath(input_path), os.path.abspath(output_path))
