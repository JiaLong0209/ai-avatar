from fastapi import FastAPI, Form, Query, Response, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Literal
import tempfile
import os
from gtts import gTTS
import ollama
from t2m import T2MGenerator, T2MConfig
from backend_utils.bvh_converter import convert_bvh_to_fbx_external


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
    print(f"payload: message={payload.message} messages={payload.messages}")
    # Build message list beginning with a system prompt to answer in Traditional Chinese
    compiled_messages: List[dict] = [
        {"role": "system", "content": "請使用繁體中文回答，並且簡短回覆，使用可愛的語氣"}
    ]

    print(f"payload: {payload}")
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

def _get_t2m_generator():
    global _t2m_generator
    if _t2m_generator is None:
        # Adjust paths relative to the backend directory
        config = T2MConfig(
            vqvae_path='T2M-GPT-main/pretrained/VQVAE/net_last.pth',
            transformer_path='T2M-GPT-main/pretrained/VQTransformer_corruption05/net_best_fid.pth',
            meta_path='T2M-GPT-main/checkpoints/t2m/VQVAEV3_CB1024_CMT_H1024_NRES3/meta/'
        )
        _t2m_generator = T2MGenerator(config)
    return _t2m_generator


@app.post("/t2m")
async def t2m(text: str = Form(...), format: str = Form("fbx"), background_tasks: BackgroundTasks = BackgroundTasks()):
    """Generate motion file from text description. Supports BVH and FBX formats."""
    
    save_file = True
    try:
        generator = _get_t2m_generator()
        
        # Generate motion data
        motion_xyz = generator.generate_motion(text)
        
        # Determine output format and file paths
        output_format = format.lower()
        if output_format not in ["bvh", "fbx"]:
            output_format = "fbx"
        
        # Create output file paths
        bvh_path = f"tests/temp_motion_{hash(text) % 10000}.bvh"
        fbx_path = f"tests/temp_motion_{hash(text) % 10000}.fbx"

        # Always generate BVH first (required for FBX conversion)
        generator.motion_to_bvh(motion_xyz, bvh_path)
        
        # Convert to FBX if requested
        if output_format == "fbx":
            success = convert_bvh_to_fbx_external(bvh_path, fbx_path)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to convert BVH to FBX")
            
            # Clean up BVH file if FBX was requested
            if not save_file:
                background_tasks.add_task(os.remove, bvh_path)
            
            return FileResponse(
                path=fbx_path,
                media_type="application/octet-stream",
                filename=f"motion_{hash(text) % 10000}.fbx"
            )
        else:
            # Return BVH file
            if not save_file:
                background_tasks.add_task(os.remove, bvh_path)
            
            return FileResponse(
                path=bvh_path,
                media_type="application/octet-stream",
                filename=f"motion_{hash(text) % 10000}.bvh"
            )
        
    except Exception as e:
        print(f"T2M generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate motion: {str(e)}")
