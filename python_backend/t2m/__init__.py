"""
T2M (Text-to-Motion) package for generating BVH motion files from text descriptions.
"""

from .generator import T2MGenerator, generate_motion_from_text, T2MConfig

__version__ = "1.0.0"
__all__ = ["T2MGenerator", "T2MConfig", "generate_motion_from_text"]
