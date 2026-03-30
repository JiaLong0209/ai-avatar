#!/bin/bash
# run_train.sh - 靈活的 ML-Agents 訓練啟動器

# --- 預設值 (Default Values) ---
ENV_NAME="mlagents"
CONFIG_PATH="./config/vrm_config.yaml"
RUN_ID="VRM_Experiment_$(date +%Y%m%d_%H%M)"
RESUME_FLAG="--resume"

# --- 參數說明 ---
usage() {
    echo "使用方法: $0 [-e env_name] [-c config_path] [-i run_id] [-f (force/new run)]"
    echo "  -e : Micromamba 環境名稱 (預設: $ENV_NAME)"
    echo "  -c : YAML 設定檔路徑 (預設: $CONFIG_PATH)"
    echo "  -i : 訓練執行 ID (預設: 時間戳記)"
    echo "  -f : 強制重新開始 (預設為 Resume 模式，加入此參數則從頭訓練)"
    exit 1
}

# --- 解析命令列參數 ---
while getopts "e:c:i:f" opt; do
    case "$opt" in
        e) ENV_NAME=$OPTARG ;;
        c) CONFIG_PATH=$OPTARG ;;
        i) RUN_ID=$OPTARG ;;
        f) RESUME_FLAG="--force" ;; # 如果輸入 -f，則清空 --resume 標籤
        *) usage ;;
    esac
done

# --- 環境檢查 ---
if [ ! -f "$CONFIG_PATH" ]; then
    echo "❌ 錯誤: 找不到設定檔 $CONFIG_PATH"
    exit 1
fi

echo "=========================================="
echo "🤖 ML-Agents 訓練啟動中..."
echo "📍 環境: $ENV_NAME"
echo "📄 配置: $CONFIG_PATH"
echo "🆔 運行 ID: $RUN_ID"
if [ -z "$RESUME_FLAG" ]; then
    echo "🔥 模式: 強制重新開始 (Force New Run)"
else
    echo "⏳ 模式: 續接訓練 (Resume)"
fi
echo "=========================================="

# --- 執行訓練 ---
# 使用 micromamba run 確保在正確的環境中調用 mlagents-learn
micromamba run -n "$ENV_NAME" mlagents-learn "$CONFIG_PATH" \
    --run-id="$RUN_ID" \
    $RESUME_FLAG \
    --num-envs=1 \
    --no-graphics
