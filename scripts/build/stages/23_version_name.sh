#!/bin/bash
# ============================================================
# 23 · 添加制作名称（内核版本后缀）
#   - setlocalversion 末尾 echo 行替换为自定义后缀（或 KERNEL_NAME）
#   - DEFCONFIG_SUFFIX_SED=1 的平台同步替换 defconfig 内 -4k 标记
#   - 修复历史 bug：原 workflow 误写 inputs.KERNEL_SUFFIX（大小写错误），
#     导致 defconfig 的 -4k 被空串剥离而非替换成自定义后缀
# ============================================================
source "$(dirname "$0")/../lib.sh"

cd "$KS"
echo "替换内核版本后缀..."
if [[ -n "$KERNEL_SUFFIX" ]]; then
  echo "当前内核版本后缀：$KERNEL_SUFFIX"
  for f in "$COMMON/scripts/setlocalversion"; do
    sed -i "\$s|echo \"\$res\"|echo \"-$KERNEL_SUFFIX\"|" "$f"
  done
  if [[ "$DEFCONFIG_SUFFIX_SED" == "1" ]]; then
    sudo sed -i "s/-4k/-$KERNEL_SUFFIX/g" "$DEFCONFIG"
  fi
else
  echo "当前内核版本后缀：$KERNEL_NAME"
  for f in "$COMMON/scripts/setlocalversion"; do
    sed -i "\$s|echo \"\$res\"|echo \"-$KERNEL_NAME\"|" "$f"
  done
  if [[ "$DEFCONFIG_SUFFIX_SED" == "1" ]]; then
    sudo sed -i "s/-4k/-$KERNEL_NAME/g" "$DEFCONFIG"
  fi
fi
sed -i 's/${scm_version}//' "$COMMON/scripts/setlocalversion"
cfg "CONFIG_LOCALVERSION_AUTO=n"
