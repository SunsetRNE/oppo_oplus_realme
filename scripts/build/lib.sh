#!/bin/bash
# ============================================================
# 链路 B 编译脚本公共库
# ============================================================
# 所有 stage 脚本均通过 `source lib.sh` 获得：
#   - 通用工具函数（log / warn / die / is_true）
#   - 工作目录常量（KS / COMMON / DEFCONFIG）
#   - 平台配置（sm*/build.conf 按 PLATFORM_DIR 自动加载）
#
# 依赖 env（由 workflow 顶层 env / job env 注入）：
#   PLATFORM_DIR  / ANDROID_VERSION / KERNEL_VERSION / SUB_VERSION /
#   KERNEL_NAME   / CCACHE_KEY      / SRC_URL        / SRC_DIRNAME /
#   以及各类输入开关（KSUTYPE / SUSFS_ENABLE / LZ4_ENABLE / ...）
# ============================================================

GITHUB_WORKSPACE="${GITHUB_WORKSPACE:-$(pwd)}"
PLATFORM_DIR="${PLATFORM_DIR:?❌ 未设置 PLATFORM_DIR（sm8650/sm8750/sm8850）}"

# ---- ccache v4.12+ 布尔环境变量兼容 ----
# workflow 的 ccache_debug 布尔输入默认 false；ccache v4.12 起布尔环境变量
# 仅接受 true（false 会报 "invalid boolean environment variable value" 并退出），
# 使 make gki_defconfig 的编译器探测（cc-version.sh → ccache clang -E）输出为空：
#   ccache clang: unknown C compiler
#   scripts/Kconfig.include:44: Sorry, this C compiler is not supported.
# 因此非 true 时统一取消该变量（需要调试日志时请在 workflow 输入中显式传 true）。
[[ "${CCACHE_DEBUG:-}" == "true" ]] || unset CCACHE_DEBUG

# ---- 平台配置（sm8650/sm8750/sm8850/build.conf）----
CONF_FILE="$GITHUB_WORKSPACE/$PLATFORM_DIR/build.conf"
if [[ -f "$CONF_FILE" ]]; then
  # shellcheck source=/dev/null
  source "$CONF_FILE"
else
  echo "❌ 找不到平台配置: $CONF_FILE" >&2
  exit 1
fi

# ---- 目录常量 ----
KS="$GITHUB_WORKSPACE/kernel_workspace"          # 工作区根
COMMON="$KS/common"                              # 内核源码树
DEFCONFIG="$COMMON/arch/arm64/configs/gki_defconfig"

# ---- 工具函数 ----
log()  { echo -e "\033[36m▶\033[0m $*"; }
warn() { echo -e "\033[33m⚠️ $*\033[0m"; }
die()  { echo -e "\033[31m❌ $*\033[0m" >&2; exit 1; }

# 输入开关判断（workflow boolean input → env 字符串 'true'/'false'）
is_true() { [[ "${!1:-false}" == "true" ]]; }

# 复制仓库内补丁到当前目录并按指定 strip 级别应用
# apply_self_patch <仓库相对路径> <strip参数,默认 -p1> [额外 patch 参数]
apply_self_patch() {
  local src="$GITHUB_WORKSPACE/$1"
  local strip="${2:--p1}"
  local extra="${3:-}"
  local name
  name="$(basename "$src")"
  [[ -f "$src" ]] || die "仓库内文件不存在: $1"
  cp "$src" "./$name"
  # shellcheck disable=SC2086
  patch "$strip" $extra < "./$name"
}

# 向 gki_defconfig 追加一行
cfg() { echo "$1" >> "$DEFCONFIG"; }
