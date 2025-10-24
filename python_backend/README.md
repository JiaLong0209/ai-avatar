# AI Desk Avatar - Python Backend

A multimodal AI backend system that provides chat, speech-to-text, text-to-speech, and text-to-motion capabilities for Unity-based virtual avatars.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Quick Start](#quick-start)
- [API Endpoints](#api-endpoints)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

This backend provides RESTful APIs for:
- **Chat**: LLM-powered conversations using Ollama
- **STT**: Speech-to-text transcription using Whisper
- **TTS**: Text-to-speech synthesis using gTTS
- **T2M**: Text-to-motion generation using T2M-GPT (BVH/FBX animation)

## ✨ Features

- 🔄 **Multimodal AI**: Voice, text, and motion generation
- 🎭 **VRM Support**: Animation ready for Unity VRM models
- 🌐 **RESTful API**: FastAPI-based endpoints
- 💾 **Memory Management**: User name persistence and chat history
- 🎨 **Motion Generation**: Text-to-animation with BVH/FBX export

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Poetry
- Ollama (for LLM)
- Blender (for BVH→FBX conversion, optional)

### 1. Install Dependencies

```bash
cd python_backend
poetry install --no-root
poetry shell
```

### 2. Setup Ollama

```bash
# Install Ollama (Arch Linux)
yay -S ollama

# Start Ollama service
sudo systemctl enable ollama
sudo systemctl start ollama

# Pull model
ollama pull gemma3:4b
```

### 3. Run the Server

```bash
poetry run uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Test the API

```bash
# Test chat endpoint
curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Hello!"}'
```

## 📡 API Endpoints

### Chat (`POST /chat`)
Generate AI responses with conversation context.

**Request:**
```json
{
  "message": "Hello!",
  "messages": [
    {"role": "user", "content": "Hi"},
    {"role": "assistant", "content": "Hello!"}
  ]
}
```

**Response:**
```json
{
  "response": "你好！有什麼我可以幫忙的嗎？😊"
}
```

### Speech-to-Text (`POST /stt`)
Transcribe audio to text using Whisper.

**Request:** Form-data with `file` (WAV audio)

**Response:**
```json
{
  "text": "轉錄的文字內容"
}
```

### Text-to-Speech (`POST /tts`)
Synthesize speech from text using gTTS.

**Request:** Form-data with `text` and optional `lang`

**Response:** MP3 audio file

### Text-to-Motion (`POST /t2m`)
Generate motion animation from text description.

**Request:** Form-data with `text` and `format` (bvh/fbx)

**Response:** BVH or FBX animation file

```bash
# Get BVH file
curl -X POST http://localhost:8000/t2m \
     -F "text=a person is walking" \
     -F "format=bvh" \
     --output motion.bvh

# Get FBX file
curl -X POST http://localhost:8000/t2m \
     -F "text=a girl waves her hand happily" \
     -F "format=fbx" \
     --output motion.fbx
```

## 🛠️ Installation

### Poetry Management

```bash
# Install dependencies
poetry install --no-root

# Activate virtual environment
poetry shell

# Run commands
poetry run uvicorn app:app --reload

# Update dependencies
poetry update

# Check environment
poetry env info
```

### Optional Dependencies

#### Whisper (for STT)
```bash
# Option 1: OpenAI Whisper
pip install openai-whisper

# Option 2: Faster-Whisper (recommended)
pip install faster-whisper
```

#### T2M-GPT Setup
1. Clone T2M-GPT repository to `T2M-GPT-main/`
2. Download pretrained models to `T2M-GPT-main/pretrained/`
3. Set model paths in `app.py` configuration

## 📁 Project Structure

```
python_backend/
├── app.py                 # FastAPI main application
├── pyproject.toml         # Poetry dependencies
├── run.sh                 # Server startup script
│
├── t2m/                   # Text-to-Motion package
│   ├── __init__.py
│   └── generator.py      # T2M core logic
│
├── backend_utils/         # Backend utilities
│   ├── __init__.py
│   └── bvh_converter.py  # BVH→FBX conversion
│
├── tests/                 # Test files
│   ├── stt.sh            # STT test script
│   ├── tts.sh            # TTS test script
│   └── t2m.sh            # T2M test script
│
└── T2M-GPT-main/         # T2M-GPT models (external)
    ├── pretrained/
    └── checkpoints/
```

## ⚙️ Configuration

### Environment Variables

```bash
# Whisper model size
export WHISPER_MODEL=base  # tiny, base, small, medium, large

# Default STT language
default_stt_lang=zh  # zh, ja, en, etc.
```

### Model Configuration

Edit `app.py` to configure:

```python
# LLM Model
MODEL_NAME = "gemma3:4b"  # or "llama3:8b"

# T2M Model Paths
vqvae_path = 'T2M-GPT-main/pretrained/VQVAE/net_last.pth'
transformer_path = 'T2M-GPT-main/pretrained/VQTransformer_corruption05/net_best_fid.pth'
meta_path = 'T2M-GPT-main/checkpoints/t2m/VQVAEV3_CB1024_CMT_H1024_NRES3/meta/'
```

## 🧪 Testing

### Test STT
```bash
cd tests
./stt.sh
```

### Test TTS
```bash
./tts.sh
```

### Test T2M
```bash
./t2m.sh
```

### Using httpie (recommended)
```bash
# Chat
http POST localhost:8000/chat message="你好"

# TTS
http GET 'localhost:8000/tts?text=你好，世界&lang=zh' --download

# T2M
http -f POST localhost:8000/t2m text="a person walks" format=fbx --download
```

## 🔧 Troubleshooting

### Poetry Environment Issues

```bash
# Remove corrupted environment
poetry env info --path
poetry env remove python

# Or manually
rm -rf $(poetry env info --path)

# Reinstall
poetry install --no-root
```

### Port Already in Use

```bash
# Find and kill process on port 8000
lsof -ti:8000 | xargs kill -9
```

### Ollama Connection Error

```bash
# Check Ollama service
sudo systemctl status ollama

# Restart service
sudo systemctl restart ollama

# Verify model
ollama list
```

### Blender Not Found (for FBX conversion)

```bash
# Check Blender installation
which blender

# Or specify path in code
blender_path = "/usr/bin/blender"
```

## 📚 System Architecture

```
┌─────────────────────┐
│   Unity Frontend    │
│   (VRM Avatar)      │
└──────────┬──────────┘
           │ HTTP/REST
           ▼
┌─────────────────────┐
│   Python Backend    │
│   (FastAPI)         │
└──────────┬──────────┘
           │
           ├─► Ollama (LLM)
           ├─► Whisper (STT)
           ├─► gTTS (TTS)
           └─► T2M-GPT (Motion)
```

## 🌐 Integration with Unity

### Unity → Python Communication

The Unity frontend communicates with this backend via REST APIs:

1. **Chat**: User text → `/chat` → AI response
2. **Voice**: Audio recording → `/stt` → Transcribed text
3. **Motion**: Text description → `/t2m` → BVH/FBX animation
4. **Speech**: Text → `/tts` → MP3 audio

### Example Unity Integration

```csharp
// Send motion request
var form = new WWWForm();
form.AddField("text", "a person waves");
var request = UnityWebRequest.Post("http://localhost:8000/t2m", form);
yield return request.SendWebRequest();

// Handle FBX/BVH response
byte[] motionData = request.downloadHandler.data;
File.WriteAllBytes("motion.fbx", motionData);
```

## 📝 License

This project is part of the AI Desk Avatar system. See main repository for license information.

## 🤝 Contributing

Contributions are welcome! Please ensure:
- Add tests for new features
- Update documentation as needed

## 🔗 Related Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Ollama Documentation](https://ollama.ai/docs)
- [T2M-GPT Repository](https://github.com/EricGuo5513/T2M-GPT)
- [UniVRM Unity Package](https://github.com/vrm-c/UniVRM)

---

**Happy coding! 🎉**