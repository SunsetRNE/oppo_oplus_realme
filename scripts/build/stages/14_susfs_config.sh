#!/bin/bash
# ============================================================
# 14 · 添加 SUSFS 配置项（仅 susfs_enable=true 时调用）
# ============================================================
source "$(dirname "$0")/../lib.sh"

cd "$KS"
cfg "CONFIG_KSU_SUSFS=y"
cfg "CONFIG_KSU_SUSFS_HAS_MAGIC_MOUNT=y"
cfg "CONFIG_KSU_SUSFS_SUS_PATH=y"
cfg "CONFIG_KSU_SUSFS_SUS_MOUNT=y"
cfg "CONFIG_KSU_SUSFS_AUTO_ADD_SUS_KSU_DEFAULT_MOUNT=y"
cfg "CONFIG_KSU_SUSFS_AUTO_ADD_SUS_BIND_MOUNT=y"
cfg "CONFIG_KSU_SUSFS_SUS_KSTAT=y"
cfg "CONFIG_KSU_SUSFS_TRY_UMOUNT=y"
cfg "CONFIG_KSU_SUSFS_AUTO_ADD_TRY_UMOUNT_FOR_BIND_MOUNT=y"
cfg "CONFIG_KSU_SUSFS_SPOOF_UNAME=y"
cfg "CONFIG_KSU_SUSFS_ENABLE_LOG=y"
cfg "CONFIG_KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS=y"
cfg "CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG=y"
cfg "CONFIG_KSU_SUSFS_OPEN_REDIRECT=y"
cfg "CONFIG_KSU_SUSFS_SUS_MAP=y"
