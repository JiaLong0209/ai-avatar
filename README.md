# AI-Avatar: Multimodal Real-time Interaction System

本專案是一個整合 **LLM (大語言模型)**、**TTS (語音合成)**、**STT (語音轉文字)** 與 **T2M (文字轉動作)** 的即時 VRM 角色聊天互動系統。透過 Python 後端進行推理，並於 Unity 端實現 VRM 模型的互動。

---

## 1. 系統架構 (System Architecture)

系統採用前後端分離架構，確保推理延遲不影響前端渲染：

### Unity Frontend (Unity 2022.3+)
- **Chat UI / Voice Input**: 負責使用者輸入（文字或語音）。
- **MotionManager & VRM Agent**: 管理 VRM 模型的動作流水線與骨骼驅動。
- **Networking Module**: 使用 `UnityWebRequest` 與後端伺服器通訊。
<!-- - **Audio Player & uLipSync**: 處理語音播放與即時口型同步。 -->

### FastAPI Backend (Python 3.11.9)
- **LLM Service**: 集成 Ollama (Gemma 3) 或 Google Gemini，負責對話邏輯。
- **TTS Service**: 基於 VITS 或 gTTS，將文字轉換為高質量的語音。
- **T2M Service**: 使用 MoMask 或 T2M-GPT 模型，根據描述生成 3D 動作。
- **STT Service**: 透過 OpenAI Whisper 進行精準的語音識別。

### 資料流 (Data Flow)
1. **輸入**: 使用者透過 Unity 發送文字或語音請求。
2. **處理**: 後端 API 接收並調度 LLM 進行思考。
3. **並行生成**: 合成回覆文字對應的語音 (TTS) 與動作 (T2M)。
4. **輸出**: Unity 接收資料包，執行口型對齊與動畫播放。

---

## 2. 模型準備 (Model Preparation)

本專案依賴多個預訓練模型，請依序下載並放置於 `python_backend/` 對應目錄。

### 🏃 Text-To-Motion 模型
請將模型統一放置於 `python_backend/t2m-models/`：

1. **T2M-GPT**:
   - 原始專案: [Mael-zys/T2M-GPT](https://github.com/Mael-zys/T2M-GPT)
   - 下載預訓練權重並放置於 `t2m-models/T2M-GPT-main/` 目錄下：
     - **VQVAE**: `pretrained/VQVAE/net_last.pth`
     - **Transformer**: `pretrained/VQTransformer_corruption05/net_best_fid.pth`
     - **Metadata**: `checkpoints/t2m/VQVAEV3_CB1024_CMT_H1024_NRES3/meta/`

2. **MoMask**:
   - 原始專案: [EricGuo5513/momask-codes](https://github.com/EricGuo5513/momask-codes)
   - 下載預訓練權重並依據 [MoMask README](https://github.com/EricGuo5513/momask-codes) 結構放置於 `t2m-models/momask/`：
     - 需包含 `checkpoints/t2m/` 下的各個模型目錄（如 `t2m_nlayer8...`, `VQ_NAME`, `tres_...`, `length_estimator`）。

### 🗣️ TTS (VITS) 模型
- 放置於 `python_backend/vits/`：
  - `G_latest.pth`: 生成器模型權重。
  - `config.json`: 模型配置文件。

---

## 3. API 使用說明 (API Usage)

後端服務預設運行於 `http://localhost:8000`。

### 💬 聊天對話 (Chat)
**Endpoint:** `POST /chat`

用於獲取 LLM 的文字回覆，支持上下文對話。

**Request Body:**
```json
{
  "message": "你好",
  "messages": [
    {"role": "user", "content": "你好"},
    {"role": "assistant", "content": "你好！有什麼我可以幫你的嗎？"}
  ]
}
```

**Response:**
```json
{
  "response": "你好呀！今天想聊些什麼呢？"
}
```

### 🗣️ 語音合成 (TTS)
**Endpoint:** `GET/POST /tts`

將文字轉換為語音音訊流。

**Parameters:**
- `text` (Required): 要合成的文字。
- `lang` (Optional): 語言代碼 (如 `zh`, `ja`, `en`)。
- `provider` (Optional): `vits` 或 `gtts`。

**Response:** Audio stream (Media Type: `audio/mpeg` or `audio/wav`).

### 🏃 動作生成 (T2M)
**Endpoint:** `POST /t2m`

根據文字描述生成 3D 動作文件。

**Request (Form Data):**
- `text`: 動作描述 (例如 "a person waves their hand")。
- `format`: `fbx` (預設) 或 `bvh`。
- `save_temp_files`: `true` (預設) 或 `false`。

**Response:** 二進位動作文件流 (`.fbx` 或 `.bvh`)。

### 🔄 聊天結合動作 (Chat T2M)
**Endpoint:** `POST /chat_t2m`

這是 Unity 前端最常用的介面，它會根據聊天上下文自動生成對應的動作。

**Request Body:**
```json
{
  "payload": { "messages": [...] },
  "t2m_text": "LLM 回覆的文本",
  "format": "fbx",
  "save_temp_files": true,
  "motion_dir": "path/to/save"
}
```

**Response:**
```json
{
  "motion_text": "English motion description used for generation",
  "format": "fbx",
  "file_name": "motion_123.fbx",
  "file_base64": "..." 
}
```

### 🎙️ 語音轉文字 (STT)
**Endpoint:** `POST /stt`

**Request:** `multipart/form-data` 包含 `file` (音訊文件)。
**Response:** `{"text": "辨識出的文字"}`。

---

## 3. 環境配置 (Configuration)

### Python 後端配置
主要配置文件為 `python_backend/config.yaml`，亦可透過 `.env` 環境變數覆蓋。

| 環境變數 | 說明 | 預設值 |
| :--- | :--- | :--- |
| `LLM_PROVIDER` | `ollama` 或 `gemini` | `ollama` |
| `LLM_MODEL_NAME` | Ollama 模型名稱 | `gemma3:4b` |
| `GEMINI_API_KEY` | Google Gemini API Key | - |
| `DEFAULT_TTS_PROVIDER` | `vits` 或 `gtts` | `vits` |
| `ACTIVE_T2M_MODEL` | `momask`, `t2m-gpt`, `mdm` | `momask` |

### Unity 前端配置
- **ChatUIManager**: 設定 `Chat Url` 與 `Chat T2m Url`。
- **TtsHttpProvider**: 設定 `Tts Url` 與 `Provider` (`vits`/`gtts`)。
- **MotionManager**: 管理 FBX 動作的載入與播放邏輯。

---

- 📂 `python_backend/`: FastAPI 服務核心。
- 📂 `AI-Desk-Avatar/`: Unity 專案資產與場景模型。
    - `Assets/Scripts/Core/`: 核心通訊與管理邏輯。
    - `Assets/Scripts/Agent/`: ML-Agents 控制器邏輯。
- 📂 `avatar-agent/`: ML-Agents 強化學習訓練配置。

---

## 5. 快速啟動

### 啟動後端
```bash
cd python_backend
poetry install --no-root
poetry shell
./run.sh
```

### 啟動 Unity
1. 開啟 `AI-Desk-Avatar` 專案。
2. 進入互動場景，點擊 **Play**。
3. 按下 `/` 鍵即可開始打字互動。
