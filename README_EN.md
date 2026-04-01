# 🤖 AI-Avatar: Real-time Multimodal Interaction System for AI NPCs

[中文版本](./README.md)

---

This project is a real-time 3D character interaction system integrating **LLM**, **TTS**, **STT**, and **T2M (Text-to-Motion)**. It is designed to explore deep interactivity and emergent behaviors for **AI NPCs** in 3D games, providing them with ears, voices, and expressive bodies.

### 📺 Demo Video
[![AI Avatar Demo](https://img.youtube.com/vi/FzcBZnh0IIE/0.jpg)](https://www.youtube.com/watch?v=FzcBZnh0IIE)
*Click the image above to view the YouTube version: [AI-Avatar Interaction Showcase](https://www.youtube.com/watch?v=FzcBZnh0IIE)*

### 👗 VRM Model Credits
The free VRM model used in this demo provided by: [VRoid Hub - Characters 420420408072029080](https://hub.vroid.com/characters/420420408072029080/models/3513321044523426488)

---

## 🏃 Motion Generation Showcase (Example: Gymnastics & Dance)
To demonstrate the system's high-performance motion generation, we use "Gymnastics and Dance" as technical benchmarks to show how the system drives complex VRM poses:

| Forward Roll | Handstand |
| :---: | :---: |
| ![Forward Roll](docs/forward-roll.png) | ![Handstand](docs/handstand.png) |

---

## 1. Core Technical Highlights

- **🤖 Embodied AI NPC**: Merges LLM reasoning with T2M technology. NPCs no longer just provide text response; they react with semantically-aligned 3D animations in real-time.
- **🏃 Custom BVH Runtime Player**:
    - **Dynamic Parsing**: Supports arbitrary `CHANNELS` definitions in BVH files to prevent Euler rotation flipping and gimbal lock.
    - **Smooth Interpolation**: Ensures stable motion playback even at high display refresh rates through frame-level smoothing.
    - **Physics Integration**: Automatically switches Rigidbodies to Kinematic during playback to ensure animation fidelity over physics interference.
- **⚡ Unified API Pipeline (Combined Flow)**: 
    - The `/chat_and_motion` endpoint allows for a single API call to retrieve reply text, voice (TTS), and motion data, significantly reducing interaction latency.
- **📸 Smart Hips Tracking**: The `CameraController` features auto-target detection for the character's `Hips` bone, keeping the view centered even during flips or high-speed root motion.

---

## 2. Backend API Specification

Default Base URL: `http://localhost:8000`

### 💬 Unified Chat & Motion
**Endpoint:** `POST /chat_and_motion`  
**Description:** The primary interface for the Unity frontend. Returns text, audio (TTS), and motion data.

**Request Body:**
```json
{
  "message": "Can you perform a flip?",
  "messages": [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi there! OuO"}
  ],
  "format": "bvh"
}
```

**Response (JSON):**
```json
{
  "reply": "Sure! Watch this (｀・ω・´)",
  "motion_text": "A person performs a quick forward roll.",
  "audio_url": "/temp/audio_123.wav",
  "motion_url": "/temp/motion_123.bvh"
}
```

### 🗣️ Text-To-Speech (TTS)
**Endpoint:** `GET /tts`  
**Parameters:**
- `text`: Text to synthesize.
- `provider`: `vits` (High-quality local inference) or `gtts` (Google Cloud).

### 🎙️ Speech-To-Text (STT)
**Endpoint:** `POST /stt`  
**Description:** Upload a `.wav/.mp3` file to receive transcribed text (based on OpenAI Whisper).

---

## 3. Unity Control Guide

| Key | Action |
| :--- | :--- |
| `/` | Quickly focus on the chat input box. |
| `Enter` | Send message (automatically clears the input field). |
| `Shift + Backspace` | **One-click Clear** UI history and reset LLM context memory. |
| `Esc` | Exit input focus. |

---

## 4. Setup & Deployment

### Python Backend
1. Install Python 3.11 and Poetry.
2. In `python_backend`, run `poetry install`.
3. Configure `config.yaml` (Set Gemini API Key or local model paths).
4. Run `./run.sh` to start the server.

### Unity Frontend
1. Open with Unity 2022.3.16f1 or newer.
2. Ensure **UniVRM 1.0** is imported.
3. Verify the API URLs in the `ChatUIManager` component match your backend server.
