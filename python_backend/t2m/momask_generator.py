
import os
import sys
import torch
import numpy as np
from os.path import join as pjoin
from argparse import Namespace

# Add momask submodule to sys.path
# Removed top-level sys.path hack
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MOMASK_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '../t2m-models/momask'))



# Imports moved to _load_models to avoid namespace conflicts


class MoMaskGenerator:
    def __init__(self, device=None):
        self.device = device if device else torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[MoMaskGenerator] Initializing on {self.device}")
        
        # Hardcoded paths and defaults based on gen_t2m.py and directory structure
        self.checkpoints_dir = os.path.join(MOMASK_DIR, 'checkpoints')
        self.dataset_name = 't2m'
        self.name = 't2m_nlayer8_nhead6_ld384_ff1024_cdp0.1_rvq6ns' # Default from BaseOptions
        # self.vq_name will be loaded from opt.txt
        
        self.clip_version = 'ViT-B/32' # Hardcoded in gen_t2m.py
        
        try:
            self._load_models()
            self.ready = True
        except Exception as e:
            print(f"[MoMaskGenerator] Failed to load models: {e}")
            self.ready = False

    def _load_models(self):
        # Ensure imports are available
        if MOMASK_DIR not in sys.path:
            sys.path.insert(0, MOMASK_DIR)

        # Local imports to prevent namespace pollution
        try:
            from models.mask_transformer.transformer import MaskTransformer, ResidualTransformer
            from models.vq.model import RVQVAE, LengthEstimator
            from utils.get_opt import get_opt
        except ImportError as e:
            # Try to force reload or handle error
            print(f"[MoMaskGenerator] Import failed: {e}. Check sys.path ordering.")
            raise e

        # 1. Load Model Options
        root_dir = pjoin(self.checkpoints_dir, self.dataset_name, self.name)
        model_opt_path = pjoin(root_dir, 'opt.txt')
        if not os.path.exists(model_opt_path):
            raise FileNotFoundError(f"Model config not found at {model_opt_path}")
            
        self.model_opt = get_opt(model_opt_path, device=self.device)
        self.model_opt.checkpoints_dir = self.checkpoints_dir # Ensure absolute path matches this env
        
        # 2. Load VQ Model
        # vq_opt_path = pjoin(self.checkpoints_dir, self.dataset_name, self.model_opt.vq_name, 'opt.txt')
        # MoMask get_opt seems to want device
        # We need to construct vq_opt manually or load it?
        # gen_t2m.py lines 130-133
        vq_opt_path = pjoin(self.checkpoints_dir, self.dataset_name, self.model_opt.vq_name, 'opt.txt')
        self.vq_opt = get_opt(vq_opt_path, device=self.device)
        self.vq_opt.checkpoints_dir = self.checkpoints_dir
        
        # Dim pose: 263 for t2m, 251 for kit. 
        self.dim_pose = 263 # t2m
        self.vq_opt.dim_pose = self.dim_pose
        
        self.vq_model = RVQVAE(self.vq_opt,
                               self.vq_opt.dim_pose,
                               self.vq_opt.nb_code,
                               self.vq_opt.code_dim,
                               self.vq_opt.output_emb_width,
                               self.vq_opt.down_t,
                               self.vq_opt.stride_t,
                               self.vq_opt.width,
                               self.vq_opt.depth,
                               self.vq_opt.dilation_growth_rate,
                               self.vq_opt.vq_act,
                               self.vq_opt.vq_norm)
        
        ckpt = torch.load(pjoin(self.checkpoints_dir, self.dataset_name, self.model_opt.vq_name, 'model', 'net_best_fid.tar'),
                          map_location=self.device) # Removed weights_only=True compatibility issue check?
        model_key = 'vq_model' if 'vq_model' in ckpt else 'net'
        self.vq_model.load_state_dict(ckpt[model_key])
        self.vq_model.to(self.device)
        self.vq_model.eval()
        
        # Update model_opt with vq params
        self.model_opt.num_tokens = self.vq_opt.nb_code
        self.model_opt.num_quantizers = self.vq_opt.nb_code # Wait, gen_t2m line 136 says num_quantizers = vq_opt.num_quantizers
        # Actually line 136: model_opt.num_quantizers = vq_opt.num_quantizers
        self.model_opt.num_quantizers = self.vq_opt.num_quantizers
        self.model_opt.code_dim = self.vq_opt.code_dim
        
        # 3. Load Residual Transformer
        # Default res_name from EvalT2MOptions: 'tres_nlayer8_ld384_ff1024_rvq6ns_cdp0.2_sw'
        res_name = 'tres_nlayer8_ld384_ff1024_rvq6ns_cdp0.2_sw'
        res_opt_path = pjoin(self.checkpoints_dir, self.dataset_name, res_name, 'opt.txt')
        self.res_opt = get_opt(res_opt_path, device=self.device)
        self.res_opt.checkpoints_dir = self.checkpoints_dir
        
        self.res_opt.num_quantizers = self.vq_opt.num_quantizers
        self.res_opt.num_tokens = self.vq_opt.nb_code
        
        self.res_model = ResidualTransformer(code_dim=self.vq_opt.code_dim,
                                             cond_mode='text',
                                             latent_dim=self.res_opt.latent_dim,
                                             ff_size=self.res_opt.ff_size,
                                             num_layers=self.res_opt.n_layers,
                                             num_heads=self.res_opt.n_heads,
                                             dropout=self.res_opt.dropout,
                                             clip_dim=512,
                                             shared_codebook=self.vq_opt.shared_codebook,
                                             cond_drop_prob=self.res_opt.cond_drop_prob,
                                             share_weight=self.res_opt.share_weight,
                                             clip_version=self.clip_version,
                                             opt=self.res_opt)
        
        ckpt = torch.load(pjoin(self.checkpoints_dir, self.dataset_name, res_name, 'model', 'net_best_fid.tar'),
                          map_location=self.device)
        self.res_model.load_state_dict(ckpt['res_transformer'], strict=False)
        self.res_model.to(self.device)
        self.res_model.eval()
        
        # 4. Load Mask Transformer
        self.t2m_transformer = MaskTransformer(code_dim=self.model_opt.code_dim,
                                              cond_mode='text',
                                              latent_dim=self.model_opt.latent_dim,
                                              ff_size=self.model_opt.ff_size,
                                              num_layers=self.model_opt.n_layers,
                                              num_heads=self.model_opt.n_heads,
                                              dropout=self.model_opt.dropout,
                                              clip_dim=512,
                                              cond_drop_prob=self.model_opt.cond_drop_prob,
                                              clip_version=self.clip_version,
                                              opt=self.model_opt)
        
        ckpt = torch.load(pjoin(self.checkpoints_dir, self.dataset_name, self.name, 'model', 'latest.tar'),
                          map_location=self.device)
        model_key = 't2m_transformer' if 't2m_transformer' in ckpt else 'trans'
        self.t2m_transformer.load_state_dict(ckpt[model_key], strict=False)
        self.t2m_transformer.to(self.device)
        self.t2m_transformer.eval()
        
        # 5. Load Length Estimator (Optional, or assume passed length usually? gen_t2m loads it)
        # We'll load it to be safe for defaults
        self.length_estimator = LengthEstimator(512, 50)
        ckpt = torch.load(pjoin(self.checkpoints_dir, self.dataset_name, 'length_estimator', 'model', 'finest.tar'),
                          map_location=self.device)
        self.length_estimator.load_state_dict(ckpt['estimator'])
        self.length_estimator.to(self.device)
        self.length_estimator.eval()
        
        # 6. Load Mean/Std
        self.mean = np.load(pjoin(self.checkpoints_dir, self.dataset_name, self.model_opt.vq_name, 'meta', 'mean.npy'))
        self.std = np.load(pjoin(self.checkpoints_dir, self.dataset_name, self.model_opt.vq_name, 'meta', 'std.npy'))
        
        print("[MoMaskGenerator] All models loaded successfully.")

    def inv_transform(self, data):
        return data * self.std + self.mean

    def generate_motion(self, text_prompt, motion_length=0, max_motion_length=196, repeats=1, use_direct_6d=False):
        """
        Generate motion from text.
        Args:
            text_prompt (str): Text description.
            motion_length (int): Desired length in frames. 0 for auto-estimation.
            max_motion_length (int): Maximum allowed length in frames.
            repeats (int): Number of variations to generate.
            use_direct_6d (bool): Ignored for MoMask.
        Returns:
            motion_xyz (np.ndarray): Shape (Frames, 22, 3) - Raw XYZ positions in METERS.
        """
        if not self.ready:
            raise RuntimeError("MoMask models not initialized properly.")
            
        # Local imports
        import torch.nn.functional as F
        from torch.distributions.categorical import Categorical
        
        captions = [text_prompt] * repeats
        
        # Length estimation
        if motion_length > 0:
            # Explicit length
            length_val = motion_length // 4
            token_lens = torch.LongTensor([length_val] * repeats).to(self.device)
        else:
            # Auto length
            with torch.no_grad():
                text_embedding = self.t2m_transformer.encode_text(captions)
                pred_dis = self.length_estimator(text_embedding)
                probs = F.softmax(pred_dis, dim=-1)
                token_lens = Categorical(probs).sample()
        
        # Clamp length to max
        max_tokens = max(1, max_motion_length // 4)
        token_lens = torch.clamp(token_lens, max=max_tokens)
            
        m_length = token_lens * 4
        
        # Generation Params (Defaults from EvalT2MOptions)
        cond_scale = 4
        temperature = 1.0
        topkr = 0.9
        time_steps = 18
        gumbel_sample = False
        
        with torch.no_grad():
            mids = self.t2m_transformer.generate(captions, token_lens,
                                                timesteps=time_steps,
                                                cond_scale=cond_scale,
                                                temperature=temperature,
                                                topk_filter_thres=topkr,
                                                gsample=gumbel_sample)
            
            # Residual Refinement
            mids = self.res_model.generate(mids, captions, token_lens, temperature=1, cond_scale=5)
            
            # Decode
            pred_motions = self.vq_model.forward_decoder(mids)
            pred_motions = pred_motions.detach().cpu().numpy()
            
            # Inverse Transform
            data = self.inv_transform(pred_motions)
            
        # Process results
        results = []
        for k, joint_data in enumerate(data):
            curr_len = m_length[k]
            joint_data = joint_data[:curr_len]
            # recover_from_ric returns (Len, 22, 3)
            # data is (Batch, Len, Dim)
            from utils.motion_process import recover_from_ric
            
            # recover_from_ric expects torch tensor
            joint = recover_from_ric(torch.from_numpy(joint_data).float(), 22).numpy()
            results.append(joint)
            
        # Return first result if repeats=1, else list?
        # MotionService usually expects one. We'll return the first one for now.
        return results[0]
