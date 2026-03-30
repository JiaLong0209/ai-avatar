"""
Text-to-Speech service supporting VITS and gTTS providers.
"""

import os
import logging
import tempfile
from typing import Optional, Literal
from pathlib import Path
import sys

from gtts import gTTS

logger = logging.getLogger(__name__)


class TtsProvider:
    """Base class for TTS providers."""
    
    def synthesize(self, text: str, lang: Optional[str] = None) -> bytes:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to synthesize
            lang: Language code
        
        Returns:
            Audio data as bytes
        """
        raise NotImplementedError


class GttsProvider(TtsProvider):
    """gTTS provider implementation."""
    
    def synthesize(self, text: str, lang: Optional[str] = None) -> bytes:
        """Generate speech using gTTS."""
        t = gTTS(text=text, lang=(lang or "zh"))
        tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        try:
            t.save(tmpfile.name)
            with open(tmpfile.name, "rb") as f:
                return f.read()
        finally:
            try:
                os.remove(tmpfile.name)
            except OSError:
                pass


class VitsProvider(TtsProvider):
    """VITS provider implementation."""
    
    def __init__(
        self,
        model_path: str,
        config_path: str,
        default_speaker: str = "default",
        default_speed: float = 1.0,
        default_language: str = "ZH"
    ):
        """
        Initialize VITS provider.
        """
        self.model_path = model_path
        self.config_path = config_path
        self.default_speaker = default_speaker
        self.default_speed = default_speed
        self.default_language = default_language
        self._model = None
        self._hps = None
        self._speaker_ids = None
        self._device = None
        
        # Resolve VITS directory
        model_path_obj = Path(model_path)
        config_path_obj = Path(config_path)
        
        # Try model_path parent first
        vits_dir = str(model_path_obj.parent)
        if not os.path.isdir(vits_dir) and config_path_obj:
            # Try config parent
            vits_dir = str(config_path_obj.parent)
            
        self.vits_dir = os.path.abspath(vits_dir)
        logger.debug(f"[VitsProvider] VITS directory resolved: {self.vits_dir}")
        self._model_module = None # To hold the model class ref if needed
        self._utils_module = None # To hold utils ref

    def _safe_vits_context(self):
        """Context manager for safe VITS imports."""
        import sys
        import contextlib

        @contextlib.contextmanager
        def _context():
            # 1. Add vits_dir to sys.path
            if self.vits_dir not in sys.path:
                sys.path.insert(0, self.vits_dir)
                inserted = True
            else:
                inserted = False
            
            try:
                yield
            finally:
                # 2. Remove vits_dir from sys.path
                if inserted and self.vits_dir in sys.path:
                    sys.path.remove(self.vits_dir)
                
                # 3. CLEANUP: Remove conflicting modules from sys.modules
                # These are the generic names VITS uses that conflict with MoMask
                conflicts = ['utils', 'models', 'commons', 'text', 'monotonic_align']
                for mod_name in conflicts:
                    # Remove top-level modules
                    if mod_name in sys.modules:
                        del sys.modules[mod_name]
                    
                    # Also remove if they are imported as submodules (less likely for root imports but good safety)
                    # We accept that we are forcefully unregistering them. 
                    # If they were loaded previously by something else, we might be breaking that,
                    # but since VITS assumes IT owns 'utils', it's better to reset.
                    pass
        return _context()

    def _load_model(self):
        """Lazy-load VITS model."""
        if self._model is not None:
            return
        
        import torch
        
        # Use safe context to import
        with self._safe_vits_context():
            try:
                import utils
                from models import SynthesizerTrn
                # Check imports
                logger.debug(f"[VitsProvider] Loaded utils from: {utils.__file__}")
                
                self._device = "cuda:0" if torch.cuda.is_available() else "cpu"
                logger.info(f"[VitsProvider] Using device: {self._device}")
                
                # Load config
                self._hps = utils.get_hparams_from_file(self.config_path)
                
                # Load model
                net_g = SynthesizerTrn(
                    len(self._hps.symbols),
                    self._hps.data.filter_length // 2 + 1,
                    self._hps.train.segment_size // self._hps.data.hop_length,
                    n_speakers=self._hps.data.n_speakers,
                    **self._hps.model
                ).to(self._device)
                
                net_g.eval()
                utils.load_checkpoint(self.model_path, net_g, None)
                self._model = net_g
                self._speaker_ids = self._hps.speakers
                
                # Keep references to critical data needed for inference that used to rely on globals or re-imports
                self._symbols = self._hps.symbols
                self._text_cleaners = self._hps.data.text_cleaners
                self._add_blank = self._hps.data.add_blank
                self._sampling_rate = self._hps.data.sampling_rate

                logger.info(f"[VitsProvider] Model loaded successfully. Available speakers: {list(self._speaker_ids.keys())}")
                
            except ImportError as e:
                logger.error(f"[VitsProvider] Failed to load VITS modules: {e}")
                raise

    def _get_text_sequence(self, text: str):
        """Convert text to sequence of token IDs."""
        from torch import LongTensor
        
        # We need imports just for this function too, as they depend on the C++ extensions or logic in those folders
        with self._safe_vits_context():
            from text import text_to_sequence
            import commons
            
            text_norm = text_to_sequence(
                text,
                self._symbols,
                self._text_cleaners
            )
            if self._add_blank:
                text_norm = commons.intersperse(text_norm, 0)
            return LongTensor(text_norm)
    
    def _map_lang_to_vits(self, lang: Optional[str]) -> str:
        """Map language code to VITS language."""
        import config
        cfg = config.get_config()
        
        if not lang:
            return cfg.VITS_DEFAULT_LANGUAGE
        
        lang_lower = lang.lower()
        return cfg.LANG_TO_VITS.get(lang_lower, cfg.VITS_DEFAULT_LANGUAGE)
    
    def synthesize(
        self,
        text: str,
        lang: Optional[str] = None,
        speaker: Optional[str] = None,
        speed: Optional[float] = None
    ) -> bytes:
        """
        Generate speech using VITS.
        """
        self._load_model()
        
        from torch import no_grad, LongTensor
        import soundfile as sf
        import io
        import config
        cfg = config.get_config()
        
        # Use provided or default values
        speaker_name = speaker if speaker is not None else (self.default_speaker or cfg.VITS_DEFAULT_SPEAKER)
        speech_speed = speed if speed is not None else self.default_speed
        vits_lang = self._map_lang_to_vits(lang) or cfg.VITS_DEFAULT_LANGUAGE
        
        # Validate speaker
        if speaker_name not in self._speaker_ids:
            available = list(self._speaker_ids.keys())
            logger.warning(
                f"[VitsProvider] Speaker '{speaker_name}' not found. "
                f"Available: {available}. Using first available speaker."
            )
            speaker_name = available[0] if available else speaker_name
        
        speaker_id = self._speaker_ids[speaker_name]
        
        # Prepare text with language markers
        lang_info = cfg.VITS_LANGUAGES.get(vits_lang, cfg.VITS_LANGUAGES[cfg.VITS_DEFAULT_LANGUAGE])
        text_with_markers = lang_info["mark"] + text + lang_info["mark"]
        
        # Convert text to sequence
        stn_tst = self._get_text_sequence(text_with_markers)
        
        # Synthesize
        with no_grad():
            x_tst = stn_tst.unsqueeze(0).to(self._device)
            x_tst_lengths = LongTensor([stn_tst.size(0)]).to(self._device)
            sid = LongTensor([speaker_id]).to(self._device)
            
            audio = self._model.infer(
                x_tst,
                x_tst_lengths,
                sid=sid,
                noise_scale=0.667,
                noise_scale_w=0.8,
                length_scale=1.0 / speech_speed
            )[0][0, 0].data.cpu().float().numpy()
        
        # Convert to MP3 format
        sampling_rate = self._sampling_rate
        
        # First, write to temporary WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_file:
            wav_path = wav_file.name
            sf.write(wav_path, audio, sampling_rate)
        
        try:
            # Convert WAV to MP3 using pydub (requires ffmpeg)
            from pydub import AudioSegment
            
            audio_segment = AudioSegment.from_wav(wav_path)
            mp3_buffer = io.BytesIO()
            audio_segment.export(mp3_buffer, format="mp3")
            mp3_buffer.seek(0)
            return mp3_buffer.read()
        except ImportError:
            # Fallback: return WAV if pydub not available
            logger.warning("[VitsProvider] pydub not available, returning WAV instead of MP3")
            with open(wav_path, "rb") as f:
                return f.read()
        finally:
            # Clean up temporary WAV file
            try:
                os.remove(wav_path)
            except OSError:
                pass


class TtsService:
    """Unified TTS service supporting multiple providers."""
    
    def __init__(
        self,
        default_provider: Literal["vits", "gtts"] = "vits",
        vits_model_path: Optional[str] = None,
        vits_config_path: Optional[str] = None,
        vits_speaker: Optional[str] = None,
        vits_speed: Optional[float] = None,
        vits_language: Optional[str] = None
    ):
        """
        Initialize TTS service.
        
        Args:
            default_provider: Default provider ("vits" or "gtts")
            vits_model_path: Path to VITS model (if using VITS)
            vits_config_path: Path to VITS config (if using VITS)
            vits_speaker: VITS speaker name
            vits_speed: VITS speech speed
            vits_language: VITS default language
        """
        import config
        cfg = config.get_config()
        
        self.default_provider = default_provider or cfg.DEFAULT_TTS_PROVIDER
        self._vits_provider: Optional[VitsProvider] = None
        self._gtts_provider = GttsProvider()
        
        # Initialize VITS provider if needed
        # if self.default_provider == "vits" or vits_model_path:
        model_path = vits_model_path or cfg.VITS_MODEL_PATH
        config_path = vits_config_path or cfg.VITS_CONFIG_PATH
        speaker = vits_speaker or cfg.VITS_DEFAULT_SPEAKER
        speed = vits_speed if vits_speed is not None else cfg.VITS_DEFAULT_SPEED
        language = vits_language or cfg.VITS_DEFAULT_LANGUAGE
        
        self._vits_provider = VitsProvider(
            model_path=model_path,
            config_path=config_path,
            default_speaker=speaker,
            default_speed=speed,
            default_language=language
        )
    

    def synthesize(
        self,
        text: str,
        lang: Optional[str] = None,
        provider: Optional[Literal["vits", "gtts"]] = None
    ) -> tuple[bytes, str]:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to synthesize
            lang: Language code
            provider: Provider to use ("vits" or "gtts"), defaults to default_provider
        
        Returns:
            Tuple of (audio_bytes, content_type)
        """
        provider = provider or self.default_provider
        
        if provider == "vits":
            if self._vits_provider is None:
                raise RuntimeError("VITS provider not initialized. Check VITS model paths.")
            audio_bytes = self._vits_provider.synthesize(text, lang=lang)
            return audio_bytes, "audio/mpeg"
        elif provider == "gtts":
            audio_bytes = self._gtts_provider.synthesize(text, lang=lang)
            return audio_bytes, "audio/mpeg"
        else:
            raise ValueError(f"Unknown provider: {provider}")


# Global service instance
_service_instance: Optional[TtsService] = None


def get_tts_service() -> TtsService:
    """Get or create global TTS service instance."""
    global _service_instance
    if _service_instance is None:
        import config
        cfg = config.get_config()
        _service_instance = TtsService(default_provider=cfg.DEFAULT_TTS_PROVIDER, vits_model_path=cfg.VITS_MODEL_PATH)
    return _service_instance

