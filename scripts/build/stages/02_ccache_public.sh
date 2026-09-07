#!/bin/bash
# ============================================================
# 02 · 拉取公共预置 ccache 缓存（SunsetRNE/public_ccache release）
# 仅当本地 actions/cache 未命中时执行
# ============================================================
source "$(dirname "$0")/../lib.sh"

echo "检查本地缓存状态..."
if [ -d "$CCACHE_DIR" ] && [ "$(ls -A "$CCACHE_DIR" 2>/dev/null)" ]; then
  echo "检测到本地已成功载入 ccache 缓存，跳过公共 ccache 拉取！"
  exit 0
fi

echo "未命中缓存，尝试拉取最新公共 ccache ..."
mkdir -p "$CCACHE_DIR"
if [[ "$DROIDSPACES_ENABLE" != "false" ]]; then
  FILE_NAME="ccache-$KERNEL_VERSION.$SUB_VERSION-Droidspaces.tar.zst"
else
  FILE_NAME="ccache-$KERNEL_VERSION.$SUB_VERSION.tar.zst"
fi

if gh release download -p "$FILE_NAME" -R SunsetRNE/public_ccache; then
  echo "成功下载 $FILE_NAME，正在解压..."
  tar -I zstd -xf "$FILE_NAME" -C "$CCACHE_DIR"
  echo "公共 ccache 恢复完成！"
else
  echo "公共 ccache 中未找到对应的 ccache 文件，将进行全量全新编译..."
fi
