#!/bin/bash
# ============================================================
# 18 · 启用 Droidspaces 容器支持（droidspaces_enable != false 时生效）
# 必须补丁清单与 extend 分支差异由平台 build.conf 控制
# ============================================================
source "$(dirname "$0")/../lib.sh"

if [[ "$DROIDSPACES_ENABLE" == "false" ]]; then
  echo "未启用 Droidspaces 容器支持，跳过。"
  exit 0
fi
echo "正在启用 Droidspaces 容器支持..."
cd "$COMMON"
# 应用 Droidspaces 容器必须补丁
for p in "${DROIDSPACES_PATCHES[@]}"; do
  apply_self_patch "$PLATFORM_DIR/droidspaces_patch/$p" "-p1" "-F 3" || true
done
# 开启 Droidspaces 容器所需内核支持
cfg "CONFIG_PID_NS=y"
cfg "CONFIG_IPC_NS=y"
cfg "CONFIG_USER_NS=y"
cfg "CONFIG_SYSVIPC=y"
cfg "CONFIG_DEVTMPFS=y"
cfg "CONFIG_NAMESPACES=y"
cfg "CONFIG_POSIX_MQUEUE=y"
cfg "CONFIG_NETFILTER_XT_MATCH_ADDRTYPE=y"
cfg "CONFIG_NETFILTER_XT_TARGET_LOG=y"
cfg "CONFIG_NETFILTER_XT_MATCH_RECENT=y"
# 未经测试的配置选项，可能导致bug
#cfg "CONFIG_CGROUP_DEVICE=y"
#cfg "CONFIG_CGROUP_PIDS=y"
#cfg "CONFIG_FW_LOADER_COMPRESS=y"
#cfg "CONFIG_BRIDGE_NETFILTER=y"
#cfg "CONFIG_NF_TABLES=y"
# 开启 NTSync
cfg "CONFIG_NTSYNC=y"
if [[ "$DROIDSPACES_ENABLE" == "extend" ]]; then
  echo "正在启用容器环境扩展支持..."
  # 开启虚拟 HCI 设备支持
  cfg "CONFIG_BT_HCIVHCI=y"
  # 开启 systemd-coredump 支持
  cfg "CONFIG_STATIC_USERMODEHELPER=n"
  # 添加 Lindroid EVDI DRM 驱动（仅 DROIDSPACES_EVDI=1 的平台）
  if [[ "$DROIDSPACES_EVDI" == "1" ]]; then
    apply_self_patch "$PLATFORM_DIR/droidspaces_patch/evdi_drm.patch" "-p1" "-F 3" || true
    cfg "CONFIG_DRM_LINDROID_EVDI=y"
  fi
fi
