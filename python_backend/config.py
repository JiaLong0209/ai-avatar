"""
Configuration class for the AI Desk Avatar backend.
Loads configuration from config.yaml with environment variable overrides.
"""

import os
import yaml
from typing import Optional, Dict, Any
from pathlib import Path


from dotenv import load_dotenv

class Config:
    """Configuration class for the application."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration from YAML file with environment variable overrides.
        
        Args:
            config_path: Path to config.yaml file (defaults to config.yaml in same directory)
        """
        # Load .env file if it exists
        load_dotenv()
        
        # Determine config file path
        if config_path is None:
            config_path = Path(__file__).parent / "config.yaml"
        else:
            config_path = Path(config_path)
        
        # Load YAML config
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                self._yaml_config = yaml.safe_load(f) or {}
        else:
            self._yaml_config = {}
            print(f"Warning: Config file not found at {config_path}, using defaults and environment variables only.")
        
        # Load configuration with environment variable overrides
        self._load_config()
    
    def _load_config(self):
        """Load all configuration values with environment variable overrides."""
        # ========= Model Configuration =========
        self.LLM_PROVIDER = os.getenv(
            "LLM_PROVIDER",
            self._get_nested("llm.provider", "ollama")
        )
        self.LLM_MODEL_NAME = os.getenv(
            "LLM_MODEL_NAME",
            self._get_nested("llm.model_name", "gemma3:4b")
        )
        
        # Gemini Configuration
        self.GEMINI_MODEL_NAME = os.getenv(
            "GEMINI_MODEL_NAME",
            self._get_nested("llm.gemini.model_name", "gemini-2.0-flash")
        )
        self.GOOGLE_API_KEY = os.getenv(
            "GOOGLE_API_KEY",
            self._get_nested("llm.gemini.api_key", "")
        )
        
        # ========= Language Configuration =========
        self.DEFAULT_STT_LANG = os.getenv(
            "DEFAULT_STT_LANG",
            self._get_nested("language.default_stt", "zh")
        )
        self.DEFAULT_TTS_LANG = os.getenv(
            "DEFAULT_TTS_LANG",
            self._get_nested("language.default_tts", "zh")
        )
        
        # ========= Chat Prompts =========
        self.CHAT_SYSTEM_PROMPT = os.getenv(
            "CHAT_SYSTEM_PROMPT",
            self._get_nested(
                "chat.system_prompt",
                "你是一位專業的體操選手，性格陽光、專注且充滿能量。你對身體素質、訓練細節和體操動作非常熱愛。請使用繁體中文回答，並且簡短回覆，使用可愛的語氣。"
            )
        )
        
        self.MOTION_DESCRIPTION_PROMPT = os.getenv(
            "MOTION_DESCRIPTION_PROMPT",
            self._get_nested(
                "chat.motion_description_prompt",
                """You are a motion description generator. Convert the given text into a concise, clear English motion description suitable for 3D human motion generation.

Requirements:
- Use simple, action-focused language (e.g., 'a person waves their hand', 'someone jumps happily')
- Keep it under 25 words
- Focus on body movements, poses, and gestures
- NO FACIAL EXPRESSIONS: Do not include words like 'smiles', 'laughs', 'looks sad', or 'blushes'. The model only generates body motion.
- Do not include dialogue, emotions without motion, or non-physical actions
- Output only the motion description, nothing else

Input text: {user_input}

Motion description:"""
            )
        )
        
        self.CHAT_AND_MOTION_PROMPT = os.getenv(
            "CHAT_AND_MOTION_PROMPT",
            self._get_nested(
                "chat.chat_and_motion_prompt",
                """You are a professional gymnast representing a 3D Avatar.
You are athletic, energetic, and love talking about training and performing gymnastic moves.
You must output ONLY a valid JSON object with EXACTLY two keys: "reply" and "motion_text".

Rules for "reply":
- 必須使用「繁體中文」。
- 以體操選手的身份回覆，語氣充滿朝氣。
- 回答必須「簡短」，控制在兩句話以內，適合語音播放。
- 禁止使用Emoji (如 😀)，因為語音念出來會很怪。
- 請多多使用「顏文字」(如 OuO、>w<、(｀・ω・´)) 來表達心情。
- 像好朋友一樣輕鬆聊天。

Rules for "motion_text":
- Must be a short English sentence describing your physical body movement while saying the reply.
- NO FACIAL EXPRESSIONS: Do not use words like "smiles", "laughs", "appears sad". T2M model only supports body poses.
- Format: "A person [action]." (e.g. "A person waves their hand.", "A person nods their head.", "A person walks forward.")
- Keep it under 15 words.

Example output format (JSON ONLY):
{
  "reply": "你好呀！很高興見到你 OuO",
  "motion_text": "A person waves their right hand enthusiastically."
}"""
            )
        )
        
        # ========= T2M Configuration =========
        self.T2M_VQVAE_PATH = os.getenv(
            "T2M_VQVAE_PATH",
            self._get_nested(
                "t2m.vqvae_path",
                "t2m-models/T2M-GPT-main/pretrained/VQVAE/net_last.pth"
            )
        )
        self.T2M_TRANSFORMER_PATH = os.getenv(
            "T2M_TRANSFORMER_PATH",
            self._get_nested(
                "t2m.transformer_path",
                "t2m-models/T2M-GPT-main/pretrained/VQTransformer_corruption05/net_best_fid.pth"
            )
        )
        self.T2M_META_PATH = os.getenv(
            "T2M_META_PATH",
            self._get_nested(
                "t2m.meta_path",
                "t2m-models/T2M-GPT-main/checkpoints/t2m/VQVAEV3_CB1024_CMT_H1024_NRES3/meta/"
            )
        )
        
        # Load Model-Specific configs
        t2m_models = self._get_nested("t2m.models", {})
        
        # MoMask
        self.T2M_MOMASK_LENGTH = int(t2m_models.get("momask", {}).get("motion_length", 0))
        self.T2M_MOMASK_MAX_LENGTH = int(t2m_models.get("momask", {}).get("max_motion_length", 196))
        
        # T2M-GPT
        self.T2M_GPT_LENGTH = int(t2m_models.get("t2m_gpt", {}).get("motion_length", 0))
        self.T2M_GPT_MAX_LENGTH = int(t2m_models.get("t2m_gpt", {}).get("max_motion_length", 196))
        
        # ========= VITS TTS Configuration =========
        vits_model_dir = os.getenv(
            "VITS_MODEL_DIR",
            self._get_nested("vits.model_dir", "vits")
        )
        self.VITS_MODEL_DIR = vits_model_dir
        
        self.VITS_MODEL_PATH = os.getenv(
            "VITS_MODEL_PATH",
            self._get_nested(
                "vits.model_path",
                str(Path(vits_model_dir) / "G_latest.pth")
            )
        )
        self.VITS_CONFIG_PATH = os.getenv(
            "VITS_CONFIG_PATH",
            self._get_nested(
                "vits.config_path",
                str(Path(vits_model_dir) / "config.json")
            )
        )
        self.VITS_DEFAULT_SPEAKER = os.getenv(
            "VITS_DEFAULT_SPEAKER",
            self._get_nested("vits.default_speaker", "default")
        )
        self.VITS_DEFAULT_SPEED = float(os.getenv(
            "VITS_DEFAULT_SPEED",
            str(self._get_nested("vits.default_speed", 1.0))
        ))
        self.VITS_DEFAULT_LANGUAGE = os.getenv(
            "VITS_DEFAULT_LANGUAGE",
            self._get_nested("vits.default_language", "ZH")
        )
        
        # VITS Language mapping
        vits_languages = self._get_nested("vits.languages", {})
        self.VITS_LANGUAGES: Dict[str, Dict[str, str]] = {
            "JA": vits_languages.get("JA", {"name": "日本語", "mark": "[JA]", "code": "ja"}),
            "ZH": vits_languages.get("ZH", {"name": "简体中文", "mark": "[ZH]", "code": "zh-CN"}),
            "EN": vits_languages.get("EN", {"name": "English", "mark": "[EN]", "code": "en"}),
        }
        
        # Language code to VITS language mapping
        lang_mapping = self._get_nested("vits.lang_mapping", {})
        self.LANG_TO_VITS: Dict[str, str] = {
            "zh": lang_mapping.get("zh", "ZH"),
            "zh-CN": lang_mapping.get("zh-CN", "ZH"),
            "zh-TW": lang_mapping.get("zh-TW", "ZH"),
            "ja": lang_mapping.get("ja", "JA"),
            "jpn": lang_mapping.get("jpn", "JA"),
            "en": lang_mapping.get("en", "EN"),
            "eng": lang_mapping.get("eng", "EN"),
        }
        
        # ========= Motion Configuration =========
        self.DEFAULT_MOTION_DIR = os.getenv(
            "DEFAULT_MOTION_DIR",
            self._get_nested("motion.default_dir", "tests/motions")
        )
        
        # ========= TTS Provider Configuration =========
        self.DEFAULT_TTS_PROVIDER = os.getenv(
            "DEFAULT_TTS_PROVIDER",
            self._get_nested("tts.default_provider", "vits")
        )

        # ========= External Tools =========
        self.BLENDER_PATH = os.getenv(
            "BLENDER_PATH",
            self._get_nested(
                "tools.blender_path",
                "/home/jialong/applications/blender-4.2.0-linux-x64/blender"
            )
        )
    
    def _get_nested(self, key_path: str, default: Any = None) -> Any:
        """
        Get nested value from YAML config using dot notation.
        
        Args:
            key_path: Dot-separated path (e.g., "llm.model_name")
            default: Default value if key not found
        
        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self._yaml_config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value if value is not None else default


# Global config instance
_config_instance: Optional[Config] = None


def get_config(config_path: Optional[str] = None) -> Config:
    """
    Get or create global configuration instance.
    
    Args:
        config_path: Optional path to config.yaml file
    
    Returns:
        Config instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_path)
    return _config_instance


# Create a global config instance for backward compatibility
# Access config values via: config.LLM_MODEL_NAME, config.DEFAULT_STT_LANG, etc.
_config = get_config()

# Export all config attributes at module level for backward compatibility
LLM_PROVIDER = _config.LLM_PROVIDER
LLM_MODEL_NAME = _config.LLM_MODEL_NAME
GEMINI_MODEL_NAME = _config.GEMINI_MODEL_NAME
GOOGLE_API_KEY = _config.GOOGLE_API_KEY
DEFAULT_STT_LANG = _config.DEFAULT_STT_LANG
DEFAULT_TTS_LANG = _config.DEFAULT_TTS_LANG
CHAT_SYSTEM_PROMPT = _config.CHAT_SYSTEM_PROMPT
MOTION_DESCRIPTION_PROMPT = _config.MOTION_DESCRIPTION_PROMPT
CHAT_AND_MOTION_PROMPT = _config.CHAT_AND_MOTION_PROMPT
T2M_VQVAE_PATH = _config.T2M_VQVAE_PATH
T2M_TRANSFORMER_PATH = _config.T2M_TRANSFORMER_PATH
T2M_META_PATH = _config.T2M_META_PATH
T2M_MOMASK_LENGTH = _config.T2M_MOMASK_LENGTH
T2M_MOMASK_MAX_LENGTH = _config.T2M_MOMASK_MAX_LENGTH
T2M_GPT_LENGTH = _config.T2M_GPT_LENGTH
T2M_GPT_MAX_LENGTH = _config.T2M_GPT_MAX_LENGTH
VITS_MODEL_DIR = _config.VITS_MODEL_DIR
VITS_MODEL_PATH = _config.VITS_MODEL_PATH
VITS_CONFIG_PATH = _config.VITS_CONFIG_PATH
VITS_DEFAULT_SPEAKER = _config.VITS_DEFAULT_SPEAKER
VITS_DEFAULT_SPEED = _config.VITS_DEFAULT_SPEED
VITS_DEFAULT_LANGUAGE = _config.VITS_DEFAULT_LANGUAGE
VITS_LANGUAGES = _config.VITS_LANGUAGES
LANG_TO_VITS = _config.LANG_TO_VITS
DEFAULT_MOTION_DIR = _config.DEFAULT_MOTION_DIR
DEFAULT_TTS_PROVIDER = _config.DEFAULT_TTS_PROVIDER
BLENDER_PATH = _config.BLENDER_PATH
