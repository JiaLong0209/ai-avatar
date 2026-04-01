# 🤖 AI-Avatar: Real-time Multimodal Interaction System for AI NPCs

[中文版本](./README.md)

![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?style=for-the-badge&logo=fastapi)
![Unity](https://img.shields.io/badge/Unity-2022.3+-black?style=for-the-badge&logo=unity)
![Gemini](https://img.shields.io/badge/LLM-Gemini_/_Gemma-orange?style=for-the-badge)
![T2M](https://img.shields.io/badge/Motion-T2M--GPT_/_MoMask-purple?style=for-the-badge)
![VITS](https://img.shields.io/badge/TTS-VITS_/_gTTS-red?style=for-the-badge)
![Whisper](https://img.shields.io/badge/STT-OpenAI_Whisper-brightgreen?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

---

This project is a high-interactivity system integrating **LLM**, **TTS**, **STT**, and **T2M (Text-to-Motion)**. Designed to bring a "soul" to **AI NPCs** in 3D games, enabling virtual characters with auditory perception, linguistic logic, vocal feedback, and real-time physical motion responses.

### 📺 Demo Video
[![AI Avatar Demo](https://img.youtube.com/vi/FzcBZnh0IIE/0.jpg)](https://www.youtube.com/watch?v=FzcBZnh0IIE)  
  

*Click the image above to view the YouTube version: [AI-Avatar Interaction Showcase](https://www.youtube.com/watch?v=FzcBZnh0IIE)*

### 👗 VRM Model Credits
The free VRM model used in this demo is provided by: [VRoid Hub - Characters 420420408072029080](https://hub.vroid.com/characters/420420408072029080/models/3513321044523426488)

---

## 🏃 Motion Generation Showcase (Example: Gymnastics & Dance)
To demonstrate the system's high-performance motion synthesis, we used "Gymnastics and Dance" as benchmarks to show how the system precisely drives complex VRM poses:

| Forward Roll | Handstand |
| :---: | :---: |
| ![Forward Roll](docs/forward-roll.png) | ![Handstand](docs/handstand.png) |

---

## 1. Key Technical Highlights

### 🤖 Embodied AI Persistence
NPCs are no longer limited to text boxes. They react with semantically-aligned 3D skeletal animations based on the conversation context (emotions, topics, or specific action requests) generated through T2M.

### 🏃 Performance BVH Runtime Player
- **Dynamic Parsing**: Automatically reads BVH `CHANNELS` definitions and handles dynamic rotation orders (XYZ/ZXY/etc.), completely eliminating skeleton flipping and gimbal lock.
- **Frame Interpolation**: Ensures stable, silky-smooth animation playback even at high display refresh rates through frame-level smoothing.
- **Physics Harmony**: Automatically manages the `isKinematic` state of the target character's Rigidbody to prevent conflicts between physical collisions and animation drivers.

### ⚡ Unified Synchronization Flow (Combined)
- Featuring a unique `/chat_and_motion` endpoint that accomplishes LLM text generation, response translation, and T2M motion synthesis in a single API call, reducing end-to-end latency.

---

## 2. Technical Architecture

The system uses a decoupled frontend/backend microservice architecture:
- **Unity Frontend (The View)**:
  - `ChatUIManager` handles user voice and text input.
  - `MotionManager` and `BvhRuntimePlayer` play back the 3D motion formats streamed from the server.
  - Communicates with the Python backend via HTTP requests.
- **FastAPI Backend (The Brain)**:
  - **LLM Core**: Calls Ollama or Google Gemini to generate dialogue and english motion descriptions.
  - **Audio Engine**: Uses Whisper for STT and VITS/gTTS for high-quality TTS.
  - **Motion Engine**: Uses T2M-GPT or MoMask models to perform real-time text-to-motion inference, exporting to BVH/FBX parameters.

---

## 3. Backend In-Depth (Python)

The backend is the "brain" of the system, powered by **FastAPI** with dependency management via **Poetry**.

### 📦 Installation Prep
1. **System Dependencies**: `ffmpeg` (audio), `blender` (motion format converter), and `poetry`.
   ```bash
   # Ubuntu/Debian
   sudo apt-get install -y ffmpeg blender poetry
   ```
2. **Installation**:
   ```bash
   cd python_backend
   poetry install
   poetry shell
   ```

### 🧠 Required Models & Preparation

This system relies on several pre-trained models. Please clone and download them into the exact folder structures below:

1. **T2M-GPT Motion Model**:
   - Clone the [T2M-GPT](https://github.com/Mael-zys/T2M-GPT) repository to `python_backend/t2m-models/T2M-GPT-main/`.
   - Download the pre-trained weights to their respective folders:
     - VQVAE: `t2m-models/T2M-GPT-main/pretrained/VQVAE/net_last.pth`
     - Transformer: `t2m-models/T2M-GPT-main/pretrained/VQTransformer_corruption05/net_best_fid.pth`
     - Metadata: `t2m-models/T2M-GPT-main/checkpoints/t2m/VQVAEV3_CB1024_CMT_H1024_NRES3/meta/`

2. **MoMask Motion Model (Optional)**:
   - If using MoMask, clone [momask-codes](https://github.com/EricGuo5513/momask-codes) to `python_backend/t2m-models/momask/`.
   - Place weights inside `python_backend/t2m-models/momask/checkpoints/t2m/` (e.g. `t2m_nlayer8...`, `VQ_NAME`).

3. **VITS High-Fidelity TTS Model**:
   - Place your custom or pre-trained VITS model files in `python_backend/vits/`:
     - `G_latest.pth` (generator)
     - `config.json` (model config)
   - *Note: If files are missing, the system acts smartly and falls back to Google TTS (`gTTS`).*

4. **Ollama LLM Foundation**:
   - Install Ollama locally and pull your preferred model: `ollama pull gemma3:4b`.
   - If you are relying purely on Google Gemini, skip Ollama and populate `GEMINI_API_KEY` in `.env`.

### 🛠️ Advanced: VITS Rebuild
For cross-platform deployment, rebuild the `monotonic_align` extension:
```bash
cd python_backend/clean_vits/monotonic_align
rm -rf build && poetry run python setup.py build_ext --inplace
```

### ⚙️ Configuration
All NPC personas and paths are managed through `config.yaml`:
- **`llm`**: Defines `provider` (`gemini`/`ollama`) and `model_name`.
- **`chat.system_prompt`**: Define the NPC's language style, persona, and rules.
- **Startup**: Run `./run.sh` (Includes automatic log rotation).

---

## 4. API Specification

Default URL: `http://localhost:8000`

### 🔄 Core Combined Interface ([POST] `/chat_and_motion`)
**The primary entry point for Unity integration, synchronizing voice, text, and motion.**
- **Request Format:**
  ```json
  {
    "message": "Do a celebration!",
    "messages": [
      {"role": "user", "content": "Hello"},
      {"role": "assistant", "content": "Hey there!"}
    ],
    "format": "bvh"
  }
  ```
- **Response:** Bundled JSON containing `reply` (text), `motion_text` (English generation), `motion_url` (motion path), and `audio_url` (audio path).

### 💬 Pure Chat Interface ([POST] `/chat`)
- **Use Case:** Standard LLM conversation.
- **Response:** `{"response": "..."}`.

### 🗣️ Text-To-Speech ([POST/GET] `/tts`)
- **Parameters:** `text` (required), `lang` (optional), `provider` (`vits` / `gtts`).
- **Output:** Binary audio stream (MP3/WAV).

### 🎙️ Speech-To-Text ([POST] `/stt`)
- **Input:** Multipart form-data with the audio file.
- **Output:** `{"text": "Transcription result"}`.

### 🏃 Independent Motion ([POST] `/t2m`)
- **Use Case:** Generate animation from pure English descriptions.
- **Output:** Binary file (`.bvh` / `.fbx`).

---

## 5. Unity Control Guide

| Key | Action |
| :--- | :--- |
| `/` | Toggle/Focus chat input. |
| `Enter` | Send message to AI and trigger motion. |
| `Shift + Backspace` | **Grand Reset**. Clears UI history and purges LLM short-term memory. |
| `Esc` | Exit input focus. |
| **Hips Tracking** | Camera targets the bone tagged `Player` or the `Hips` bone automatically. |

---

## ⚙️ Service Deployment (Systemd)
The backend includes a `ai-avatar.service` template:
1. Edit `User` and `WorkingDirectory` paths.
2. Run:
   ```bash
   cd python_backend
   sudo cp ai-avatar.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now ai-avatar
   ```
3. Monitor logs: `tail -f server.log`.
