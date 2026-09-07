#!/bin/bash
# ============================================================
# 25 · 应用 KPM 并修补内核（仅 kpm_enable=true 时调用）
# ============================================================
source "$(dirname "$0")/../lib.sh"

echo "正在应用KP-N并修补内核..."
cd "$COMMON/out/arch/arm64/boot"
wget https://github.com/KernelSU-Next/KPatch-Next/releases/latest/download/kptools-linux
wget https://github.com/KernelSU-Next/KPatch-Next/releases/latest/download/kpimg-linux
chmod +x ./kptools-linux
./kptools-linux -p -i ./Image -k ./kpimg-linux -o ./oImage
rm -f Image
mv oImage Image
