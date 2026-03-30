# blender_scripts/convert_bvh_to_fbx.py

import bpy
import sys
import pathlib

# -------------------------
# Parse arguments
# -------------------------
argv = sys.argv
argv = argv[argv.index("--") + 1:]

bvh_path = pathlib.Path(argv[0]).resolve()
fbx_path = pathlib.Path(argv[1]).resolve()

# -------------------------
# Reset Blender
# -------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)

# -------------------------
# Import BVH
# -------------------------
try:
    bpy.ops.import_anim.bvh(
        filepath=str(bvh_path),
        axis_forward='-Z',
        axis_up='Y',
        global_scale=1.0,
        frame_start=1,
    )
except Exception as e:
    print(f"Error importing BVH: {e}", file=sys.stderr)
    sys.exit(1)

# -------------------------
# Get Armature
# -------------------------
armatures = [obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE']
if not armatures:
    raise RuntimeError("❌ No armature found after BVH import")

armature = armatures[0]
bpy.context.view_layer.objects.active = armature
armature.select_set(True)

# -------------------------
# Apply transforms (VERY IMPORTANT)
# -------------------------
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.transform_apply(
    location=True,
    rotation=True,
    scale=True
)

# -------------------------
# Force animation bake
# -------------------------
try:
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.nla.bake(
        frame_start=bpy.context.scene.frame_start,
        frame_end=bpy.context.scene.frame_end,
        only_selected=False,
        visual_keying=True,
        clear_constraints=False,
        use_current_action=True,
        bake_types={'POSE'}
    )
    bpy.ops.object.mode_set(mode='OBJECT')
except Exception as e:
    print(f"Warning: Animation bake failed or skipped: {e}")
    bpy.ops.object.mode_set(mode='OBJECT')

# -------------------------
# Export FBX (Unity / VRM safe)
# -------------------------
try:
    bpy.ops.export_scene.fbx(
        filepath=str(fbx_path),
        use_selection=True,
        object_types={'ARMATURE'},
        bake_anim=True,
        bake_anim_use_all_bones=True,     # ⭐ VERY IMPORTANT
        bake_anim_force_startend_keying=True,
        add_leaf_bones=False,
        primary_bone_axis='Y',
        secondary_bone_axis='X',
        axis_forward='-Z',
        axis_up='Y',
        apply_scale_options='FBX_SCALE_ALL',
        use_armature_deform_only=True
    )
except Exception as e:
    print(f"Error exporting FBX: {e}", file=sys.stderr)
    sys.exit(1)

print(f"✅ Converted BVH → FBX successfully")
print(f"   {bvh_path}")
print(f"   {fbx_path}")
