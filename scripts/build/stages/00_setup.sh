#!/bin/bash
# ============================================================
# 00 · 安装环境依赖 + 初始化源码仓库及工具链
# 下载：内核源码（SRC_URL/SRC_DIRNAME）、LLVM 工具链、Rust（可选）、build-tools
# 收尾：去除 ABI 保护（可选）与 -dirty 后缀
# ============================================================
source "$(dirname "$0")/../lib.sh"

rm -rf kernel_workspace
mkdir kernel_workspace
cd kernel_workspace
echo "当前仓库：$GITHUB_REPOSITORY"
echo "当前分支：$GITHUB_REF_NAME"

sudo apt-mark hold firefox &&
sudo apt-mark hold libc-bin &&
sudo apt purge man-db &&
sudo rm -rf /var/lib/man-db/auto-update &&
sudo apt update &&
sudo apt-get install -y --no-install-recommends binutils python-is-python3 libssl-dev libelf-dev libdw-dev &

# 使用最新版 ccache v4.12.2（Ubuntu 软件仓库的版本并非最新）
cp "$GITHUB_WORKSPACE/$PLATFORM_DIR/lib/ccache-x86-64" ./ccache &&
sudo cp -f ./ccache /usr/bin/ccache &&
sudo chmod +x /usr/bin/ccache &&
rm -f ./ccache &

echo "正在克隆源码仓库..."
aria2c -s16 -x16 -k1M "$SRC_URL" -o common.zip &&
unzip -q common.zip &&
mv "$SRC_DIRNAME" common &&
rm -rf common.zip &

echo "正在克隆${CLANG_LABEL}工具链..." &&
mkdir -p "$CLANG_DIR" &&
aria2c -s16 -x16 -k1M "$TOOLCHAIN_BASE/$CLANG_ZIP" -o clang.zip &&
unzip -q clang.zip -d "$CLANG_DIR" &&
rm -rf clang.zip &

if [[ "$HAS_RUST" == "1" ]]; then
  echo "正在克隆Rust 1.82.0工具链..." &&
  mkdir -p rust &&
  aria2c -s16 -x16 -k1M "$TOOLCHAIN_BASE/rust.zip" -o rust.zip &&
  unzip -q rust.zip -d rust &&
  rm -rf rust.zip &
fi

echo "正在克隆构建工具..." &&
aria2c -s16 -x16 -k1M "$TOOLCHAIN_BASE/build-tools.zip" -o build-tools.zip &&
unzip -q build-tools.zip &&
rm -rf build-tools.zip &

wait
echo "所有源码及${CLANG_LABEL}工具链初始化完成！"
echo "正在去除 ABI 保护 & 去除 dirty 后缀..."
if [[ "$ABI_PROTECT_RM" == "1" ]]; then
  rm common/android/abi_gki_protected_exports_* || true
fi
for f in common/scripts/setlocalversion; do
  sed -i 's/ -dirty//g' "$f"
  sed -i '$i res=$(echo "$res" | sed '\''s/-dirty//g'\'')' "$f"
done
