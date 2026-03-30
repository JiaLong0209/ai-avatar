import sys
import os
import torch
import numpy as np
import hydra
from omegaconf import OmegaConf, DictConfig
from scipy.spatial.transform import Rotation as R

# =========================================================
# Path Setup
# =========================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIGHT_T2M_ROOT = os.path.join(PROJECT_ROOT, "t2m-models", "light-t2m-main")
T2M_GPT_ROOT = os.path.join(PROJECT_ROOT, "t2m-models", "T2M-GPT-main")

# Ensure modules are importable
if LIGHT_T2M_ROOT not in sys.path:
    print(f"[LightT2MGenerator] Appending to sys.path: {os.path.abspath(LIGHT_T2M_ROOT)}")
    sys.path.append(os.path.abspath(LIGHT_T2M_ROOT))

# Debug import
try:
    import src.models.nets.light_final
    print("[LightT2MGenerator] successfully imported src.models.nets.light_final")
except ImportError as e:
    print(f"[LightT2MGenerator] FAILED to import src.models.nets.light_final: {e}")
    # List directory to see what's wrong
    print(f"Listing {LIGHT_T2M_ROOT}: {os.listdir(LIGHT_T2M_ROOT) if os.path.exists(LIGHT_T2M_ROOT) else 'PATH NOT FOUND'}")

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Setup rootutils for Light-T2M internal imports
try:
    import src.utils.rootutils as rootutils
    # This sets up the environment so 'src' imports work correctly within light-t2m modules
    rootutils.setup_root(os.path.join(LIGHT_T2M_ROOT, ".project-root"), indicator=".project-root", pythonpath=True)
except ImportError:
    print("[LightT2MGenerator] Warning: Could not import rootutils or setup root. Ensure light-t2m-main dependencies are installed.")

# Import Light-T2M specific Utils
try:
    from src.data.humanml.scripts.motion_process import recover_root_rot_pos
    from src.data.humanml.common.quaternion import cont6d_to_matrix
except ImportError as e:
    print(f"[LightT2MGenerator] Error importing Light-T2M modules: {e}")

# Import Local Project Utils
try:
    from Motion.Animation import Animation
    from Motion.BVH import save as bvh_save
    from Motion.Quaternions import Quaternions
    from t2m.generator import T2MConfig
except ImportError:
    pass # Will fail if run standalone, but fine in app context

class LightT2MGenerator:
    """
    Generator wrapper for the Light-T2M model.
    Implements Direct 6D -> BVH conversion for smoother results.
    """
    
    def __init__(self, 
                 cfg_path=None, 
                 ckpt_path=None, 
                 meta_path=None,
                 device=None):
        
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[LightT2MGenerator] Initializing on {self.device}")
        
        # Paths
        if cfg_path is None:
            cfg_path = os.path.join(LIGHT_T2M_ROOT, "configs", "gen_motion.yaml")
            
        if ckpt_path is None:
            # Default to hml3d.ckpt
            ckpt_path = os.path.join(LIGHT_T2M_ROOT, "checkpoints", "hml3d.ckpt")
            
        if meta_path is None:
            # Reusing T2M-GPT meta stats as fallback/standard
            meta_path = os.path.join(T2M_GPT_ROOT, "checkpoints/t2m/VQVAEV3_CB1024_CMT_H1024_NRES3/meta")

        # Load Configuration
        self._load_config(cfg_path, ckpt_path)
        
        # Load Mean/Std for normalization
        self._load_meta(meta_path)
        
        # Load Model
        self._load_model()
        
        # Configuration for Output (Skeleton definition)
        self.t2m_config = T2MConfig()

    def _load_config(self, cfg_path, ckpt_path):
        """Constructs the configuration object."""
        # 1. Load Main Gen Config (gen_motion.yaml)
        # We don't really use this much, mainly for 'data' defaults if we pursued that.
        self.cfg = OmegaConf.load(cfg_path)

        # 2. Load Model Config (light_final.yaml) with COMPOSITION
        model_cfg_path = os.path.join(LIGHT_T2M_ROOT, "configs", "model", "light_final.yaml")
        if os.path.exists(model_cfg_path):
            # Use manual composition to resolve 'defaults' list
            self.cfg.model = self._compose_config(model_cfg_path)
        else:
            print(f"Warning: Model config not found at {model_cfg_path}. Using config as is.")

        # 3. Apply Overrides
        self.cfg.ckpt_path = ckpt_path
        self.cfg.device = self.device
        
        # [FIX] Manually satisfy interpolations that Hydra would normally handle
        if "data" not in self.cfg:
            self.cfg.data = OmegaConf.create({
                "dataset_name": "hml3d",
                "motion_dim": 263,
                "njoints": 22
            })
            
        # Also provide 'paths' if referenced (e.g. paths.output_dir in ckpt_path default)
        if "paths" not in self.cfg:
             self.cfg.paths = OmegaConf.create({"output_dir": ".", "root_dir": LIGHT_T2M_ROOT})
        
        # Ensure 'extras' and other needed keys exist if code expects them
        if "extras" not in self.cfg:
            self.cfg.extras = OmegaConf.create({"ignore_warnings": True})

    def _compose_config(self, primary_cfg_path):
        """
        Manually composes configuration by processing the 'defaults' list.
        Simplistic Hydra-like composition logic.
        """
        base_cfg = OmegaConf.load(primary_cfg_path)
        print(f"Composing config for {primary_cfg_path}")
        
        # If there are defaults, process them
        if "defaults" in base_cfg:
            defaults = base_cfg.defaults
            for item in defaults:
                # item can be a string "default" or a dict {"text_encoder": "clip"}
                
                group = None
                name = None
                
                if isinstance(item, str):
                    if item == "_self_": continue
                    # Logic: string usually maps to a file in the SAME directory
                    name = item
                elif OmegaConf.is_dict(item) or isinstance(item, dict):
                    # e.g. {"text_encoder": "clip"}
                    # item is DictConfig if loaded via OmegaConf, so list(item.keys()) works
                    # Convert to dict to be safe with keys()
                    item_dict = OmegaConf.to_container(item) if OmegaConf.is_config(item) else item
                    group = list(item_dict.keys())[0]
                    name = item_dict[group]
                
                if name:
                    config_dir = os.path.dirname(primary_cfg_path) # e.g. configs/model
                    
                    if group:
                        # Group exists: look in configs/model/{group}/{name}.yaml
                        sub_path = os.path.join(config_dir, group, f"{name}.yaml")
                    else:
                        # No group: look in configs/model/{name}.yaml
                        sub_path = os.path.join(config_dir, f"{name}.yaml")
                        
                    if os.path.exists(sub_path):
                        # Recursive composition? Hydra does it, so we should try simple loading first
                        # Ideally we recursively compose sub_cfg too, but let's assume 1-level deep for now or recurse
                        sub_cfg = self._compose_config(sub_path)
                        
                        if group:
                             # Merge into specific key, e.g. model.text_encoder
                             print(f"Merging {group}={name} from {sub_path}")
                             if group not in base_cfg:
                                 base_cfg[group] = sub_cfg
                             else:
                                 base_cfg[group] = OmegaConf.merge(base_cfg[group], sub_cfg)
                        else:
                             # Merge at root (mixin), e.g. model/default.yaml
                             print(f"Merging root mixin {name} from {sub_path}")
                             base_cfg = OmegaConf.merge(sub_cfg, base_cfg)
                    else:
                        print(f"[LightT2MGenerator] Warning context: Could not find config component {sub_path}")
        
        return base_cfg

    def _load_meta(self, meta_path):
        try:
            mean_path = os.path.join(meta_path, "mean.npy")
            std_path = os.path.join(meta_path, "std.npy")
            
            self.mean = torch.from_numpy(np.load(mean_path)).to(self.device).float()
            self.std = torch.from_numpy(np.load(std_path)).to(self.device).float()
            print("[LightT2MGenerator] Mean and Std loaded successfully.")
        except Exception as e:
            print(f"[LightT2MGenerator] Failed to load Mean/Std from {meta_path}: {e}")
            raise

    def _load_model(self):
        try:
            # Instantiate model from config
            # Debug: Check if composition worked
            print(OmegaConf.to_yaml(self.cfg.model))
            self.model = hydra.utils.instantiate(self.cfg.model)
            
            # Load Checkpoint
            print(f"[LightT2MGenerator] Loading weights from {self.cfg.ckpt_path}")
            if os.path.exists(self.cfg.ckpt_path):
                ckpt = torch.load(self.cfg.ckpt_path, map_location=self.device, weights_only=False)
                self.model.load_state_dict(ckpt["state_dict"], strict=False)
                print("[LightT2MGenerator] Model loaded successfully.")
            else:
                print(f"[LightT2MGenerator] Warning: Checkpoint not found at {self.cfg.ckpt_path}. Using random weights.")
            
            self.model.to(self.device)
            self.model.eval()
            print("[LightT2MGenerator] Model loaded successfully.")
        except Exception as e:
            print(f"[LightT2MGenerator] Model loading failed: {e}")
            raise

    def generate_motion(self, text, seq_len=196, use_direct_6d=True):
        """
        Generates motion data from text.
        Returns the raw model output (denormalized).
        """
        print(f"[LightT2MGenerator] Generating request: '{text}'")
        
        # Prepare Dummy Input (Model expects [B, L, D])
        batch_size = 1
        dummy_motion = torch.zeros((batch_size, seq_len, 263)).to(self.device)
        length_tensor = torch.tensor([seq_len], dtype=torch.long, device=self.device)
        
        with torch.no_grad():
            # 1. Sample Motion
            # sample_motion expects (motion, length, text_list)
            pred_motion = self.model.sample_motion(dummy_motion, length_tensor, [text])
            
            # 2. Denormalize
            pred_motion = pred_motion * self.std + self.mean
            
        return pred_motion[0] # Return single sequence (L, 263)

    def motion_to_bvh(self, data, output_path, use_direct_6d=True):
        """
        Converts motion data to BVH.
        Supports Direct 6D conversion (recommended) or standard IK extraction.
        """
        if use_direct_6d:
            self.motion_to_bvh_direct6d(data, output_path)
        else:
            # Fallback to standard reconstruction (if needed)
            # For Light-T2M, the data IS RIC features, so we can use standard recover_from_ric 
            # and then standard Animation from positions.
            print("[LightT2MGenerator] usage of non-direct-6d not fully implemented, defaulting to direct 6d")
            self.motion_to_bvh_direct6d(data, output_path)

    def motion_to_bvh_direct6d(self, data, output_path):
        """
        Converts RIC feature vector directly to BVH using the 6D rotation components,
        skipping the Position -> IK step.
        """
        joints_num = 22
        
        # Data shape: (T, 263)
        
        # 1. Recover Root Rotation and Position (needed for global placement)
        # recover_root_rot_pos expects (..., 263)
        r_rot_quat, r_pos = recover_root_rot_pos(data)
        # r_rot_quat: (T, 4)
        # r_pos: (T, 3)
        
        # 2. Extract Body 6D Rotations
        # Indices logic matches recover_from_rot in motion_process.py
        # Skip: Root(4) + Positions(21*3)
        start_indx = 1 + 2 + 1 + (joints_num - 1) * 3
        end_indx = start_indx + (joints_num - 1) * 6
        
        cont6d_params = data[..., start_indx:end_indx] # (T, 126)
        cont6d_params = cont6d_params.view(-1, joints_num - 1, 6) # (T, 21, 6)
        
        # 3. Convert Body 6D -> Matrix -> Quaternion
        # Helper from light-t2m-main
        body_mats = cont6d_to_matrix(cont6d_params) # (T, 21, 3, 3)
        
        # Convert to Numpy for Scipy/BVH construction
        body_mats_np = body_mats.cpu().numpy()
        r_rot_quat_np = r_rot_quat.cpu().numpy()
        r_pos_np = r_pos.cpu().numpy()
        
        # Flatten to (N, 3, 3) for efficient Scipy conversion
        T = body_mats_np.shape[0]
        body_mats_flat = body_mats_np.reshape(-1, 3, 3)
        
        # R.from_matrix returns (x, y, z, w)
        body_quats_flat = R.from_matrix(body_mats_flat).as_quat()
        
        # Convert to (w, x, y, z) for our Animation/Quaternions class
        # (x, y, z, w) -> (w, x, y, z) : Roll +1
        body_quats_flat = np.roll(body_quats_flat, 1, axis=-1)
        
        # Reshape back to (T, 21, 4)
        body_quats = body_quats_flat.reshape(T, 21, 4)
        
        # 4. Concatenate Root + Body Quaternions
        # Root quat from recover_root_rot_pos is likely (w, x, y, z) (standard PyTorch convention used in project)
        # Checking recover_root_rot_pos implementation:
        # r_rot_quat[..., 0] = cos(angle/2) -> this IS 'w'. 
        # So r_rot_quat is already (w, x, y, z).
        
        r_rot_quat_np = r_rot_quat_np[:, None, :] # (T, 1, 4)
        full_quats = np.concatenate([r_rot_quat_np, body_quats], axis=1) # (T, 22, 4)
        
        # 5. Construct Final Positions
        # Animation expects (T, J, 3). Root at index 0 is used for global position.
        # Rest are offsets (usually).
        # We need to construct a positions array where index 0 is valid R_POS.
        
        positions = np.zeros((T, 22, 3))
        positions[:, 0, :] = r_pos_np
        
        # 6. Offsets
        # Use T2MConfig offsets (Standard HumanML3D Skeleton)
        # We need to compute them or load them. 
        # The T2MGenerator computes them from T-Pose.
        # We will reuse the logic from T2MGenerator if possible, 
        # or just assume standard offsets are needed by the BVH writer.
        # Actually, `Animation` class takes `offsets`.
        # We can calculate offsets from the T2MConfig parents and some T-Pose data.
        # Or simpler: The BVH writer needs offsets.
        # Let's use the offsets from T2MConfig logic.
        
        offsets = np.zeros((22, 3))
        # Note: We don't have the T-Pose positions handy unless we store them.
        # BUT, standard HumanML3D offsets are roughly constant.
        # A hack: Load one sample from Mean.npy (which is in positions) ?? No.
        # Better hack: Use the T2MConfig from existing generator to get offsets logic?
        # Re-implementing offsets calculation requires the VQVAE skeleton data...
        # Wait, recover_from_ric in T2M-GPT code generates positions.
        # We can use that ONCE to get the offsets from the first frame of a dummy generation?
        
        # Creating a temporary skeleton from T2MConfig to get offsets
        # Actually, if we use `recover_from_ric` (standard), we obtain XYZ positions.
        # We could use that for the first frame to deduce offsets.
        # Let's do that as a robust initialization.
        
        # Using recover_from_ric (from motion_process) on a zero vector to get T-pose? 
        # Or better: Recover the positions for THIS motion briefly just to get valid offsets?
        # recover_from_ric returns global positions.
        # offsets[i] = pos[i] - pos[parent[i]] (in T-pose or first frame).
        
        # Let's compute offsets from the CURRENT motion's first frame reconstructed via RIC
        # (which is what T2MGenerator does).
        # Note: We are doing "Direct 6D", so we prefer 6D rotations. 
        # But for the OFFSETS (bone lengths), we need the position data which implies bone lengths.
        # The RIC vector contains local positions! (Indices 4:67).
        # We can just use that.
        
        # Extract Local Positions from RIC (indices 4 : 67)
        # These are local positions relative to root? No, relative to parent?
        # "ric_data" in motion_process is "local joint position". 
        # Actually recover_from_ric documentation: "positions = data[..., 4:(joints_num - 1) * 3 + 4]"
        # Then it does qrot(...) + r_pos.
        # This implies these are relative coordinate differences or something.
        
        # Let's just trust T2MGenerator's method:
        # It calls `recover_from_ric` to get positions, AND THEN uses those positions to calculate offsets 
        # for the Animation object.
        # We can do the same just for offsets, but use OUR rotations for the animation.
        
        from src.data.humanml.scripts.motion_process import recover_from_ric as recover_from_ric_light
        # Note: This returns global positions.
        
        positions_xyz = recover_from_ric_light(data.unsqueeze(0), joints_num).squeeze(0) # (T, 22, 3)
        positions_xyz_np = positions_xyz.cpu().numpy()
        
        # Compute offsets from first frame
        t_pose_pos = positions_xyz_np[0]
        parents = self.t2m_config.parents
        for i in range(22):
            p = parents[i]
            if p == -1:
                offsets[i] = [0,0,0]
            else:
                offsets[i] = t_pose_pos[i] - t_pose_pos[p]
                
        # 7. Create Animation
        anim = Animation(
            rotations=Quaternions(full_quats),
            positions=positions, # (T, 22, 3) - Only root matters usually, but we provide all
            orients=Quaternions.id(22),
            offsets=offsets,
            parents=parents
        )
        
        # 8. Save
        bvh_save(str(output_path), anim, self.t2m_config.joint_names, frametime=1.0/20.0)
        print(f"[LightT2MGenerator] Saved Direct 6D BVH to {output_path}")

