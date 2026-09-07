#!/bin/bash
# ============================================================
# 11 · 应用 KernelSU & SUSFS 补丁（仅 susfs_enable=true 时调用）
# ============================================================
source "$(dirname "$0")/../lib.sh"

cd "$KS"
if [[ "$KSUTYPE" != "none" ]]; then
  echo "正在添加susfs补丁..."
  git clone --depth=1 https://github.com/SunsetRNE/susfs4oki.git susfs4ksu -b "oki-$ANDROID_VERSION-$KERNEL_VERSION"
  cp "./susfs4ksu/kernel_patches/50_add_susfs_in_gki-$ANDROID_VERSION-$KERNEL_VERSION.patch" "$COMMON/"
  if [[ "$HIDE_STUFF" == "1" ]]; then
    cp "$GITHUB_WORKSPACE/$PLATFORM_DIR/other_patch/69_hide_stuff.patch" "$COMMON/"
  fi
  cp ./susfs4ksu/kernel_patches/fs/* "$COMMON/fs/"
  cp ./susfs4ksu/kernel_patches/include/linux/* "$COMMON/include/linux/"
  cd "$COMMON"
  patch -p1 < "50_add_susfs_in_gki-$ANDROID_VERSION-$KERNEL_VERSION.patch" || true
  if [[ "$HIDE_STUFF" == "1" ]]; then
    patch -p1 -N -F 3 < 69_hide_stuff.patch || true
  fi
  cd "$KS"
else
  echo "已选择无内置KernelSU模式，跳过susfs配置..."
fi
if [[ "$KSUTYPE" == "ksu" ]]; then
  echo "正在为原版 KernelSU (tiann/KernelSU)添加补丁..."
  cp ./susfs4ksu/kernel_patches/KernelSU/10_enable_susfs_for_ksu.patch ./KernelSU/
  cd ./KernelSU
  patch -p1 < 10_enable_susfs_for_ksu.patch || true
fi
