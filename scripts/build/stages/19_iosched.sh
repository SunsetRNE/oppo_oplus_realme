#!/bin/bash
# ============================================================
# 19 · 启用 IO 调度器（adios 或 ssg，由平台 build.conf 决定）
# ============================================================
source "$(dirname "$0")/../lib.sh"

cd "$KS"
if [[ "$IOSCHED" == "adios" ]]; then
  echo "正在启用ADIOS IO调度器(将截止时间优先调度算法与基于自主学习的自适应延迟控制算法相结合, 降低I/O延迟)…"
  cfg "CONFIG_MQ_IOSCHED_ADIOS=y"
  cfg "CONFIG_MQ_IOSCHED_DEFAULT_ADIOS=y"
else
  echo "正在启用三星SSG IO调度器(一加12等极少数机型开启后可能不开机,若出现bug请关闭此项)…"
  cfg "CONFIG_MQ_IOSCHED_SSG=y"
  cfg "CONFIG_MQ_IOSCHED_SSG_CGROUP=y"
fi
