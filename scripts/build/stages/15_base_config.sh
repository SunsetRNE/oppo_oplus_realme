#!/bin/bash
# ============================================================
# 15 · 添加 KSU & 其他配置项 + CVE 修复补丁
# ============================================================
source "$(dirname "$0")/../lib.sh"

cd "$KS"
cfg "CONFIG_KSU=y"
if [[ "$SUSFS_ENABLE" == "false" ]]; then
  cfg "CONFIG_KSU_SUSFS=n"
fi
# 添加对 Mountify (backslashxx/mountify) 模块的支持
cfg "CONFIG_TMPFS_XATTR=y"
cfg "CONFIG_TMPFS_POSIX_ACL=y"
if [[ "$LZ4KD_ENABLE" == "true" ]]; then
  cfg "CONFIG_ZSMALLOC=y"
  cfg "CONFIG_CRYPTO_LZ4HC=y"
  cfg "CONFIG_CRYPTO_LZ4K=y"
  cfg "CONFIG_CRYPTO_LZ4KD=y"
  cfg "CONFIG_CRYPTO_842=y"
  #以下配置选项用于编译zram模块，开启与否不影响内核编译
  cfg "CONFIG_ZRAM_BACKEND_LZ4HC=y"
  cfg "CONFIG_ZRAM_BACKEND_LZ4K=y"
  cfg "CONFIG_ZRAM_BACKEND_LZ4KD=y"
  cfg "CONFIG_ZRAM_BACKEND_842=y"
fi
# 开启O2编译优化配置
cfg "CONFIG_CC_OPTIMIZE_FOR_PERFORMANCE=y"
# 禁用 defconfig 检查
sed -i 's/check_defconfig//' "$COMMON/build.config.gki"
#跳过将uapi标准头安装到 usr/include 目录的不必要操作，节省编译时间
cfg "CONFIG_HEADERS_INSTALL=n"
# 6.12内核Rust配置（仅 sm8850）
if [[ "$HAS_RUST" == "1" ]]; then
  cfg "CONFIG_RUST=y"
  cfg "CONFIG_ANDROID_BINDER_IPC_RUST=m"
fi
# 应用 CVE_2026_43499 修复补丁
cd "$COMMON"
apply_self_patch "$PLATFORM_DIR/other_patch/$CVE_PATCH" "-p1" "-F 3"
