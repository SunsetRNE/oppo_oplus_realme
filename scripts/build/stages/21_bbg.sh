#!/bin/bash
# ============================================================
# 21 · 启用内核级基带保护（仅 baseband_guard=true 时调用）
# ============================================================
source "$(dirname "$0")/../lib.sh"

echo "正在启用内核级基带保护支持…"
cd "$KS"
cfg "CONFIG_BBG=y"
cd "$COMMON"
curl -sSL https://github.com/SunsetRNE/Baseband-guard/raw/master/setup.sh | bash
sed -i '/^config LSM$/,/^help$/{ /^[[:space:]]*default/ { /baseband_guard/! s/selinux/selinux,baseband_guard/ } }' security/Kconfig
