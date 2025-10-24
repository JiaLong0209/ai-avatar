"""
BVH to FBX conversion utility using Blender.
"""

import bpy
import sys
import os
import contextlib
import io
import subprocess
import tempfile
from typing import Optional


@contextlib.contextmanager
def suppress_bpy_warnings():
    """Temporarily suppress Blender console warnings (FBX/BVH import)."""
    old_stdout, old_stderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
    try:
        yield
    finally:
        sys.stdout, sys.stderr = old_stdout, old_stderr


def convert_bvh_to_fbx(bvh_path: str, fbx_path: str) -> bool:
    """
    Convert BVH file to FBX using Blender.
    
    Args:
        bvh_path: Path to input BVH file
        fbx_path: Path to output FBX file
        
    Returns:
        True if conversion successful, False otherwise
    """
    try:
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

        if armature is None:
            print("Error: No armature found in BVH file")
            return False

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

        print(f"✅ Exported: {fbx_path}")
        return True

    except Exception as e:
        print(f"Error converting BVH to FBX: {e}")
        return False


def convert_bvh_to_fbx_external(bvh_path: str, fbx_path: str, blender_path: Optional[str] = None) -> bool:
    """
    Convert BVH to FBX using external Blender process.
    This is safer for production use as it doesn't interfere with the main process.
    
    Args:
        bvh_path: Path to input BVH file
        fbx_path: Path to output FBX file
        blender_path: Path to Blender executable (auto-detect if None)
        
    Returns:
        True if conversion successful, False otherwise
    """
    try:
        # Auto-detect Blender path
        if blender_path is None:
            blender_path = "blender"  # Assume it's in PATH
        
        # Create temporary script
        script_content = f'''
import bpy
import sys
import os
import contextlib
import io

@contextlib.contextmanager
def suppress_bpy_warnings():
    old_stdout, old_stderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
    try:
        yield
    finally:
        sys.stdout, sys.stderr = old_stdout, old_stderr

def convert():
    bvh_path = "{bvh_path}"
    fbx_path = "{fbx_path}"
    
    # Clean scene
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # Import BVH
    with suppress_bpy_warnings():
        bpy.ops.import_anim.bvh(
            filepath=bvh_path,
            axis_forward='-Z',
            axis_up='Y',
            filter_glob="*.bvh",
            global_scale=1.0,
        )

    # Rename Armature
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            obj.name = "T2M_Armature"
            bpy.context.view_layer.objects.active = obj
            break

    # Export FBX
    bpy.ops.export_scene.fbx(
        filepath=fbx_path,
        use_selection=False,
        apply_scale_options='FBX_SCALE_ALL',
        object_types={{'ARMATURE'}},
        bake_anim=True,
        bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=False,
        bake_anim_force_startend_keying=False,
        add_leaf_bones=False,
        axis_forward='-Z',
        axis_up='Y',
    )

    print(f"✅ Exported: {{fbx_path}}")

if __name__ == "__main__":
    convert()
    bpy.ops.wm.quit_blender()
'''
        
        # Write script to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as script_file:
            script_file.write(script_content)
            script_path = script_file.name

        try:
            # Run Blender with the script
            cmd = [blender_path, "-b", "-P", script_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print(f"✅ BVH to FBX conversion successful: {fbx_path}")
                return True
            else:
                print(f"Blender conversion failed: {result.stderr}")
                return False
            
        finally:
            # Clean up temporary script
            try:
                os.remove(script_path)
            except:
                pass
                
    except Exception as e:
        print(f"Error in external BVH to FBX conversion: {e}")
        return False
