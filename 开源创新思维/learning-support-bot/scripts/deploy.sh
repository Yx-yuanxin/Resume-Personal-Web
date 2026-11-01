#!/usr/bin/env bash
# 部署脚本 - 启动 Demo 服务
set -e
echo "Starting learning-support-bot demo..."
python -m src.learning_support_bot.main
