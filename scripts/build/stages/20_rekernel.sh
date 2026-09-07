#!/bin/bash
# ============================================================
# 20 · 启用 Re-Kernel 支持（仅 rekernel_enable=true 时调用）
# ============================================================
source "$(dirname "$0")/../lib.sh"

echo "正在启用Re-Kernel支持(用于与Freezer,NoActive等软件配合使用,提升冻结后台能力)…"
cd "$KS"
cfg "CONFIG_REKERNEL=y"
cfg "CONFIG_REKERNEL_NETWORK=y"
