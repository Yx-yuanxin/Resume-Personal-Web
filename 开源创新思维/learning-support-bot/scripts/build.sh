#!/usr/bin/env bash
# 构建脚本 - 打包当前项目
set -e
echo "Building learning-support-bot..."
python -m pip install --upgrade build
python -m build
echo "Done. Check dist/ directory."
