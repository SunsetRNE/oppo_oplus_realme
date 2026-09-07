#!/bin/bash
# ============================================================
# 12 · 应用 lz4 1.10.0 & zstd 1.5.7 补丁（仅 lz4_enable=true 时调用）
# 平台差异：LZ4_GIT_APPLY（sm8650/sm8750 用 git apply，sm8850 用 patch）
#          LZ4_ARMV8（sm8650/sm8750 额外覆盖 lz4armv8.S）
# 版本差异：LZ4_CLEARMAKE（仅 sm8750 6.6.50 / 6.6.89_mtk 额外应用 clearMake）
# ============================================================
source "$(dirname "$0")/../lib.sh"

echo "正在添加lz4 1.10.0 & zstd 1.5.7补丁…"
cd "$KS"
cp "$GITHUB_WORKSPACE/$PLATFORM_DIR/zram_patch/001-lz4.patch" "$COMMON/"
if [[ "${LZ4_CLEARMAKE:-0}" == "1" ]]; then
  cp "$GITHUB_WORKSPACE/$PLATFORM_DIR/zram_patch/001-lz4-clearMake.patch" "$COMMON/"
fi
if [[ "$LZ4_ARMV8" == "1" ]]; then
  cp "$GITHUB_WORKSPACE/$PLATFORM_DIR/zram_patch/lz4armv8.S" "$COMMON/lib"
fi
cp "$GITHUB_WORKSPACE/$PLATFORM_DIR/zram_patch/002-zstd.patch" "$COMMON/"
cd "$COMMON"
if [[ "$LZ4_GIT_APPLY" == "1" ]]; then
  git apply -p1 < 001-lz4.patch || true
  if [[ "${LZ4_CLEARMAKE:-0}" == "1" ]]; then
    git apply -p1 < 001-lz4-clearMake.patch || true
  fi
else
  patch -p1 < 001-lz4.patch || true
fi
patch -p1 < 002-zstd.patch || true
