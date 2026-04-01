# 🤖 AI-Avatar: AI NPC 即時多模態互動系統

[English Version](./README_EN.md)

![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?style=for-the-badge&logo=fastapi)
![Unity](https://img.shields.io/badge/Unity-2022.3+-black?style=for-the-badge&logo=unity)
![Gemini](https://img.shields.io/badge/LLM-Gemini_/_Gemma-orange?style=for-the-badge)
![T2M](https://img.shields.io/badge/Motion-T2M--GPT_/_MoMask-purple?style=for-the-badge)
![VITS](https://img.shields.io/badge/TTS-VITS_/_gTTS-red?style=for-the-badge)
![Whisper](https://img.shields.io/badge/STT-OpenAI_Whisper-brightgreen?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

---

本專案是一個整合 **LLM (大語言模型)**、**TTS (語音合成)**、**STT (語音解析)** 與 **T2M (Text-to-Motion)** 的全方位 3D 角色互動系統。我們致力於為 3D 遊戲中的 **AI NPC** 提供深度的互動靈魂，讓虛擬角色具備聽覺認知、語言邏輯、語音回饋以及即時的身體動作反應。

### 📺 專案演示 (Demo Video)
[![AI Avatar Demo](https://img.youtube.com/vi/FzcBZnh0IIE/0.jpg)](https://www.youtube.com/watch?v=FzcBZnh0IIE)   
   
*點擊上方圖片查看 YouTube 演示版本：[AI-Avatar Interaction Showcase](https://www.youtube.com/watch?v=FzcBZnh0IIE)*

### 👗 使用的 VRM 模型
本專案演示使用的免費 VRM 模型來源：[VRoid Hub - Characters 420420408072029080](https://hub.vroid.com/characters/420420408072029080/models/3513321044523426488)

---

## 🏃 動作生成展示 (範例：體操與舞蹈)
為了展示系統的高性能運動生成能力，我們以「體操與舞蹈」作為範例，演示系統如何精準驅動 VRM 模型執行高度複雜的動作：

| 前滾翻 (Forward Roll) | 倒立 (Handstand) |
| :---: | :---: |
| ![Forward Roll](docs/forward-roll.png) | ![Handstand](docs/handstand.png) |

---

## 1. 核心技術亮點 (Key Features)

### 🤖 具身智慧 NPC (Embodied AI)
整合 LLM 推理與 T2M 技術，NPC 不再只是文字輸出，而是會根據對話語境（情緒、主題、動作要求）同步產生對應的 3D 骨骼動畫。

### 🏃 自研 BVH Runtime Player
- **動態解析**: 支持各類 BVH 檔案的 `CHANNELS` 定義解析，動態處理旋轉順序（XYZ/ZXY 等），徹底解決骨骼翻轉與萬向鎖問題。
- **流暢插值**: 影格間平滑處理，確保在 60+ FPS 下動畫依然絲滑穩定。
- **物理相容**: 播放時自動管理目標角色的 `isKinematic` 狀態，防止實體物理與動畫驅動發生衝突。

### ⚡ 聯合同步流 (Combined Flow)
- 透過獨有的 `/chat_and_motion` 介面，單次請求即可完成 LLM 生成、回覆翻譯、動作數據合成，極大降低端到端延遲。

---

## 2. 系統架構 (Technical Architecture)

系統採用前後端分離的微服務架構：
- **Unity Frontend (前台)**:
  - 透過 `ChatUIManager` 負責擷取玩家語音與文字輸入。
  - 透過 `MotionManager` 與 `BvhRuntimePlayer` 即時播放來自後端的 3D 動作。
  - 透過 HTTP 請求與 Python 後端通訊。
- **FastAPI Backend (後台大腦)**:
  - **LLM 核心**: 呼叫 Ollama 或 Gemini 生成人物對話與動作描述。
  - **語音模組**: 使用 Whisper 進行 STT（語音辨識），使用 VITS 或 gTTS 進行 TTS（語音合成）。
  - **運動大腦**: 使用 T2M-GPT 或 MoMask 模型，基於英文動作描述即時推理出 3D 骨骼運動軌跡 (FBX / BVH)。

---

## 3. Python 後端詳解 (Backend In-Depth)

後端是系統的「大腦」，基於 **FastAPI** 構建，透過 **Poetry** 進行依賴管理。

### 📦 環境準備與安裝
1. **系統套件**: 需安裝 `ffmpeg` (音訊處理)、`blender` (動作格式轉換) 與 `poetry`。
   ```bash
   # Ubuntu/Debian
   sudo apt-get install -y ffmpeg blender poetry
   ```
2. **安裝 Python 環境**:
   ```bash
   cd python_backend
   poetry install
   poetry shell
   ```

### 🧠必備模型下載與放置 (Required Models)

本系統依賴多組預訓練模型來完成工作，請依照以下路徑配置你的模型庫：

1. **T2M-GPT 動作模型**:
   - 將 [T2M-GPT](https://github.com/Mael-zys/T2M-GPT) Repo clone 下來並命名為 `python_backend/t2m-models/T2M-GPT-main/`。
   - 下載預訓練權重，並放置於對應結構：
     - VQVAE: `t2m-models/T2M-GPT-main/pretrained/VQVAE/net_last.pth`
     - Transformer: `t2m-models/T2M-GPT-main/pretrained/VQTransformer_corruption05/net_best_fid.pth`
     - Metadata: `t2m-models/T2M-GPT-main/checkpoints/t2m/VQVAEV3_CB1024_CMT_H1024_NRES3/meta/`

2. **MoMask 動作模型 (可選)**:
   - 若想使用 MoMask，需將 [momask-codes](https://github.com/EricGuo5513/momask-codes) clone 並放置於 `python_backend/t2m-models/momask/`。
   - 將預訓練權重放在 `python_backend/t2m-models/momask/checkpoints/t2m/` 內（如 `t2m_nlayer8...`, `VQ_NAME` 等）。

3. **VITS 高音質語音合成模型**:
   - 將 VITS 的模型檔案放在 `python_backend/vits/`：
     - `G_latest.pth` (生成器權重)
     - `config.json` (VITS 模型配置)
   - 若未放置，系統會自動降級使用 Google 的 `gTTS`。

4. **Ollama 大模型基座**:
   - 本地端需安裝 Ollama 並拉取模型：`ollama pull gemma3:4b`。
   - 若使用 Google Gemini API 則可跳過此步驟，請直接在 `.env` 或 `config.yaml` 填入 `GEMINI_API_KEY`。

### 🛠️ VITS 跨平台編譯 (Advanced Rebuild)
如果你更換了作業系統或從 Windows 轉移到 Linux，需手動重新編譯 `monotonic_align` 擴充套件：
```bash
cd python_backend/clean_vits/monotonic_align
rm -rf build && poetry run python setup.py build_ext --inplace
```

### ⚙️ 服務配置與啟動 (Configuration & Startup)
- 大部分參數都可以透過 `config.yaml` 調整，包含 `llm.provider`、`chat.system_prompt` (改寫角色性格)、預設模型路徑等。
- **啟動服務**: 
  ```bash
  cd python_backend
  ./run.sh
  ```

---

## 4. API 介面全規格 (Full API Docs)

預設 URL: `http://localhost:8000`

### 🔄 核心聯合介面 ([POST] `/chat_and_motion`)
**Unity 前端最核心的對話入口，實現語音與動作同步返還。**
- **請求格式**:
  ```json
  {
    "message": "做一個慶祝動作！",
    "messages": [
      {"role": "user", "content": "你好"},
      {"role": "assistant", "content": "嘿嘿！"}
    ],
    "format": "bvh"
  }
  ```
- **回傳內容**: 包含 `reply` (回覆文字)、`motion_text` (生成的英文動作描述)、`motion_url` (動作檔路徑)、`audio_url` (音訊檔路徑)。

### 💬 純對話介面 ([POST] `/chat`)
- **用途**: 單純與 LLM 聊天。
- **回傳**: `{"response": "..."}`。

### 🗣️ 語音合成 ([POST/GET] `/tts`)
- **參數**: `text` (必填), `lang` (可選), `provider` (`vits` / `gtts`)。
- **回傳**: 音訊二進位流 (MP3/WAV)。

### 🎙️ 語音轉文字 ([POST] `/stt`)
- **參數**: Multipart 上傳音訊檔案。
- **回傳**: `{"text": "識別結果"}`。

### 🏃 獨立動作生成 ([POST] `/t2m`)
- **用途**: 根據純英文動作描述生成動畫。
- **參數**: `text` (英文描述), `format` (`bvh`/`fbx`)。

---

## 5. Unity 操作指南 (Unity Controls)

| 按鍵 (Key) | 功能 (Action) |
| :--- | :--- |
| `/` | 開啟/聚焦聊天框。 |
| `Enter` | 送出訊息給 AI 並觸發動作。 |
| `Shift + Backspace` | **全域重置 (Grand Reset)**。清除 UI 歷史及 LLM 記憶，重新啟動一段對話。 |
| `Esc` | 退出輸入模式。 |

---

## ⚙️ 服務部署 (Systemd Service)
後端包含一個 `ai-avatar.service` 模版，方便將其作為系統背景服務執行：
1. 將 `ai-avatar.service` 裡的 `User` 與 `WorkingDirectory` 改為你的實際路徑。
2. 執行指令：
   ```bash
   cd python_backend
   sudo cp ai-avatar.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now ai-avatar
   ```
3. 查看日誌：`tail -f server.log`。
