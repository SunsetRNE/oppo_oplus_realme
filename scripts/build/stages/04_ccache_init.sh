#!/bin/bash
# ============================================================
# 04 · 初始化并配置 ccache
# ============================================================
source "$(dirname "$0")/../lib.sh"

# 设置ccache环境变量
export CCACHE_COMPILERCHECK="none"
export CCACHE_BASEDIR="$GITHUB_WORKSPACE"
export CCACHE_NOHASHDIR="true"
export CCACHE_NOHARDLINK="true"
export CCACHE_DIR="$CCACHE_DIR"
export CCACHE_MAXSIZE="$CCACHE_MAXSIZE"

# 确保ccache目录存在
mkdir -p "$CCACHE_DIR"

# 每次运行都重新配置缓存大小
echo "配置ccache缓存大小为: $CCACHE_MAXSIZE"
ccache -M "$CCACHE_MAXSIZE"
ccache -o compression=true

# 显示初始缓存状态
echo "ccache初始状态:"
ccache -s

# 如果缓存恢复命中，显示详细信息
if [ "${CACHE_HIT:-false}" == 'true' ]; then
  echo "ccache缓存命中详情:"
  ccache -sv
fi
