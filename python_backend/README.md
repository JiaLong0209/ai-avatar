# 🤖 AI-Avatar - Python Backend

A multimodal AI backend system providing **Chat (LLM)**, **STT**, **TTS**, and **T2M (Text-to-Motion)** capabilities for Unity-based VRM avatars.

![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?style=flat-square&logo=fastapi)
![Gemini](https://img.shields.io/badge/LLM-Gemini_/_Gemma-orange?style=flat-square)
![T2M](https://img.shields.io/badge/Motion-T2M--GPT_/_MoMask-purple?style=flat-square)

---

## 📋 Table of Contents
- [Overview](#overview)
- [✨ Core Features](#core-features)
- [📦 Installation](#installation)
- [⚙️ Configuration](#configuration)
- [📡 API Specifications](#api-endpoints)
- [🛠️ Advanced: VITS Rebuild](#vits-rebuild)
- [🚀 Service Deployment](#deployment)

---

## 🎯 Overview
This backend acts as the "brain" for the AI Avatar, handling:
- **LLM Reasoning**: Powered by Google Gemini (Flash/Pro) or local Ollama (Gemma 3).
- **Audio Processing**: Whisper for STT; VITS (Neural) & gTTS for vocal synthesis.
- **Motion Synthesis**: T2M-GPT & MoMask for generating realistic 3D skeletal animations.
- **Context Management**: Multi-turn conversation memory for consistent NPC behavior.

---

## ✨ Core Features
- 🛡️ **Embodied AI**: Generates semantically aligned body language for every chat response.
- 💃 **Gymnast/Dancer Persona**: Pre-configured athletic personality and motion suggestions.
- 🏎️ **Optimized Pipeline**: Combined endpoints (`/chat_and_motion`) reduces total latency by batching reasoning and motion generation.
- 🎞️ **Multi-Format Export**: Supports both **FBX** and **BVH** (with dynamic channel order support).

---

## 📦 Installation

### 1. System Requirements
- **OS**: Linux (Recommended), macOS, or Windows (WSL2).
- **Dependencies**: `ffmpeg`, `blender` (for FBX conversion), `poetry`.

```bash
# Ubuntu/Debian
sudo apt-get install -y ffmpeg blender poetry
```

### 2. Environment Setup
```bash
cd python_backend
poetry install
poetry shell
```

### 3. Model Downloads
- **T2M-GPT**: Clone to `t2m-models/T2M-GPT-main/`. Download checkpoints for VQVAE and Transformer.
- **VITS**: Place `G_latest.pth` and `config.json` in the `vits/` folder.
- **Ollama**: `ollama pull gemma3:27b` (Optional if using Gemini).

---

## ⚙️ Configuration
Managed via `config.yaml`. Supports environment variable overrides via `.env`.

- **`llm.provider`**: `gemini` or `ollama`.
- **`chat.system_prompt`**: Define your NPC persona here.
- **`t2m.models`**: Adjust default motion length and model selection.

---

## 📡 API Specifications

### [POST] `/chat_and_motion`
The primary interaction endpoint.
**Request:**
```json
{
  "message": "Can you do a handstand?",
  "messages": [], 
  "format": "bvh"
}
```
**Response:** Returns a bundle of `reply`, `motion_text`, `audio_url`, and `motion_url`.

### [POST] `/tts`
- `text`: Input text.
- `provider`: `vits` (High fidelity) or `gtts`.

---

## 🛠️ Advanced: VITS Rebuild (Cross-Platform)
If you are moving to a new OS, you must rebuild the `monotonic_align` extension:
```bash
cd clean_vits/monotonic_align
rm -rf build
poetry run python setup.py build_ext --inplace
```

---

## 🚀 Service Deployment (Systemd)
Use the provided `ai-avatar.service` template:
1. Edit `User` and `WorkingDirectory` in the `.service` file.
2. `sudo cp ai-avatar.service /etc/systemd/system/`
3. `sudo systemctl enable --now ai-avatar`
