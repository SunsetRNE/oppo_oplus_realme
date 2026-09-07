#!/bin/bash
# ============================================================
# 03 · 清除旧 ccache 缓存（仅 ccache_update=true 时由 workflow 调用）
# ============================================================
source "$(dirname "$0")/../lib.sh"

echo "正在清除仓库中的旧 ccache 缓存..."
if gh cache delete "$CCACHE_REAL_KEY-$RUNNER_OS-$GITHUB_REF_NAME" -R "$GITHUB_REPOSITORY"; then
  echo "成功删除旧的 ccache 缓存！"
else
  echo "旧缓存不存在或已被清理！"
fi
