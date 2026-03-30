# AI Desk Avatar - Python Backend

A multimodal AI backend system that provides chat, speech-to-text, text-to-speech, and text-to-motion capabilities for Unity-based virtual avatars.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [API Endpoints](#api-endpoints)
- [Systemd Service](#systemd-service)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

This backend provides RESTful APIs for:
- **Chat**: LLM-powered conversations using Ollama
- **STT**: Speech-to-text transcription using Whisper
- **TTS**: Text-to-speech synthesis using VITS (default) or gTTS
- **T2M**: Text-to-motion generation using T2M-GPT (BVH/FBX animation)

## ✨ Features

- 🔄 **Multimodal AI**: Voice, text, and motion generation
- 🎭 **VRM Support**: Animation ready for Unity VRM models
- 🌐 **RESTful API**: FastAPI-based endpoints
- 💾 **Memory Management**: User name persistence and chat history
- 🎨 **Motion Generation**: Text-to-animation with BVH/FBX export
- 🎤 **VITS TTS**: High-quality neural TTS with multiple languages
- 📝 **YAML Configuration**: Centralized configuration management

## 📦 Prerequisites

### Required Software

- **Python 3.10+** (3.11 recommended)
- **Poetry** (dependency management)
- **Ollama** (for LLM chat)
- **ffmpeg** (for MP3 audio conversion)
- **Blender** (optional, for BVH→FBX conversion)

### Required Models and Data

1. **T2M-GPT Models**: 
   - Clone the [T2M-GPT repository](https://github.com/EricGuo5513/T2M-GPT) to `t2m-models/T2M-GPT-main/`
   - Download pretrained models and place them in the `t2m-models/T2M-GPT-main` directory structure:
     - VQVAE: `t2m-models/T2M-GPT-main/pretrained/VQVAE/net_last.pth`
     - Transformer: `t2m-models/T2M-GPT-main/pretrained/VQTransformer_corruption05/net_best_fid.pth`
     - Metadata: `t2m-models/T2M-GPT-main/checkpoints/t2m/VQVAEV3_CB1024_CMT_H1024_NRES3/meta/`
   - See [T2M-GPT README](https://github.com/EricGuo5513/T2M-GPT) for detailed setup instructions

2. **VITS TTS Models** (optional, for TTS):
   - Place VITS model files in `clean_vits/`:
     - `G_latest.pth` (generator model)
     - `config.json` (model configuration)
   - If not available, the system will fall back to gTTS

3. **Ollama Models**:
   - Install and pull a model: `ollama pull gemma3:4b` (or `llama3:8b`)

## 🚀 Installation

### 1. Install System Dependencies

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3.11 python3-pip ffmpeg blender

# Arch Linux
sudo pacman -S python python-pip ffmpeg blender
yay -S ollama  # or use official installer

# macOS
brew install python@3.11 ffmpeg blender
brew install ollama
```

### 2. Install Python Dependencies

```bash
cd python_backend
poetry install --no-root
poetry shell
```

### 3. Setup Ollama

```bash
# Install Ollama (if not already installed)
# Arch Linux: yay -S ollama
# Or use official installer: https://ollama.ai

# Start Ollama service
sudo systemctl enable ollama
sudo systemctl start ollama

# Pull a model
ollama pull gemma3:4b
# or
ollama pull llama3:8b
```

### 4. Configure the Backend

Edit `config.yaml` to set your preferences:

```yaml
llm:
  model_name: "gemma3:4b"  # or "llama3:8b"

t2m:
  vqvae_path: "T2M-GPT-main/pretrained/VQVAE/net_last.pth"
  transformer_path: "T2M-GPT-main/pretrained/VQTransformer_corruption05/net_best_fid.pth"
  meta_path: "T2M-GPT-main/checkpoints/t2m/VQVAEV3_CB1024_CMT_H1024_NRES3/meta/"

vits:
  model_dir: "clean_vits"
  model_path: "clean_vits/G_latest.pth"
  config_path: "clean_vits/config.json"
```

### 5. Run the Server

```bash
# Development mode (with auto-reload)
./run.sh

# Or manually
poetry run uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

The server will be available at `http://localhost:8000`

## ⚙️ Configuration

### Configuration File (`config.yaml`)

All configuration is managed through `config.yaml`. Key sections:

- **llm**: LLM model settings
- **language**: Default STT/TTS languages
- **chat**: System prompts and motion description templates
- **t2m**: T2M-GPT model paths
- **vits**: VITS TTS model settings
- **motion**: Motion file storage directory
- **tts**: Default TTS provider (vits or gtts)

### Environment Variables (Override YAML)

You can override any YAML setting using environment variables:

```bash
export LLM_MODEL_NAME="llama3:8b"
export DEFAULT_TTS_PROVIDER="gtts"
export VITS_MODEL_DIR="/path/to/vits/models"
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

**Request:** Form-data with `file` (WAV audio) and optional `lang` parameter

**Response:**
```json
{
  "text": "轉錄的文字內容"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/stt \
     -F "file=@audio.wav" \
     -F "lang=zh"
```

### Text-to-Speech (`POST /tts` or `GET /tts`)

Synthesize speech from text using VITS (default) or gTTS.

**Request Parameters:**
- `text` (required): Text to synthesize
- `lang` (optional): Language code (defaults to configured default)
- `provider` (optional): `"vits"` or `"gtts"` (defaults to configured default, usually "vits")
- `format` (optional, deprecated): Auto-detected from provider

**Response:** MP3 audio file (or WAV if pydub/ffmpeg unavailable)

**Examples:**
```bash
# POST request (recommended)
curl -X POST http://localhost:8000/tts \
     -F "text=你好，世界" \
     -F "lang=zh" \
     -F "provider=vits" \
     --output speech.mp3

# GET request
curl "http://localhost:8000/tts?text=Hello%20World&lang=en&provider=gtts" \
     --output speech.mp3
```

**VITS Usage Notes:**
- VITS supports multiple languages: `ZH` (Chinese), `JA` (Japanese), `EN` (English)
- Language is auto-detected from `lang` parameter
- Requires `clean_vits/G_latest.pth` and `clean_vits/config.json`
- Falls back to gTTS if VITS model not available
- Output is MP3 format (requires ffmpeg)

### Text-to-Motion (`POST /t2m`)

Generate motion animation from text description.

**Request:** Form-data with:
- `text` (required): Motion description (e.g., "a person walks")
- `format` (optional): `"bvh"` or `"fbx"` (default: `"fbx"`)
- `save_temp_files` (optional): `true` or `false` (default: `true`)

**Response:** BVH or FBX animation file

**Example:**
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

### Chat-to-Motion (`POST /chat_t2m`)

Generate motion from chat context or LLM response. This endpoint intelligently converts conversational text (e.g., LLM responses in Chinese) into English motion descriptions suitable for 3D animation.

**Request:**
```json
{
  "payload": {
    "messages": [
      {"role": "user", "content": "你好"},
      {"role": "assistant", "content": "你好！有什麼我可以幫你的嗎？"}
    ]
  },
  "t2m_text": "你好！有什麼我可以幫你的嗎？",
  "format": "fbx",
  "save_temp_files": true,
  "motion_dir": "tests/motions"
}
```

**Request Parameters:**
- `payload` (optional): Chat history with messages array
- `t2m_text` (optional): Direct text input (usually LLM response)
- `format` (optional): `"bvh"` or `"fbx"` (default: `"fbx"`)
- `save_temp_files` (optional): Whether to save temporary files (default: `true`)
- `motion_dir` (optional): Directory to save motion files (default: configured `DEFAULT_MOTION_DIR`)

**Response:**
```json
{
  "motion_text": "a person waves their hand happily",
  "format": "fbx",
  "file_name": "motion_123_a_person_waves_their_hand_happily.fbx",
  "file_base64": "base64_encoded_file_content..."
}
```

**How it works:**
1. Accepts either `t2m_text` (direct input) or extracts from `payload.messages`
2. Uses LLM to convert the input (which may be in Chinese or conversational) into a concise English motion description
3. Generates motion file using the motion description
4. Returns base64-encoded file along with the generated motion text

**Example:**
```bash
curl -X POST http://localhost:8000/chat_t2m \
     -H "Content-Type: application/json" \
     -d '{
       "t2m_text": "沒問題呀！😊 請問有什麼我可以幫你的嗎？",
       "format": "fbx",
       "save_temp_files": true
     }' \
     --output response.json

# Extract and save the motion file
cat response.json | jq -r '.file_base64' | base64 -d > motion.fbx
```

**Use Cases:**
- Chain chat response → motion generation automatically
- Convert conversational responses to motion descriptions
- Generate contextual motions based on chat history

## 🔧 Systemd Service

### Setup Systemd Service

1. **Copy the service file** (adjust paths as needed):
```bash
sudo cp ai-avatar.service /etc/systemd/system/
```

2. **Edit the service file** to match your user and paths:
```bash
sudo nano /etc/systemd/system/ai-avatar.service
```

Update these lines:
- `User=your_username`
- `Group=your_group`
- `WorkingDirectory=/path/to/python_backend`
- `ExecStart=/path/to/python_backend/run.sh`
- Log file paths

3. **Reload systemd and enable the service**:
```bash
# Reload systemd configuration
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable ai-avatar

# Start the service
sudo systemctl start ai-avatar

# Check status
sudo systemctl status ai-avatar
```

### Service Management

```bash
# Start service
sudo systemctl start ai-avatar

# Stop service
sudo systemctl stop ai-avatar

# Restart service
sudo systemctl restart ai-avatar

# View logs
sudo journalctl -u ai-avatar -f

# Or view log file directly
tail -f /home/jialong/Programming/ai-desk-avatar/python_backend/server.log
```

### Logging

The service logs to:
- **Systemd journal**: `sudo journalctl -u ai-avatar`
- **Log file**: `python_backend/server.log` (configured in `run.sh`)

Log rotation is handled automatically by the `run.sh` script (rotates at ~10MB).

## 📁 Project Structure

```
python_backend/
├── app.py                 # FastAPI main application
├── config.py             # Configuration loader (YAML)
├── config.yaml            # Configuration file
├── pyproject.toml         # Poetry dependencies
├── run.sh                 # Server startup script
├── ai-avatar.service      # Systemd service file
│
├── services/              # Service layer
│   ├── motion_service.py  # Motion generation service
│   └── tts_service.py     # TTS service (VITS/gTTS)
│
├── t2m/                   # Text-to-Motion package
│   ├── __init__.py
│   └── generator.py      # T2M core logic
│
├── Motion/                # Motion processing library
│   ├── Animation.py      # Animation data structures
│   ├── InverseKinematics.py  # IK solver
│   └── BVH.py            # BVH file I/O
│
├── backend_utils/         # Backend utilities
│   ├── __init__.py
│   └── bvh_converter.py  # BVH→FBX conversion (Blender)
│
├── clean_vits/            # VITS TTS models (optional)
│   ├── G_latest.pth
│   └── config.json
│
├── tests/                 # Test files
│   ├── stt.sh            # STT test script
│   ├── tts.sh            # TTS test script
│   └── t2m.sh            # T2M test script
│
└── t2m-models/           # T2M Model Repositories
    ├── T2M-GPT-main/     # T2M-GPT (Git Submodule/Clone)
    ├── momask/           # MoMask (Git Submodule/Clone)
    └── light-t2m-main/   # Light-T2M (Git Submodule/Clone)
├── vits/                 # VITS TTS models (optional)
│   ├── G_latest.pth
│   └── config.json
│
```

## 🧪 Testing

### Test Chat
```bash
curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "你好"}'
```

### Test STT
```bash
cd tests
./stt.sh
```

### Test TTS
```bash
# Test VITS
curl -X POST http://localhost:8000/tts \
     -F "text=你好，世界" \
     -F "provider=vits" \
     --output test_vits.mp3

# Test gTTS
curl -X POST http://localhost:8000/tts \
     -F "text=Hello World" \
     -F "provider=gtts" \
     --output test_gtts.mp3
```

### Test T2M
```bash
./tests/t2m.sh
```

### Test Chat-to-Motion
```bash
curl -X POST http://localhost:8000/chat_t2m \
     -H "Content-Type: application/json" \
     -d '{
       "t2m_text": "你好！很高興見到你",
       "format": "fbx"
     }'
```

### Using httpie (recommended)
```bash
# Install httpie
pip install httpie

# Chat
http POST localhost:8000/chat message="你好"

# TTS
http POST localhost:8000/tts text="你好，世界" lang=zh provider=vits --download

# T2M
http -f POST localhost:8000/t2m text="a person walks" format=fbx --download

# Chat-to-Motion
http POST localhost:8000/chat_t2m t2m_text="很高興見到你" format=fbx
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

# Test connection
ollama run gemma3:4b "Hello"
```

### Blender Not Found (for FBX conversion)

```bash
# Check Blender installation
which blender

# Or specify path in backend_utils/bvh_converter.py
blender_path = "/usr/bin/blender"
```

### VITS TTS Not Working

```bash
# Check if VITS model files exist
ls -la clean_vits/G_latest.pth
ls -la clean_vits/config.json

# Check if ffmpeg is installed (required for MP3)
which ffmpeg

# If VITS fails, it will automatically fall back to gTTS
# Check logs for details
tail -f server.log
```

### Rebuild VITS (if your OS is not Linux)

```bash
# 在專案根目錄 (python_backend 資料夾) 執行：
poetry add cython --group dev
# 或者如果你的 dependencies 已經有寫在 pyproject.toml 裡了，就直接 install
poetry install

# 1. 進入 monotonic_align 資料夾
cd ./python_backend/clean_vits/monotonic_align

# 2. 清除舊的 build 資料夾 (選用，但在跨平台轉移時強烈建議)
rm -rf build

# 3. 使用 Poetry 的環境來執行編譯指令
poetry run python setup.py build_ext --inplace

```


### T2M-GPT Models Not Found

```bash
# Verify model paths in config.yaml
cat config.yaml | grep -A 3 "t2m:"

# Check if files exist
ls -la T2M-GPT-main/pretrained/VQVAE/net_last.pth
ls -la T2M-GPT-main/pretrained/VQTransformer_corruption05/net_best_fid.pth

# Download models from T2M-GPT repository
# See: https://github.com/EricGuo5513/T2M-GPT
```

### Systemd Service Issues

```bash
# Check service status
sudo systemctl status ai-avatar

# View detailed logs
sudo journalctl -u ai-avatar -n 50

# If service fails to start, check:
# 1. User/group permissions
# 2. Working directory path
# 3. ExecStart path
# 4. Log file permissions

# Reset failed state
sudo systemctl reset-failed ai-avatar
sudo systemctl daemon-reload
sudo systemctl start ai-avatar
```

### NumPy Compatibility Issues

If you encounter `RuntimeError: cannot load _umath_tests module`, ensure you're using:
- Python 3.10 or 3.11
- NumPy >= 1.25, < 2.0

The codebase has been updated to remove all dependencies on deprecated `numpy.core.umath_tests`.

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
           ├─► VITS/gTTS (TTS)
           └─► T2M-GPT (Motion)
```

## 🌐 Integration with Unity

### Unity → Python Communication

The Unity frontend communicates with this backend via REST APIs:

1. **Chat**: User text → `/chat` → AI response
2. **Voice**: Audio recording → `/stt` → Transcribed text
3. **Motion**: Text description → `/t2m` or `/chat_t2m` → BVH/FBX animation
4. **Speech**: Text → `/tts` → MP3 audio

### Example Unity Integration

```csharp
// Send chat-to-motion request
var payload = new ChatT2MRequest {
    payload = chatHistory,
    t2m_text = llmResponse,
    format = "fbx"
};
var json = JsonUtility.ToJson(payload);
var request = UnityWebRequest.Post("http://localhost:8000/chat_t2m", json);
request.SetRequestHeader("Content-Type", "application/json");
yield return request.SendWebRequest();

// Handle response
var response = JsonUtility.FromJson<ChatT2MResponse>(request.downloadHandler.text);
byte[] motionData = Convert.FromBase64String(response.file_base64);
File.WriteAllBytes("motion.fbx", motionData);
```

## 📝 License

This project is part of the AI Desk Avatar system. See main repository for license information.

## 🤝 Contributing

Contributions are welcome! Please ensure:
- Add tests for new features
- Update documentation as needed
- Follow existing code style

## 🔗 Related Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Ollama Documentation](https://ollama.ai/docs)
- [T2M-GPT Repository](https://github.com/EricGuo5513/T2M-GPT)
- [UniVRM Unity Package](https://github.com/vrm-c/UniVRM)
- [VITS Repository](https://github.com/jaywalnut310/vits)

---

**Happy coding! 🎉**
