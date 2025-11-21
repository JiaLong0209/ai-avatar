from fastapi import FastAPI, Form, Query, Response, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Literal
import tempfile
import os
import re
import logging
from gtts import gTTS
import ollama
from t2m import T2MGenerator, T2MConfig
from backend_utils.bvh_converter import convert_bvh_to_fbx_external
import base64


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


app = FastAPI()

# 使用するモデル
MODEL_NAME = "gemma3:4b"
# MODEL_NAME = "llama3:8b"
default_stt_lang = "zh"

class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class ChatPayload(BaseModel):
    # Backward-compat: accept a single message
    message: Optional[str] = None
    # New: accept full message history
    messages: Optional[List[ChatMessage]] = None

def _tts_mp3_bytes(text: str, lang: Optional[str]) -> bytes:
    t = gTTS(text=text, lang=(lang or "zh"))
    tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    t.save(tmpfile.name)
    with open(tmpfile.name, "rb") as f:
        data = f.read()
    return data

@app.get("/tts")
async def tts_get(text: str = Query(...), lang: Optional[str] = Query(None), format: Optional[str] = Query("mp3")):
    fmt = (format or "mp3").lower()
    if fmt == "mp3":
        data = _tts_mp3_bytes(text, lang)
        return Response(content=data, media_type="audio/mpeg")
    else:
        # For now only mp3 implemented fully; extend as needed
        data = _tts_mp3_bytes(text, lang)
        return Response(content=data, media_type="audio/mpeg")

@app.post("/tts")
async def tts_post(text: str = Form(...), lang: Optional[str] = Form(None), format: Optional[str] = Form("mp3")):
    fmt = (format or "mp3").lower()
    if fmt == "mp3":
        data = _tts_mp3_bytes(text, lang)
        return Response(content=data, media_type="audio/mpeg")
    else:
        data = _tts_mp3_bytes(text, lang)
        return Response(content=data, media_type="audio/mpeg")

@app.post("/chat")
async def chat(payload: ChatPayload):
    logger.debug(f"Chat payload received: message={payload.message}, messages={payload.messages}")
    # Build message list beginning with a system prompt to answer in Traditional Chinese
    compiled_messages: List[dict] = [
        {"role": "system", "content": "請使用繁體中文回答，並且簡短回覆，使用可愛的語氣"}
    ]

    logger.debug(f"Full payload: {payload}")
    if payload.messages and len(payload.messages) > 0:
        compiled_messages.extend(
            [{"role": m.role, "content": m.content} for m in payload.messages]
        )
    elif payload.message is not None:
        compiled_messages.append({"role": "user", "content": payload.message})
    else:
        # Fallback empty prompt (unlikely in normal use)
        compiled_messages.append({"role": "user", "content": ""})

    response = ollama.chat(
        model=MODEL_NAME,
        messages=compiled_messages,
    )

    # Ollama の返答内容を抽出
    answer = response["message"]["content"]
    return {"response": answer}

# ========= STT (Whisper / Faster-Whisper) =========
# Lazy-load backends to avoid import errors if packages are missing
_openai_whisper = None
_faster_model = None

def _load_whisper_backends():
    global _openai_whisper, _faster_model
    if _openai_whisper is None and _faster_model is None:
        try:
            import whisper as _w  # openai-whisper
            if hasattr(_w, "load_model"):
                _openai_whisper = _w
        except Exception:
            _openai_whisper = None
        if _openai_whisper is None:
            try:
                from faster_whisper import WhisperModel  # type: ignore
                model_size = os.getenv("WHISPER_MODEL", "base")
                _faster_model = WhisperModel(model_size)
            except Exception:
                _faster_model = None


def _transcribe_audio(path: str, language: str = "zh") -> str:
    _load_whisper_backends()
    if _openai_whisper is not None:
        model_size = os.getenv("WHISPER_MODEL", "base")
        model = _openai_whisper.load_model(model_size)
        result = model.transcribe(path, language=language)
        return result.get("text", "")
    if _faster_model is not None:
        segments, info = _faster_model.transcribe(path, language=language)
        parts = []
        for seg in segments:
            parts.append(seg.text)
        return " ".join(parts).strip()
    raise RuntimeError("No Whisper backend available. Install openai-whisper or faster-whisper.")


@app.post("/stt")
async def stt(file: UploadFile = File(...), lang: Optional[str] = Query("zh")):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        text = _transcribe_audio(tmp_path, language=(lang or default_stt_lang))
        return {"text": text}
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

# ========= T2M (Text-to-Motion) =========
_t2m_generator = None
DEFAULT_MOTION_DIR = "tests/motions"


def _get_t2m_generator():
    """Lazy-load T2M generator to avoid initialization overhead."""
    global _t2m_generator
    if _t2m_generator is None:
        config = T2MConfig(
            vqvae_path='T2M-GPT-main/pretrained/VQVAE/net_last.pth',
            transformer_path='T2M-GPT-main/pretrained/VQTransformer_corruption05/net_best_fid.pth',
            meta_path='T2M-GPT-main/checkpoints/t2m/VQVAEV3_CB1024_CMT_H1024_NRES3/meta/'
        )
        _t2m_generator = T2MGenerator(config)
    return _t2m_generator


def _sanitize_filename(text: str, max_length: int = 50) -> str:
    """
    Sanitize text for use in filename.
    
    Args:
        text: Text to sanitize
        max_length: Maximum length of sanitized text
    
    Returns:
        Sanitized filename-safe string
    """
    # Remove or replace invalid filename characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '', text)
    sanitized = re.sub(r'\s+', '_', sanitized)  # Replace spaces with underscores
    sanitized = sanitized.strip('._')  # Remove leading/trailing dots and underscores
    
    # Limit length and ensure it's not empty
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    if not sanitized:
        sanitized = "motion"
    
    return sanitized


def _ensure_motion_directory(motion_dir: str = DEFAULT_MOTION_DIR) -> None:
    """Ensure motion directory exists, create if it doesn't."""
    os.makedirs(motion_dir, exist_ok=True)


def _generate_motion_filename(motion_text: str, output_format: str, motion_dir: str = DEFAULT_MOTION_DIR) -> tuple[str, str]:
    """
    Generate motion file paths with descriptive naming.
    
    Args:
        motion_text: Motion description text
        output_format: Desired format ('fbx' or 'bvh')
        motion_dir: Directory to store motion files
    
    Returns:
        Tuple of (bvh_path, fbx_path)
    """
    _ensure_motion_directory(motion_dir)
    
    # Generate hash and sanitized text for filename
    file_hash = abs(hash(motion_text)) % 10000
    sanitized_text = _sanitize_filename(motion_text, max_length=50)
    
    # Create descriptive filename: motion_{hash}_{sanitized_text}.{ext}
    base_name = f"motion_{file_hash}_{sanitized_text}"
    bvh_path = os.path.join(motion_dir, f"{base_name}.bvh")
    fbx_path = os.path.join(motion_dir, f"{base_name}.fbx")
    
    return bvh_path, fbx_path


@app.post("/t2m")
async def t2m(
    text: str = Form(...),
    format: str = Form("fbx"),
    save_temp_files: bool = Form(True),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Generate motion file from text description. Supports BVH and FBX formats.
    
    Args:
        text: Motion description text
        format: Output format ('fbx' or 'bvh'), default 'fbx'
        save_temp_files: Whether to save temporary motion files, default True
    """
    try:
        logger.info(f"[t2m] Motion text: {text}")
        
        # Validate and normalize format
        output_format = format.lower()
        if output_format not in ["bvh", "fbx"]:
            output_format = "fbx"
        
        # Generate file paths with descriptive naming
        bvh_path, fbx_path = _generate_motion_filename(text, output_format)
        
        # Generate motion
        generator = _get_t2m_generator()
        motion_xyz = generator.generate_motion(text)
        
        # Always generate BVH first (required for FBX conversion)
        generator.motion_to_bvh(motion_xyz, bvh_path)
        
        # Convert to requested format
        if output_format == "fbx":
            success = convert_bvh_to_fbx_external(bvh_path, fbx_path)
            if not success:
                # Clean up on failure
                try:
                    os.remove(bvh_path)
                except:
                    pass
                raise HTTPException(
                    status_code=500,
                    detail="Failed to convert BVH to FBX. Check if converter is available."
                )
            
            # Schedule cleanup if not saving temp files
            if not save_temp_files:
                background_tasks.add_task(os.remove, bvh_path)
                background_tasks.add_task(os.remove, fbx_path)
            
            return FileResponse(
                path=fbx_path,
                media_type="application/octet-stream",
                filename=os.path.basename(fbx_path)
            )
        else:
            # Return BVH file
            if not save_temp_files:
                background_tasks.add_task(os.remove, bvh_path)
            
            return FileResponse(
                path=bvh_path,
                media_type="application/octet-stream",
                filename=os.path.basename(bvh_path)
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[t2m] Generation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate motion: {str(e)}"
        )


class ChatT2MRequest(BaseModel):
    payload: Optional[ChatPayload] = None
    t2m_text: Optional[str] = None
    format: Optional[str] = "fbx"
    save_temp_files: Optional[bool] = True
    motion_dir: Optional[str] = None  # Defaults to DEFAULT_MOTION_DIR if None


def _extract_user_input(payload: Optional[ChatPayload]) -> Optional[str]:
    """Extract the most recent user input from chat payload."""
    if not payload:
        return None
    
    if payload.messages:
        # Find the last user message
        for message in reversed(payload.messages):
            if message.role == "user":
                return message.content
    elif payload.message:
        return payload.message
    
    return None


def _generate_motion_description_from_chat(user_input: str, chat_history: Optional[List[dict]] = None) -> str:
    """
    Use LLM to generate a concise English motion description from user input.
    
    Args:
        user_input: The user's input text (e.g., LLM response or user message)
        chat_history: Optional chat history for context
    
    Returns:
        English motion description suitable for 3D motion generation
    """
    # Build message history if provided
    messages: List[dict] = []
    if chat_history:
        messages.extend(chat_history)
    
    # Create a focused instruction for motion description generation
    motion_instruction = (
        "You are a motion description generator. Convert the given text into a concise, "
        "clear English motion description suitable for 3D human motion generation.\n\n"
        "Requirements:\n"
        "- Use simple, action-focused language (e.g., 'a person waves their hand', 'someone jumps happily')\n"
        "- Keep it under 25 words\n"
        "- Focus on body movements and gestures\n"
        "- Do not include dialogue, emotions without motion, or non-physical actions\n"
        "- Output only the motion description, nothing else\n\n"
        f"Input text: {user_input}\n\n"
        "Motion description:"
    )
    
    messages.append({"role": "system", "content": motion_instruction})
    
    response = ollama.chat(model=MODEL_NAME, messages=messages)
    motion_text = response["message"]["content"].strip()
    
    # Clean up common LLM artifacts
    motion_text = motion_text.strip('"\'')
    if motion_text.lower().startswith("motion description:"):
        motion_text = motion_text[len("motion description:"):].strip()
    
    logger.info(f"[chat_t2m] Generated motion text: {motion_text}")
    return motion_text


def _generate_motion_file(
    motion_text: str,
    output_format: str,
    save_temp_files: bool = True,
    motion_dir: Optional[str] = None
) -> tuple[str, str]:
    """
    Generate motion file from description text.
    
    Args:
        motion_text: English motion description
        output_format: Desired format ('fbx' or 'bvh')
        save_temp_files: Whether to save temporary motion files, default True
        motion_dir: Directory to store motion files, defaults to DEFAULT_MOTION_DIR
    
    Returns:
        Tuple of (file_path, file_base64)
    """
    # Validate and normalize format
    output_format = output_format.lower()
    if output_format not in ["fbx", "bvh"]:
        output_format = "fbx"
    
    # Use provided directory or default
    storage_dir = motion_dir if motion_dir else DEFAULT_MOTION_DIR
    
    # Generate file paths with descriptive naming
    bvh_path, fbx_path = _generate_motion_filename(motion_text, output_format, storage_dir)
    
    # Generate motion
    generator = _get_t2m_generator()
    motion_xyz = generator.generate_motion(motion_text)
    
    # Generate BVH file (required as intermediate format)
    generator.motion_to_bvh(motion_xyz, bvh_path)
    
    # Convert to requested format
    if output_format == "fbx":
        success = convert_bvh_to_fbx_external(bvh_path, fbx_path)
        if not success:
            # Clean up BVH file on failure
            try:
                os.remove(bvh_path)
            except:
                pass
            raise HTTPException(
                status_code=500,
                detail="Failed to convert BVH to FBX. Check if converter is available."
            )
        
        final_path = fbx_path
        
        # Clean up intermediate BVH if not saving temp files
        if not save_temp_files:
            try:
                os.remove(bvh_path)
            except:
                pass
    else:
        final_path = bvh_path
    
    # Read file and encode to base64
    try:
        with open(final_path, "rb") as f:
            file_bytes = f.read()
        file_b64 = base64.b64encode(file_bytes).decode("utf-8")
        
        # Clean up final file if not saving temp files
        if not save_temp_files:
            try:
                os.remove(final_path)
            except:
                pass
        
        return final_path, file_b64
    except Exception as e:
        # Clean up on error
        if not save_temp_files:
            try:
                if output_format == "fbx" and os.path.exists(bvh_path):
                    os.remove(bvh_path)
                if os.path.exists(final_path):
                    os.remove(final_path)
            except:
                pass
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read generated motion file: {str(e)}"
        )


@app.post("/chat_t2m")
async def chat_t2m(req: ChatT2MRequest):
    """
    Generate motion from text description or chat context.
    
    This endpoint accepts either:
    - Direct motion description in `t2m_text`
    - Chat context in `payload` which will be processed to extract/generate motion description
    
    Args:
        req: Request containing payload, t2m_text, format, save_temp_files, and motion_dir
    
    Returns:
        Motion file as base64 along with metadata (motion_text, format, file_name, file_base64)
    """
    try:
        # Step 1: Determine motion description text
        # Always generate motion description from context, even if t2m_text is provided
        # (t2m_text might be the LLM response in Chinese, not a motion description)
        
        # Build chat history from payload if available
        chat_history: List[dict] = []
        if req.payload and req.payload.messages:
            chat_history = [{"role": m.role, "content": m.content} for m in req.payload.messages]
        
        # Determine input text for motion generation
        user_input = None
        
        # If t2m_text is provided, use it as the primary input (usually LLM response)
        if req.t2m_text:
            user_input = req.t2m_text
            logger.debug(f"[chat_t2m] Using provided t2m_text as input: {user_input}")
        else:
            # Otherwise, extract from payload
            user_input = _extract_user_input(req.payload)
        
        if not user_input:
            raise HTTPException(
                status_code=400,
                detail="Either 't2m_text' or valid 'payload' with user input is required"
            )
        
        # Always generate motion description from the input (converts LLM response to motion description)
        motion_text = _generate_motion_description_from_chat(user_input, chat_history)
        
        if not motion_text:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate motion description from input"
            )
        
        # Log motion text for debugging
        logger.info(f"[chat_t2m] Motion text: {motion_text}")
        
        # Step 2: Generate motion file
        output_format = (req.format or "fbx").lower()
        if output_format not in ["fbx", "bvh"]:
            output_format = "fbx"
        
        save_temp_files = req.save_temp_files if req.save_temp_files is not None else True
        motion_dir = req.motion_dir if req.motion_dir else None
        
        file_path, file_b64 = _generate_motion_file(
            motion_text,
            output_format,
            save_temp_files=save_temp_files,
            motion_dir=motion_dir
        )
        
        return {
            "motion_text": motion_text,
            "format": output_format,
            "file_name": os.path.basename(file_path),
            "file_base64": file_b64,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[chat_t2m] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"chat_t2m failed: {str(e)}"
        )
