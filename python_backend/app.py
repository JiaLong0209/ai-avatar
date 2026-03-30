from fastapi import FastAPI, Form, Query, Response, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Literal
import tempfile
import os
import logging
import time
from functools import wraps

from t2m import T2MConfig
from services.motion_service import get_motion_service, MotionService
from services.tts_service import get_tts_service, TtsService
import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

# --- LLM Provider Setup ---
import ollama
genai = None
try:
    import google.generativeai as _genai
    genai = _genai
    logger.info("Successfully imported google.generativeai")
except ImportError as e:
    logger.error(f"Failed to import google.generativeai: {e}")
except Exception as e:
    logger.error(f"Unexpected error importing google.generativeai: {e}")

# --- CONFIGURATION ---
USE_DIRECT_6D_METHOD = False  # Set to True to use 6D rotation direct conversion, False for Analytical IK
# USE_DIRECT_6D_METHOD = True  

# Options: "t2m-gpt", "light-t2m", "mdm", "momask"
# ACTIVE_T2M_MODEL = "t2m-gpt" 
# ACTIVE_T2M_MODEL = "mdm" 
ACTIVE_T2M_MODEL = "momask" 

app = FastAPI()

logger.info(f"USE_DIRECT_6D_METHOD: {USE_DIRECT_6D_METHOD}")
logger.info(f"ACTIVE_T2M_MODEL: {ACTIVE_T2M_MODEL}")

class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class ChatPayload(BaseModel):
    """Chat payload with message history."""
    message: Optional[str] = None  # Backward-compat: single message
    messages: Optional[List[ChatMessage]] = None  # Full message history


# ========= Decorators =========
def log_execution_time(endpoint_name: str):
    """Decorator to log endpoint execution time."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                elapsed = time.time() - start_time
                logger.info(f"{endpoint_name}: executed in {elapsed:.3f}s")
        return wrapper
    return decorator

# ========= TTS (Text-to-Speech) =========
@app.get("/tts")
@log_execution_time("/tts [GET]")
async def tts_get(
    text: str = Query(...),
    lang: Optional[str] = Query(None),
    provider: Optional[str] = Query(None),
    format: Optional[str] = Query(None)
):
    """
    Generate speech audio from text (GET).
    
    Args:
        text: Text to synthesize
        lang: Language code (defaults to configured default)
        provider: TTS provider ("vits" or "gtts"), defaults to configured default
        format: Output format (deprecated, auto-detected from provider)
    
    Returns:
        Audio response
    """
    tts_service = get_tts_service()
    provider_type: Optional[Literal["vits", "gtts"]] = (
        provider.lower() if provider else None
    )
    
    try:
        audio_bytes, content_type = tts_service.synthesize(
            text=text,
            lang=lang or config.DEFAULT_TTS_LANG,
            provider=provider_type
        )
        return Response(content=audio_bytes, media_type=content_type)
    except Exception as e:
        logger.error(f"[tts] Generation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate speech: {str(e)}"
        )


@app.post("/tts")
@log_execution_time("/tts [POST]")
async def tts_post(
    text: str = Form(...),
    lang: Optional[str] = Form(None),
    provider: Optional[str] = Form(None),
    format: Optional[str] = Form(None)
):
    """
    Generate speech audio from text (POST).
    
    Args:
        text: Text to synthesize
        lang: Language code (defaults to configured default)
        provider: TTS provider ("vits" or "gtts"), defaults to configured default (VITS)
        format: Output format (deprecated, auto-detected from provider)
    
    Returns:
        Audio response
    """
    tts_service = get_tts_service()
    provider_type: Optional[Literal["vits", "gtts"]] = (
        provider.lower() if provider else None
    )
    
    try:
        audio_bytes, content_type = tts_service.synthesize(
            text=text,
            lang=lang or config.DEFAULT_TTS_LANG,
            provider=provider_type
        )
        return Response(content=audio_bytes, media_type=content_type)
    except Exception as e:
        logger.error(f"[tts] Generation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate speech: {str(e)}"
        )

# ========= Helpers =========
def _log_full_context(endpoint_tag: str, messages: List[dict]):
    """
    Log the full chat context in a structured, readable format.
    """
    log_lines = [f"\n=== [{endpoint_tag}] Full Context Start ==="]
    for i, msg in enumerate(messages):
        role = msg.get("role", "unknown").upper()
        content = msg.get("content", "").strip()
        # Truncate very long content for readability if needed, but user asked for full context.
        # We'll keep it full but indented.
        log_lines.append(f"[{i}] {role}: {content}")
    log_lines.append(f"=== [{endpoint_tag}] Full Context End ===\n")
    logger.info("\n".join(log_lines))
    
def _get_llm_response(compiled_messages: List[dict]) -> str:
    """Helper to get response from configured LLM provider."""
    provider = config.LLM_PROVIDER.lower()
    
    if provider == "gemini":
        if not genai:
            raise RuntimeError("Gemini SDK (google-generativeai) not installed")
        if not config.GOOGLE_API_KEY:
            raise RuntimeError("GOOGLE_API_KEY not configured")
        
        genai.configure(api_key=config.GOOGLE_API_KEY)
        model = genai.GenerativeModel(config.GEMINI_MODEL_NAME)
        
        # Convert messages to Gemini format
        # Gemini usually expects a specific history format or a flattened string for simple calls.
        # We'll use the ChatSession for history.
        
        if not compiled_messages:
            return "No messages provided"
            
        # Separate the last message as the "prompt/trigger"
        # Everything else is history or system instructions
        trigger_msg = compiled_messages[-1]
        history_msgs = compiled_messages[:-1]
        
        system_instruction = ""
        history = []
        
        for msg in history_msgs:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                system_instruction += content + "\n"
            elif role == "user":
                history.append({"role": "user", "parts": [content]})
            elif role == "assistant":
                history.append({"role": "model", "parts": [content]})
        
        # If the trigger message is also a system message, add it to instructions
        # and use a generic prompt if no other content. But usually we want 
        # the trigger message's content to be the send_message argument.
        prompt = trigger_msg["content"]
        if trigger_msg["role"] == "system":
            # If the last message is system, we treat it as the instruction to be executed
            # against the cumulative history. In Gemini, this is effectively a user prompt 
            # saying "Hey system, do this based on above".
            pass 
        
        # We use simple generate_content with system prompt prepended for now, 
        # or use system_instruction if the model supports it (Gemini 1.5+ does)
        try:
            # Try with system_instruction (available in newer SDKs/Models)
            model_with_sys = genai.GenerativeModel(
                model_name=config.GEMINI_MODEL_NAME,
                system_instruction=system_instruction.strip()
            )
            
            chat_session = model_with_sys.start_chat(history=history)
            response = chat_session.send_message(prompt)
            return response.text
                
        except Exception as e:
            logger.warning(f"Gemini system_instruction failed or not supported: {e}. Falling back to prefixing.")
            # Fallback for models that don't support system_instruction
            full_prompt = f"System Instruction: {system_instruction}\n\nTask: {prompt}"
            
            chat_session = model.start_chat(history=history)
            response = chat_session.send_message(full_prompt)
            return response.text

    else: # Default to Ollama
        response = ollama.chat(model=config.LLM_MODEL_NAME, messages=compiled_messages)
        return response["message"]["content"]


# ========= Chat =========
@app.post("/chat")
@log_execution_time("/chat")
async def chat(payload: ChatPayload):
    """
    Chat endpoint for LLM conversation.
    
    Args:
        payload: Chat payload with message or message history
    
    Returns:
        LLM response
    """
    logger.debug(f"Chat payload received: message={payload.message}, messages={payload.messages}")
    
    # Build message list with system prompt
    compiled_messages: List[dict] = [
        {"role": "system", "content": config.CHAT_SYSTEM_PROMPT}
    ]
    
    # Add user messages
    if payload.messages and len(payload.messages) > 0:
        compiled_messages.extend(
            [{"role": m.role, "content": m.content} for m in payload.messages]
        )
    elif payload.message is not None:
        compiled_messages.append({"role": "user", "content": payload.message})
    else:
        compiled_messages.append({"role": "user", "content": ""})
    
    
    # 3. Log the full context before sending to LLM
    _log_full_context("chat", compiled_messages)

    # 4. Get LLM response
    answer = _get_llm_response(compiled_messages)
    
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
@log_execution_time("/stt")
async def stt(file: UploadFile = File(...), lang: Optional[str] = Query("zh")):
    """Speech-to-text endpoint."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    
    try:
        text = _transcribe_audio(tmp_path, language=(lang or config.DEFAULT_STT_LANG))
        return {"text": text}
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

# ========= T2M (Text-to-Motion) =========
def _get_motion_service() -> MotionService:
    """Get configured motion service instance."""
    t2m_config = T2MConfig(
        vqvae_path=config.T2M_VQVAE_PATH,
        transformer_path=config.T2M_TRANSFORMER_PATH,
        meta_path=config.T2M_META_PATH
    )
    return get_motion_service(
        t2m_config=t2m_config, 
        default_motion_dir=config.DEFAULT_MOTION_DIR,
        model_name=ACTIVE_T2M_MODEL
    )


@app.post("/t2m")
@log_execution_time("/t2m")
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
    
    Returns:
        FileResponse with motion file
    """
    try:
        logger.info(f"[t2m] Motion text: {text}")
        motion_service = _get_motion_service()
        output_format = motion_service.validate_format(format)
        
        # Get file paths for cleanup if needed
        bvh_path, fbx_path = motion_service.generate_file_paths(text)
        final_path = fbx_path if output_format == "fbx" else bvh_path
        
        # Generate motion file (no cleanup - we handle it with background tasks)
        file_path, _ = motion_service.generate_motion_file(
            motion_text=text,
            output_format=output_format,
            use_direct_6d=USE_DIRECT_6D_METHOD
        )
        
        # Schedule cleanup if not saving temp files
        if not save_temp_files:
            background_tasks.add_task(_cleanup_file, file_path)
            # Also clean up intermediate BVH if FBX was generated
            if output_format == "fbx" and bvh_path != file_path:
                background_tasks.add_task(_cleanup_file, bvh_path)
        
        return FileResponse(
            path=file_path,
            media_type="application/octet-stream",
            filename=os.path.basename(file_path)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[t2m] Generation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate motion: {str(e)}"
        )


def _cleanup_file(file_path: str) -> None:
    """Helper to safely remove a file."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except OSError:
        pass


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
    motion_instruction = config.MOTION_DESCRIPTION_PROMPT.format(user_input=user_input)
    messages.append({"role": "system", "content": motion_instruction})
    
    # Log full context
    _log_full_context("chat_t2m", messages)
    
    motion_text = _get_llm_response(messages)
    motion_text = motion_text.strip()
    
    # Clean up common LLM artifacts
    motion_text = motion_text.strip('"\'')
    if motion_text.lower().startswith("motion description:"):
        motion_text = motion_text[len("motion description:"):].strip()
    
    logger.info(f"[chat_t2m] Generated motion_text: {motion_text}")
    return motion_text


# ========= Chat T2M =========

@app.post("/chat_t2m")
@log_execution_time("/chat_t2m")
async def chat_t2m(req: ChatT2MRequest):
    """
    Generate motion from text description or chat context.
    
    This endpoint accepts either:
    - Direct motion description in `t2m_text`
    - Chat context in `payload` which will be processed to extract/generate motion description
    
    Args:
        req: Request containing payload, t2m_text, format, save_temp_files, and motion_dir
    
    Returns:
        Motion file as base64 along with metadata
    """
    try:
        # Step 1: Extract user input and build chat history
        chat_history: List[dict] = []
        if req.payload and req.payload.messages:
            chat_history = [{"role": m.role, "content": m.content} for m in req.payload.messages]
        
        user_input = req.t2m_text or _extract_user_input(req.payload)
        if not user_input:
            raise HTTPException(
                status_code=400,
                detail="Either 't2m_text' or valid 'payload' with user input is required"
            )
        
        # Step 2: Generate motion description from input (converts LLM response to motion description)
        start_step2 = time.time()
        # Logging handled inside _generate_motion_description_from_chat now
        motion_text = _generate_motion_description_from_chat(user_input, chat_history)
        logger.info(f"[chat_t2m] LLM Motion Description duration: {time.time() - start_step2:.4f}s")
        if not motion_text:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate motion description from input"
            )
        
        logger.info(f"[chat_t2m] Motion text: {motion_text}")
        
        # Step 3: Generate motion file
        start_step3 = time.time()
        motion_service = _get_motion_service()
        output_format = motion_service.validate_format(req.format or "fbx")
        save_temp_files = req.save_temp_files if req.save_temp_files is not None else True
        
        file_path, file_b64 = motion_service.generate_motion_file_with_cleanup(
            motion_text=motion_text,
            output_format=output_format,
            motion_dir=req.motion_dir,
            save_temp_files=save_temp_files,
            use_direct_6d=USE_DIRECT_6D_METHOD
        )
        logger.info(f"[chat_t2m] T2M Generation duration: {time.time() - start_step3:.4f}s")
        
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

