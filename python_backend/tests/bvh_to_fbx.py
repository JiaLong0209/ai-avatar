import bpy
import sys
import os
import contextlib
import io

# ============================================================
# Helper: Suppress Blender console warnings (optional)
# ============================================================
@contextlib.contextmanager
def suppress_bpy_warnings():
    """Temporarily suppress Blender console warnings (FBX/BVH import)."""
    old_stdout, old_stderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
    try:
        yield
    finally:
        sys.stdout, sys.stderr = old_stdout, old_stderr


# ============================================================
# Helper: Parse CLI arguments
# Usage:
#   blender -b -P bvh_to_fbx.py -- input.bvh output.fbx
#   OR call convert_bvh_to_fbx(bvh_path, fbx_path) directly
# ============================================================
def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    if len(argv) < 2:
        print("Usage: blender -b -P bvh_to_fbx.py -- <input.bvh> <output.fbx>")
        print("OR call convert_bvh_to_fbx(bvh_path, fbx_path) directly")
        sys.exit(1)
    return os.path.abspath(argv[0]), os.path.abspath(argv[1])


# ============================================================
# Convert BVH → FBX
# ============================================================
def convert_bvh_to_fbx(bvh_path, fbx_path):
    print(f"Processing: {bvh_path}")

    # Clean scene
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # Import BVH (quietly)
    with suppress_bpy_warnings():
        bpy.ops.import_anim.bvh(
            filepath=bvh_path,
            axis_forward='-Z',
            axis_up='Y',
            filter_glob="*.bvh",
            global_scale=1.0,
        )

    # Rename Armature
    armature = None
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            obj.name = "T2M_Armature"
            bpy.context.view_layer.objects.active = obj
            armature = obj
            break

    # Adjust rotation for Unity/VRM (Z-up → Y-up); (But it was implemented in t2m)
    # if armature:
    #     armature.rotation_euler[0] = -1.5708  # -90° X rotation

    # Export FBX
    print(f"Exporting FBX → {fbx_path}")
    bpy.ops.export_scene.fbx(
        filepath=fbx_path,
        use_selection=False,
        apply_scale_options='FBX_SCALE_ALL',
        object_types={'ARMATURE'},
        bake_anim=True,
        bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=False,
        bake_anim_force_startend_keying=False,
        add_leaf_bones=False,
        axis_forward='-Z',
        axis_up='Y',
    )

    # Cleanup
    bpy.ops.object.delete()
    for block in bpy.data.objects:
        bpy.data.objects.remove(block, do_unlink=True)

    print(f"✅ Exported: {fbx_path}\n")


# ============================================================
# Main entry
# ============================================================
if __name__ == "__main__":
    # Check if we're running as a script with arguments
    if len(sys.argv) > 1 and "--" in sys.argv:
        bvh_path, fbx_path = parse_args()
        convert_bvh_to_fbx(bvh_path, fbx_path)
        bpy.ops.wm.quit_blender()
    else:
        # Running as imported module or without CLI args
        # Example usage - you can call convert_bvh_to_fbx() directly
        print("Script loaded. Call convert_bvh_to_fbx(bvh_path, fbx_path) to convert files.")
        print("Example: convert_bvh_to_fbx('input.bvh', 'output.fbx')")
