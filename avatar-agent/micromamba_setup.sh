#!/bin/bash
# install_env.sh - 自動化環境部署

ENV_NAME="mlagents"
PYTHON_VERSION="3.10"

echo "--- 正在初始化 Micromamba 環境: $ENV_NAME ---"

# 1. 建立環境 (若已存在則跳過)
if micromamba env list | grep -q "$ENV_NAME"; then
    echo "警告: 環境 '$ENV_NAME' 已存在。正在嘗試更新套件..."
else
    micromamba create -n $ENV_NAME python=$PYTHON_VERSION -c conda-forge -y
fi

# 2. 安裝核心套件
# 注意：Unity ML-Agents 4.0 依賴 PyTorch，建議安裝相容版本
micromamba run -n $ENV_NAME pip install \
    torch \
    onnx \
    mlagents==1.1.0 \
    gymnasium

echo "--- 安裝完成！使用 './run_train.sh' 開始訓練 ---"

# micromamba activate mlagents
