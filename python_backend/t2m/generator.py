"""
T2M Generator module for text-to-motion generation.
Handles the full pipeline: Text -> T2M -> SMPL (IK) -> BVH -> FBX
"""

import sys
import os
import torch
import numpy as np
import clip
import warnings
from typing import Optional

# T2M-GPT dependencies and Motion library imports moved to _load_models
# to prevent sys.path pollution and namespace conflicts (e.g. 'models' package).
import warnings

# Import centralized IK converter
from backend_utils.ik_bvh_converter import convert_xyz_to_bvh

warnings.filterwarnings("ignore")


class T2MConfig:
    """Configuration for T2M generation."""
    
    def __init__(
        self,
        # Paths from render_gif.py logic
        vqvae_path: str = 't2m-models/T2M-GPT-main/pretrained/VQVAE/net_last.pth',
        transformer_path: str = 't2m-models/T2M-GPT-main/pretrained/VQTransformer_corruption05/net_best_fid.pth',
        # Meta path seems to be VQVAEV3 in render_gif.py, so we keep this
        meta_path: str = 't2m-models/T2M-GPT-main/checkpoints/t2m/VQVAEV3_CB1024_CMT_H1024_NRES3/meta/',
        frame_rate: int = 20,
        device: Optional[str] = None
    ):
        self.vqvae_path = vqvae_path
        self.transformer_path = transformer_path
        self.meta_path = meta_path
        self.frame_rate = frame_rate
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        
        # T2M joint structure (22 joints)
        self.parents = [
            -1, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8,
            9, 9, 9, 12, 13, 14, 16, 17, 18, 19
        ]
        
        self.joint_names = [
            "Hips", "L_Hip", "R_Hip", "Spine",
            "L_Knee", "R_Knee", "Chest",
            "L_Ankle", "R_Ankle", "UpperChest",
            "L_Foot", "R_Foot", "Neck",
            "L_Shoulder", "R_Shoulder", "Head",
            "L_UpperArm", "R_UpperArm",
            "L_LowerArm", "R_LowerArm",
            "L_Hand", "R_Hand"
        ]


class T2MGenerator:
    """
    Main class for text-to-motion generation.
    """
    
    def __init__(self, config: Optional[T2MConfig] = None):
        self.config = config or T2MConfig()
        self.device = self.config.device
        self._loaded = False
        self.clip_model = None
        self.vqvae = None
        self.transformer = None

    def _load_models(self):
        """Lazy-load models using EXACTLY the logic from render_gif.py"""
        if self._loaded:
            return

        # --- Dynamic Import Block to avoid Namespace Conflicts ---
        # Add paths
        t2m_gpt_path = os.path.join(os.path.dirname(__file__), '..', 't2m-models', 'T2M-GPT-main')
        motion_lib_path = os.path.join(os.path.dirname(__file__), '..')
        
        for p in [t2m_gpt_path, motion_lib_path]:
            if p not in sys.path:
                sys.path.insert(0, p)
                
        # Import modules (Locally scoped to avoid global pollution if possible, but sys.modules catches them)
        # Note: 'models' package is problematic. Ideally we'd package them properly.
        # Here we just import them late.
        try:
            import options.option_transformer as option_trans
            import models.vqvae as vqvae
            import models.t2m_trans as trans
        except ImportError:
            # If MoMask 'models' is already loaded, we might need to reload or force?
            # This is tricky. Python doesn't support two 'models' packages easily.
            # Ideally, user should restart process to switch models if they conflict.
            # But for now, we assume if we import here, it might work if MoMask wasn't imported first.
            import options.option_transformer as option_trans
            import models.vqvae as vqvae
            import models.t2m_trans as trans

        # 1. Simulate arguments (Same as render_gif.py)
        sys.argv = ['GPT_eval_multi.py']
        args = option_trans.get_args_parser()
        
        # 2. Set specific overrides (Same as render_gif.py)
        args.dataname = 't2m'
        args.down_t = 2
        args.depth = 3
        args.block_size = 51
        
        # Note: We do NOT manually set nb_code to 1024 here anymore.
        # We trust get_args_parser() defaults + the checkpoint.

        # 3. Load CLIP
        self.clip_model, _ = clip.load("ViT-B/32", device=self.device, jit=False)
        self.clip_model.eval()

        # 4. Load VQVAE
        self.vqvae = vqvae.HumanVQVAE(
            args, args.nb_code, args.code_dim, args.output_emb_width,
            args.down_t, args.stride_t, args.width, args.depth,
            args.dilation_growth_rate
        )
        
        # Load weights with strict=True (Same as render_gif.py)
        ckpt_vq = torch.load(self.config.vqvae_path, map_location='cpu')
        self.vqvae.load_state_dict(ckpt_vq['net'], strict=True)
        self.vqvae.eval().to(self.device)

        # 5. Load Transformer
        self.transformer = trans.Text2Motion_Transformer(
            num_vq=args.nb_code, 
            embed_dim=1024, 
            clip_dim=args.clip_dim, 
            block_size=args.block_size, 
            num_layers=9, 
            n_head=16, 
            drop_out_rate=args.drop_out_rate, 
            fc_rate=args.ff_rate
        )
        
        # Load weights with strict=True (Same as render_gif.py)
        ckpt_trans = torch.load(self.config.transformer_path, map_location='cpu')
        self.transformer.load_state_dict(ckpt_trans['trans'], strict=True)
        self.transformer.eval().to(self.device)

        self._loaded = True


    def generate_motion(self, text: str, motion_length: int = 0, max_motion_length: int = 196, use_direct_6d: bool = True):
        from scipy.signal import savgol_filter
        """
        Generate motion using EXACTLY the logic from render_gif.py
        Args:
            motion_length: Exact length (not fully supported by T2M-GPT sampling yet, effectively ignored or handled by truncation if data is longer)
            max_motion_length: Max frames to return (truncation)
        """
        self._load_models()

        # Load mean/std (Same as render_gif.py)
        # Note: render_gif.py hardcodes the path, here we use config but ensure it matches
        mean = torch.from_numpy(np.load(os.path.join(self.config.meta_path, "mean.npy"))).to(self.device)
        std = torch.from_numpy(np.load(os.path.join(self.config.meta_path, "std.npy"))).to(self.device)

        with torch.no_grad():
            # Tokenize (Same as render_gif.py)
            clip_text = [text] # render_gif expects a list
            text_tokens = clip.tokenize(clip_text, truncate=True).to(self.device)
            feat_clip_text = self.clip_model.encode_text(text_tokens).float()
            
            # Sample (Same as render_gif.py)
            # T2M-GPT transformer sample usually runs until EOS or max_len (often hardcoded or large)
            index_motion = self.transformer.sample(feat_clip_text[0:1], False)
            pred_pose = self.vqvae.forward_decoder(index_motion)
            
            # Denormalize
            pred_pose = (pred_pose * std + mean).float()

            if use_direct_6d:
                # Return raw 263-dim output (Seq, 263)
                motion_data = pred_pose[0] # Take first from batch
            else:
                # Recover (Same as render_gif.py)
                from utils.motion_process import recover_from_ric
                motion_data = recover_from_ric(pred_pose, 22).cpu().numpy()
                # Strip batch dimension (1, T, 22, 3) -> (T, 22, 3)
                if motion_data.ndim == 4:
                    motion_data = motion_data[0]
            
            # --- Apply Length Constraints ---
            cur_len = motion_data.shape[0]
            
            # If max length defined, truncate
            if max_motion_length > 0 and cur_len > max_motion_length:
                motion_data = motion_data[:max_motion_length]
                
            # If fixed length requested (and it's shorter than what we got via truncation), truncate further
            # Padding to extend is risky for quality, so we usually only truncate.
            if motion_length > 0 and motion_data.shape[0] > motion_length:
                motion_data = motion_data[:motion_length]
            
            # [FIX] Apply Savitzky-Golay filter for smoothing
            # window_length 必須是奇數，且小於幀數。越大越平滑，但細節越少。
            # polyorder 是多項式階數，通常用 2 或 3。
            # try:
            #     # 針對時間軸 (axis=0 或 axis=1) 進行平滑
            #     # 假設 motion_data 是 (1, T, 22, 3)
            #     if motion_data.shape[1] > 9: # 確保長度夠長
            #         motion_data[0] = savgol_filter(motion_data[0], window_length=9, polyorder=3, axis=0)
            # except Exception as e:
            #     print(f"Smoothing failed: {e}")

            
        return motion_data # Returns shape (T, 22, 3) or (Seq, 263)

    def motion_to_bvh(self, motion_data, bvh_path: str, append_end_joints: bool = True, use_direct_6d: bool = True):
        """
        Convert T2M motion positions to BVH file using IK.
        """
        if use_direct_6d:
            # New Method: Direct 6D -> BVH
            print(f"[T2MGenerator] Using Direct 6D Method for {bvh_path}")
            from utils.motion_process import recover_bvh_from_263
            recover_bvh_from_263(motion_data, bvh_path, fps=self.config.frame_rate)
            return

        motion_xyz = motion_data
        # Handle batch dimension if present
        if motion_xyz.ndim == 4:
            positions_np = motion_xyz[0]
        else:
            positions_np = motion_xyz if isinstance(motion_xyz, np.ndarray) else motion_xyz.cpu().numpy()
        
        # Use centralized IK converter
        convert_xyz_to_bvh(positions_np, bvh_path, foot_ik=True)

def generate_motion_from_text(text: str, output_path: str, config: Optional[T2MConfig] = None, use_direct_6d: bool = True) -> str:
    generator = T2MGenerator(config)
    motion_data = generator.generate_motion(text, use_direct_6d=use_direct_6d)
    generator.motion_to_bvh(motion_data, output_path, use_direct_6d=use_direct_6d)
    return output_path

