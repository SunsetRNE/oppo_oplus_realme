#!/bin/bash
# ============================================================
# 01 · 配置 ccache 目录（写入 GITHUB_ENV 供后续 step 使用）
# ============================================================
source "$(dirname "$0")/../lib.sh"

echo "CCACHE_DIR=$HOME/.ccache_$KERNEL_VERSION.$SUB_VERSION" >> "$GITHUB_ENV"
echo "CCACHE_MAXSIZE=3G" >> "$GITHUB_ENV"
echo "当前磁盘空间："
df -h
echo "当前构建内核版本：$KERNEL_VERSION.$SUB_VERSION"
if [[ "$DROIDSPACES_ENABLE" != "false" ]]; then
  CCACHE_REAL_KEY="$CCACHE_KEY-Droidspaces"
else
  CCACHE_REAL_KEY="$CCACHE_KEY-none"
fi
echo "CCACHE_REAL_KEY=$CCACHE_REAL_KEY" >> "$GITHUB_ENV"
