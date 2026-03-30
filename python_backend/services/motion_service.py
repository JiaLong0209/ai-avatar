"""
Motion generation service.
Handles motion file generation, format conversion, and file management.
"""

import os
import re
import logging
from typing import Optional, Literal
from pathlib import Path
import base64

from t2m import T2MGenerator, T2MConfig
try:
    from t2m.light_generator import LightT2MGenerator
except ImportError:
    LightT2MGenerator = None
from t2m.momask_generator import MoMaskGenerator
from backend_utils.ik_bvh_converter import convert_xyz_to_bvh
from backend_utils.bvh_converter import convert_bvh_to_fbx

logger = logging.getLogger(__name__)

# Constants
DEFAULT_MOTION_DIR = "tests/motions"
SUPPORTED_FORMATS = ["bvh", "fbx"]


class MotionService:
    """
    Service for motion generation and file management.
    Handles the full pipeline: text -> motion -> BVH -> (optional) FBX
    """
    
    def __init__(
        self,
        t2m_config: Optional[T2MConfig] = None,
        default_motion_dir: str = DEFAULT_MOTION_DIR,
        model_name: str = "t2m-gpt"
    ):
        """
        Initialize motion service.
        
        Args:
            t2m_config: Optional T2M configuration
            default_motion_dir: Default directory for motion files
            model_name: "t2m-gpt", "light-t2m", "momask", or "mdm"
        """
        self.t2m_config = t2m_config
        self.default_motion_dir = default_motion_dir
        self.model_name = model_name
        self._generator = None
        
        logger.info(f"[MotionService] Initialized with model: {self.model_name}")
    
    @property
    def generator(self):
        """Lazy-load T2M generator."""
        if self._generator is None:
            if self.model_name == "light-t2m":
                if LightT2MGenerator is None:
                    raise RuntimeError("LightT2MGenerator not available. Check dependencies.")
                logger.info("Initializing LightT2MGenerator...")
                self._generator = LightT2MGenerator()
            elif self.model_name == "momask":
                logger.info("Initializing MoMaskGenerator...")
                self._generator = MoMaskGenerator()
            elif self.model_name == "mdm":
                raise NotImplementedError("MDM model not implemented yet.")
            else:
                logger.info("Initializing T2MGenerator (T2M-GPT)...")
                self._generator = T2MGenerator(self.t2m_config)
        return self._generator
    
    @staticmethod
    def sanitize_filename(text: str, max_length: int = 50) -> str:
        """
        Sanitize text for use in filename.
        
        Args:
            text: Text to sanitize
            max_length: Maximum length of sanitized text
        
        Returns:
            Sanitized filename-safe string
        """
        sanitized = re.sub(r'[<>:"/\\|?*]', '', text)
        sanitized = re.sub(r'\s+', '_', sanitized)
        sanitized = sanitized.strip('._')
        
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized or "motion"
    
    def generate_file_paths(
        self,
        motion_text: str,
        motion_dir: Optional[str] = None
    ) -> tuple[str, str]:
        """
        Generate BVH and FBX file paths with descriptive naming.
        
        Args:
            motion_text: Motion description text
            motion_dir: Directory to store motion files (defaults to service default)
        
        Returns:
            Tuple of (bvh_path, fbx_path)
        """
        storage_dir = motion_dir or self.default_motion_dir
        os.makedirs(storage_dir, exist_ok=True)
        
        file_hash = abs(hash(motion_text)) % 10000
        sanitized_text = self.sanitize_filename(motion_text, max_length=50)
        base_name = f"motion_{file_hash}_{sanitized_text}"
        
        bvh_path = os.path.join(storage_dir, f"{base_name}.bvh")
        fbx_path = os.path.join(storage_dir, f"{base_name}.fbx")
        
        return bvh_path, fbx_path
    
    @staticmethod
    def validate_format(format_str: str) -> Literal["bvh", "fbx"]:
        """
        Validate and normalize output format.
        
        Args:
            format_str: Format string to validate
        
        Returns:
            Normalized format ('bvh' or 'fbx')
        """
        normalized = format_str.lower() if format_str else "fbx"
        return normalized if normalized in SUPPORTED_FORMATS else "fbx"
    
    def generate_motion_file(
        self,
        motion_text: str,
        output_format: str = "fbx",
        motion_dir: Optional[str] = None,
        use_direct_6d: bool = False
    ) -> tuple[str, str]:
        """
        Generate motion file from text description.
        
        Args:
            motion_text: Motion description text
            output_format: Desired format ('fbx' or 'bvh')
            motion_dir: Directory to store motion files
            use_direct_6d: Ignored now. We enforce XYZ output for consistency with new converter.
        
        Returns:
            Tuple of (file_path, file_base64)
        
        Raises:
            RuntimeError: If motion generation or conversion fails
        """
        output_format = self.validate_format(output_format)
        bvh_path, fbx_path = self.generate_file_paths(motion_text, motion_dir)
        
        # Generate motion positions - Force output to be XYZ positions to work with centralized IK
        # Note: use_direct_6d=False forces T2M-GPT to return XYZ
        # Prepare length constraints based on model
        import config as app_config
        
        motion_len = 0
        max_motion_len = 196
        
        if self.model_name == "momask":
            motion_len = app_config.T2M_MOMASK_LENGTH
            max_motion_len = app_config.T2M_MOMASK_MAX_LENGTH
        elif self.model_name == "t2m-gpt": # or default
            motion_len = app_config.T2M_GPT_LENGTH
            max_motion_len = app_config.T2M_GPT_MAX_LENGTH
            
        logger.info(f"[MotionService] Generating motion from text: {motion_text} (Model: {self.model_name}, Len: {motion_len}, Max: {max_motion_len})")
        motion_data = self.generator.generate_motion(
            motion_text, 
            motion_length=motion_len, 
            max_motion_length=max_motion_len,
            use_direct_6d=False
        )
        
        # Ensure motion_data is numpy array
        if hasattr(motion_data, 'cpu'): 
            motion_data = motion_data.cpu().numpy()
            
        # Convert to BVH using centralized converter (MoMask IK)
        logger.debug(f"[MotionService] Converting to BVH using IK Converter: {bvh_path}")
        convert_xyz_to_bvh(motion_data, bvh_path, foot_ik=True)
        
        # Convert to requested format
        if output_format == "fbx":
            logger.debug(f"[MotionService] Converting BVH to FBX: {fbx_path}")
            success = convert_bvh_to_fbx(bvh_path, fbx_path)
            if not success:
                # Clean up BVH on failure
                try:
                    os.remove(bvh_path)
                except OSError:
                    pass
                raise RuntimeError("Failed to convert BVH to FBX. Check if converter is available.")
            final_path = fbx_path
        else:
            final_path = bvh_path
        
        # Read file and encode to base64
        try:
            with open(final_path, "rb") as f:
                file_bytes = f.read()
            file_b64 = base64.b64encode(file_bytes).decode("utf-8")
            return final_path, file_b64
        except Exception as e:
            raise RuntimeError(f"Failed to read generated motion file: {str(e)}") from e
    
    def generate_motion_file_with_cleanup(
        self,
        motion_text: str,
        output_format: str = "fbx",
        motion_dir: Optional[str] = None,
        save_temp_files: bool = True,
        use_direct_6d: bool = False
    ) -> tuple[str, str]:
        """
        Generate motion file with optional cleanup of temporary files.
        
        Note: If save_temp_files=False, files are deleted after encoding to base64.
        This is useful for returning base64 data without keeping files on disk.
        
        Args:
            motion_text: Motion description text
            output_format: Desired format ('fbx' or 'bvh')
            motion_dir: Directory to store motion files
            save_temp_files: Whether to save temporary files (if False, files are deleted after reading)
            use_direct_6d: Whether to use direct 6D rotation method
        
        Returns:
            Tuple of (file_path, file_base64)
        """
        output_format = self.validate_format(output_format)
        bvh_path, fbx_path = self.generate_file_paths(motion_text, motion_dir)
        
        try:
            file_path, file_b64 = self.generate_motion_file(motion_text, output_format, motion_dir, use_direct_6d=use_direct_6d)
            
            # Clean up intermediate files if not saving
            if not save_temp_files:
                # Clean up intermediate BVH if FBX was the final format
                if output_format == "fbx" and bvh_path != file_path:
                    try:
                        if os.path.exists(bvh_path):
                            os.remove(bvh_path)
                    except OSError:
                        pass
                
                # Clean up final file after encoding
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except OSError:
                    pass
            
            return file_path, file_b64
            
        except Exception:
            # Clean up on error if not saving
            if not save_temp_files:
                for cleanup_file in [bvh_path, fbx_path]:
                    try:
                        if os.path.exists(cleanup_file):
                            os.remove(cleanup_file)
                    except OSError:
                        pass
            raise


# Global service instance (lazy-loaded)
_service_instance: Optional[MotionService] = None


def get_motion_service(
    t2m_config: Optional[T2MConfig] = None,
    default_motion_dir: str = DEFAULT_MOTION_DIR,
    model_name: str = "t2m-gpt"
) -> MotionService:
    """
    Get or create global motion service instance.
    
    Args:
        t2m_config: Optional T2M configuration
        default_motion_dir: Default directory for motion files
        model_name: Name of the model to use
    
    Returns:
        MotionService instance
    """
    global _service_instance
    # Re-initialize if model_name changes (simple approach) or just verify consistency
    if _service_instance is None or _service_instance.model_name != model_name:
        _service_instance = MotionService(t2m_config, default_motion_dir, model_name=model_name)
    return _service_instance

