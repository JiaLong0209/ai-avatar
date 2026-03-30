
import os
import numpy as np
import torch
from .joints2bvh import Joint2BVHConvertor

def convert_xyz_to_bvh(xyz_positions, output_path, foot_ik=True, target_fps=20):
    """
    Converts XYZ positions (Frames, Joints, 3) to BVH file using MoMask's IK.
    
    Args:
        xyz_positions: (Frames, Joints, 3) numpy array. 
                       Expected content: 22 joints (SMPL structure).
                       Expected unit: Meters (matching template.bvh).
        output_path: Path to save the BVH file.
        foot_ik: Whether to apply foot locking/cleanup.
        target_fps: Frame rate (currently likely fixed by the converter logic, but kept for interface).
    """
    # Initialize implementation
    converter = Joint2BVHConvertor()
    
    # Ensure directory exists
    dir_path = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(dir_path, exist_ok=True)
    
    # Run conversion
    # Note: converter.convert returns (new_anim, glb)
    # It also saves the file if filename is provided.
    converter.convert(xyz_positions, output_path, foot_ik=foot_ik)
    
    print(f"[IK-BVH-Converter] Saved BVH to {output_path}")
