#!/bin/bash
# ============================================================
# 13 · 应用 lz4kd 补丁（仅 lz4kd_enable=true 时调用）
# ============================================================
source "$(dirname "$0")/../lib.sh"

echo "正在添加lz4kd补丁…"
cd "$COMMON"
apply_self_patch "$PLATFORM_DIR/other_patch/lz4kd.patch" "-p1" "-F 3" || true
