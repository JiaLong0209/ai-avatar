"""
T2M Generator module for text-to-motion generation.
"""

import sys
import os
import torch
import numpy as np
import clip
import warnings
from tqdm import tqdm
from scipy.spatial.transform import Rotation as R
import tempfile
from typing import Optional

# Import T2M-GPT dependencies
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'T2M-GPT-main'))
import options.option_transformer as option_trans
import models.vqvae as vqvae
import models.t2m_trans as trans
from utils.motion_process import recover_from_ric

warnings.filterwarnings('ignore')
class T2MConfig:
    """Configuration for T2M generation."""
    
    def __init__(self, 
                 vqvae_path: str = 'T2M-GPT-main/pretrained/VQVAE/net_last.pth',
                 transformer_path: str = 'T2M-GPT-main/pretrained/VQTransformer_corruption05/net_best_fid.pth',
                 meta_path: str = 'T2M-GPT-main/checkpoints/t2m/VQVAEV3_CB1024_CMT_H1024_NRES3/meta/',
                 frame_rate: int = 20,
                 device: Optional[str] = None):
        self.vqvae_path = vqvae_path
        self.transformer_path = transformer_path
        self.meta_path = meta_path
        self.frame_rate = frame_rate
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Joint structure for BVH
        self.joint_names = [
            "Hips", "L_Hip", "R_Hip", "Spine1", "L_Knee", "R_Knee", "Spine2", 
            "L_Ankle", "R_Ankle", "Spine3", "L_Foot", "R_Foot", "Neck", 
            "L_Collar", "R_Collar", "Head", "L_Shoulder", "R_Shoulder", 
            "L_Elbow", "R_Elbow", "L_Wrist", "R_Wrist"
        ]
        self.convert_to_vrm()
        self.parents = [-1, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 9, 9, 12, 13, 14, 16, 17, 18, 19]

    def convert_to_vrm(self):
        """Convert T2M joint names to VRM-compatible joint names."""
        T2M_TO_VRM = {
            "Hips": "J_Bip_C_Hips",
            "L_Hip": "J_Bip_L_UpperLeg",
            "R_Hip": "J_Bip_R_UpperLeg",
            "Spine1": "J_Bip_C_Spine",
            "L_Knee": "J_Bip_L_LowerLeg",
            "R_Knee": "J_Bip_R_LowerLeg",
            "Spine2": "J_Bip_C_Chest",
            "L_Ankle": "J_Bip_L_Foot",
            "R_Ankle": "J_Bip_R_Foot",
            "Spine3": "J_Bip_C_UpperChest",
            "L_Foot": "J_Bip_L_ToeBase",
            
            "R_Foot": "J_Bip_R_ToeBase",
            "Neck": "J_Bip_C_Neck",
            "L_Collar": "J_Bip_L_Shoulder",
            "R_Collar": "J_Bip_R_Shoulder",
            "Head": "J_Bip_C_Head",
            "L_Shoulder": "J_Bip_L_UpperArm",
            "R_Shoulder": "J_Bip_R_UpperArm",
            "L_Elbow": "J_Bip_L_LowerArm",
            "R_Elbow": "J_Bip_R_LowerArm",
            "L_Wrist": "J_Bip_L_Hand",
            "R_Wrist": "J_Bip_R_Hand",
        }

        remapped = []
        for j in self.joint_names:
            vrm_joint = T2M_TO_VRM.get(j)
            if vrm_joint:
                remapped.append(vrm_joint)
            else:
                print(f"[Warning] No VRM mapping for joint '{j}', keeping original.")
                remapped.append(j)

        self.joint_names = remapped
        return self.joint_names


class T2MGenerator:
    """Main class for text-to-motion generation."""
    
    def __init__(self, config: Optional[T2MConfig] = None):
        self.config = config or T2MConfig()
        self.device = torch.device(self.config.device)
        self.models = None
        self._models_loaded = False
    
    def _load_models(self):
        """Load all required models."""
        if self._models_loaded:
            return
            
        print("Loading T2M models...")
        
        # Set up args for model loading
        sys.argv = ['GPT_eval_multi.py']
        args = option_trans.get_args_parser()
        args.dataname, args.down_t, args.depth, args.block_size = 't2m', 2, 3, 51
        
        # Load CLIP
        clip_model, _ = clip.load("ViT-B/32", device=self.device, jit=False, download_root='./')
        
        # Load VQVAE
        net = vqvae.HumanVQVAE(
            args, args.nb_code, args.code_dim, args.output_emb_width, 
            args.down_t, args.stride_t, args.width, args.depth, args.dilation_growth_rate
        )
        ckpt = torch.load(self.config.vqvae_path, map_location='cpu')
        net.load_state_dict(ckpt['net'], strict=True)
        net.eval().to(self.device)
        
        # Load Transformer
        trans_encoder = trans.Text2Motion_Transformer(
            num_vq=args.nb_code, embed_dim=1024, clip_dim=args.clip_dim, 
            block_size=args.block_size, num_layers=9, n_head=16, 
            drop_out_rate=args.drop_out_rate, fc_rate=args.ff_rate
        )
        ckpt = torch.load(self.config.transformer_path, map_location='cpu')
        trans_encoder.load_state_dict(ckpt['trans'], strict=True)
        trans_encoder.eval().to(self.device)
        
        self.models = (clip_model, net, trans_encoder)
        self._models_loaded = True
        print("T2M models loaded successfully.")
    
    def generate_motion(self, text: str) -> np.ndarray:
        """Generate motion data from text description."""
        self._load_models()
        clip_model, net, trans_encoder = self.models
        
        # Load statistics
        mean = torch.from_numpy(np.load(os.path.join(self.config.meta_path, 'mean.npy'))).to(self.device)
        std = torch.from_numpy(np.load(os.path.join(self.config.meta_path, 'std.npy'))).to(self.device)
        
        # Tokenize and encode text
        tokenized_text = clip.tokenize([text], truncate=True).to(self.device)
        feat_clip_text = clip_model.encode_text(tokenized_text).float()
        
        # Generate motion
        with torch.no_grad():
            index_motion = trans_encoder.sample(feat_clip_text[0:1], False)
            pred_pose = net.forward_decoder(index_motion)
            pred_xyz = recover_from_ric((pred_pose * std + mean).float(), 22)
        
        return pred_xyz.reshape(-1, 22, 3).detach().cpu().numpy()
    
    def motion_to_bvh(self, motion_xyz: np.ndarray, output_path: str):
        """Convert motion data to BVH file."""
        # Calculate T-Pose offsets
        t_pose = motion_xyz[0]
        offsets = {
            name: (t_pose[i] - t_pose[self.config.parents[i]]) 
            if self.config.parents[i] != -1 else np.zeros(3) 
            for i, name in enumerate(self.config.joint_names)
        }
        
        # Calculate frame data
        all_frame_data = []
        for frame_data in tqdm(motion_xyz, desc="Processing frames"):
            frame_line_data = []
            
            # Add root position
            frame_line_data.extend(frame_data[0])
            
            # Calculate rotations for all joints
            for i, name in enumerate(self.config.joint_names):
                if self.config.parents[i] == -1:  # Root joint
                    rotation = R.identity()
                else:
                    parent_idx = self.config.parents[i]
                    v_initial = offsets[name]
                    v_current = frame_data[i] - frame_data[parent_idx]
                    
                    if np.linalg.norm(v_initial) < 1e-6 or np.linalg.norm(v_current) < 1e-6:
                        rotation = R.identity()
                    else:
                        rotation, _ = R.align_vectors([v_current], [v_initial])
                
                # BVH uses ZXY rotation order
                euler_angles = rotation.as_euler('zxy', degrees=True)
                frame_line_data.extend(euler_angles)
            
            all_frame_data.append(frame_line_data)
        
        # Write BVH file
        self._write_bvh_file(output_path, all_frame_data, offsets)
    
    def _write_bvh_file(self, filename: str, frame_data: list, offsets: dict):
        """Write BVH file with skeleton and motion data."""
        with open(filename, 'w') as f:
            f.write("HIERARCHY\n")
            
            children = {i: [] for i in range(len(self.config.joint_names))}
            for i, p in enumerate(self.config.parents):
                if p != -1: 
                    children[p].append(i)

            def write_joint(joint_index, indent_level):
                joint_name = self.config.joint_names[joint_index]
                indent = "  " * indent_level
                
                if self.config.parents[joint_index] == -1:
                    f.write(f"{indent}ROOT {joint_name}\n")
                    channels = "Xposition Yposition Zposition Zrotation Xrotation Yrotation"
                    num_channels = 6
                else:
                    f.write(f"{indent}JOINT {joint_name}\n")
                    channels = "Zrotation Xrotation Yrotation"
                    num_channels = 3

                f.write(f"{indent}{{\n")
                indent_inner = indent + "  "
                offset = offsets[joint_name]
                f.write(f"{indent_inner}OFFSET {offset[0]:.6f} {offset[1]:.6f} {offset[2]:.6f}\n")
                f.write(f"{indent_inner}CHANNELS {num_channels} {channels}\n")

                if not children[joint_index]:
                    f.write(f"{indent_inner}End Site\n{indent_inner}{{\n{indent_inner}  OFFSET 0.0 0.0 0.0\n{indent_inner}}}\n")
                else:
                    for child_index in children[joint_index]: 
                        write_joint(child_index, indent_level + 1)
                
                f.write(f"{indent}}}\n")

            write_joint(0, 0)
            
            f.write("MOTION\n")
            f.write(f"Frames: {len(frame_data)}\n")
            f.write(f"Frame Time: {1.0 / self.config.frame_rate:.8f}\n")
            for frame_line in frame_data:
                f.write(" ".join([f"{val:.6f}" for val in frame_line]) + "\n")


def generate_motion_from_text(text: str, output_path: str, config: Optional[T2MConfig] = None) -> str:
    """
    Convenience function to generate BVH file from text.
    
    Args:
        text: Text description of the motion
        output_path: Path where to save the BVH file
        config: Optional T2M configuration
        
    Returns:
        Path to the generated BVH file
    """
    generator = T2MGenerator(config)
    motion_xyz = generator.generate_motion(text)
    generator.motion_to_bvh(motion_xyz, output_path)
    return output_path
