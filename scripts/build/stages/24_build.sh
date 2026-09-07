#!/bin/bash
# ============================================================
# 24 · 构建内核
#   - fakestat/faketime 时间劫持 wrapper（确定性构建，配合 ccache）
#   - HAS_RUST=1（sm8850）：Rust 环境 + gendwarfksyms 路径重映射
#   - HAS_RUST=0（sm8650/sm8750）：内联 KCFLAGS 直接 make
# ============================================================
source "$(dirname "$0")/../lib.sh"

WORKDIR="$GITHUB_WORKSPACE"
export PATH="/usr/lib/ccache:$PATH"
export PATH="$WORKDIR/kernel_workspace/$CLANG_DIR/bin:$PATH"
export PATH="$WORKDIR/kernel_workspace/build-tools/bin:$PATH"
if [[ "$HAS_RUST" == "1" ]]; then
  export PATH="$WORKDIR/kernel_workspace/rust/bin:$PATH"
fi
CLANG_DIR_ABS="$WORKDIR/kernel_workspace/$CLANG_DIR/bin"
CLANG_VERSION="$($CLANG_DIR_ABS/clang --version | head -n 1)"
LLD_VERSION="$($CLANG_DIR_ABS/ld.lld --version | head -n 1)"
echo "编译器信息:"
echo "Clang版本: $CLANG_VERSION"
echo "LLD版本: $LLD_VERSION"
if [[ "$HAS_RUST" == "1" ]]; then
  RUSTC_VERSION="$(rustc -V 2>/dev/null | head -n1)"
  BINDGEN_VERSION="$(bindgen --version 2>/dev/null | head -n1)"
  echo "Rustc版本: $RUSTC_VERSION"
  echo "Bindgen版本: $BINDGEN_VERSION"
fi
pahole_version=$(pahole --version 2>/dev/null | head -n1); [ -z "$pahole_version" ] && echo "pahole版本：未安装" || echo "pahole版本：$pahole_version"

export CCACHE_LOGFILE="$GITHUB_WORKSPACE/kernel_workspace/ccache.log"
export CCACHE_COMPILERCHECK="none"
export CCACHE_BASEDIR="$GITHUB_WORKSPACE"
export CCACHE_NOHASHDIR="true"
export CCACHE_NOHARDLINK="true"
export CCACHE_DIR="$CCACHE_DIR"
export CCACHE_MAXSIZE="3G"
export CCACHE_IS_KERNEL_COMPILING="true"
echo "sloppiness = file_stat_matches,include_file_ctime,include_file_mtime,pch_defines,file_macro,time_macros" >> "$CCACHE_DIR/ccache.conf"

cd "$COMMON"
cp "$GITHUB_WORKSPACE/$PLATFORM_DIR/lib/libfakestat.so" .
cp "$GITHUB_WORKSPACE/$PLATFORM_DIR/lib/libfaketimeMT.so" .
chmod 777 ./*.so
export FAKESTAT="2025-05-25 12:00:00"
export FAKETIME="@2025-05-25 13:00:00"
echo "FAKESTAT=$FAKESTAT" >> "$GITHUB_ENV"
echo "FAKETIME=$FAKETIME" >> "$GITHUB_ENV"
SO_DIR=$(pwd)
export PRELOAD_LIBS="$SO_DIR/libfakestat.so $SO_DIR/libfaketimeMT.so"
if [[ "$HAS_RUST" == "1" ]]; then
  export REAL_CLANG_PATH="$WORKDIR/kernel_workspace/$CLANG_DIR/bin/clang"
fi
#创建 CC (编译器) 包装器
echo '#!/bin/bash' > cc-wrapper
echo 'export LD_PRELOAD="'$PRELOAD_LIBS'"' >> cc-wrapper
echo 'export FAKESTAT="'$FAKESTAT'"' >> cc-wrapper
echo 'export FAKETIME="'$FAKETIME'"' >> cc-wrapper
if [[ "$HAS_RUST" == "1" ]]; then
  echo 'ccache $REAL_CLANG_PATH "$@"' >> cc-wrapper
else
  echo 'ccache clang "$@"' >> cc-wrapper
fi
#创建 LD (链接器) 包装器
echo '#!/bin/bash' > ld-wrapper
echo 'export LD_PRELOAD="'$PRELOAD_LIBS'"' >> ld-wrapper
echo 'export FAKESTAT="'$FAKESTAT'"' >> ld-wrapper
echo 'export FAKETIME="'$FAKETIME'"' >> ld-wrapper
echo 'ld.lld "$@"' >> ld-wrapper

# 测试时间劫持测试是否正常工作
echo "--- [Wrapper Test] 正在创建通用的时间劫持测试脚本 ---"
echo '#!/bin/bash' > test-wrapper.sh
echo 'export LD_PRELOAD="'$PRELOAD_LIBS'"' >> test-wrapper.sh
echo 'export FAKESTAT="'$FAKESTAT'"' >> test-wrapper.sh
echo 'export FAKETIME="'$FAKETIME'"' >> test-wrapper.sh
echo 'echo ">>> Wrapper 内部环境检查完毕."' >> test-wrapper.sh
echo 'exec "$@"' >> test-wrapper.sh # 执行所有传入的参数
chmod +x test-wrapper.sh
echo "--- [Wrapper Test] 正在测试 (date) 命令 ---"
./test-wrapper.sh date
echo "--- [Wrapper Test] 正在测试 (stat) 命令 ---"
./test-wrapper.sh stat ./Makefile
echo "--- [Wrapper Test] 测试完毕 ---"
chmod +x cc-wrapper ld-wrapper
echo "--- 编译前环境时间: $(LD_PRELOAD=$PRELOAD_LIBS date) ---"
echo "--- 编译前环境文件时间戳: ---"
LD_PRELOAD=$PRELOAD_LIBS stat ./Makefile

if [[ "$HAS_RUST" == "1" ]]; then
  # 6.12内核make编译核心配置：
  # 1. 重映射物理路径 (由于6.12内核引入了Rust代码，计算内核符号版本的工具变成了gendwarfksyms，而gendwarfksyms无法正确预处理绝对路径，故我们需要手动把绝对路径重映射为相对路径，否则内核符号校验值会大面积出错)
  COMMON_REAL_PATH=$(pwd -P)
  ROOT_REAL_PATH=$(dirname "$COMMON_REAL_PATH")
  KCFLAGS+=" -fdebug-prefix-map=$ROOT_REAL_PATH=."
  KCFLAGS+=" -fmacro-prefix-map=$ROOT_REAL_PATH=."
  KCFLAGS+=" -ffile-prefix-map=$ROOT_REAL_PATH=."
  # 2. 声明Rust等工具（此处若不进行声明，内核编译前的Rust环境预检测脚本scripts/rust_is_available.sh会检测失败，导致内核无法正常开启Rust代码编译）
  export RUSTC="rustc"
  export BINDGEN="bindgen"
  export CC="clang"
  export LIBCLANG_PATH="$WORKDIR/kernel_workspace/$CLANG_DIR/lib"
  # 3. 配置KCFLAGS
  KCFLAGS+=" -no-canonical-prefixes"
  KCFLAGS+=" -O2"
  KCFLAGS+=" -pipe"
  KCFLAGS+=" -Wno-error"
  KCFLAGS+=" -fno-stack-protector"
  KCFLAGS+=" -D__ANDROID_COMMON_KERNEL__"
  export KCFLAGS
  # 4. 配置其他工具及选项（非必须，防错冗余）
  export HOSTCC=clang
  export LD="ld.lld"
  export HOSTLD=ld.lld
  export LLVM=1 LLVM_IAS=1
  export ARCH=arm64 SUBARCH=arm64
  export CROSS_COMPILE=aarch64-linux-gnu-
  export LD=ld.lld HOSTLD=ld.lld AR=llvm-ar NM=llvm-nm AS=clang READELF=llvm-readelf
  export OBJCOPY=llvm-objcopy OBJDUMP=llvm-objdump OBJSIZE=llvm-size STRIP=llvm-strip
  # 5. 编译前运行官方环境配置脚本
  source "./_setup_env.sh" 2>/dev/null || true
fi

#在构建内核的同时清除不必要的.NET, Android NDK, Haskell, CodeQL运行库，清理空间且不阻塞后续步骤运行
sudo rm -rf /usr/share/dotnet &
sudo rm -rf /usr/local/lib/android &
sudo rm -rf /opt/ghc &
sudo rm -rf /opt/hostedtoolcache/CodeQL &
if [[ "$HAS_RUST" == "1" ]]; then
  make -j"$(nproc --all)" LLVM=1 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- CC="clang" LD="ld.lld" OBJCOPY="llvm-objcopy" O=out gki_defconfig &&
  export CC="$(pwd)/cc-wrapper" && export LD="$(pwd)/ld-wrapper" &&
  make -j"$(nproc --all)" LLVM=1 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- CC="$(pwd)/cc-wrapper" LD="$(pwd)/ld-wrapper" OBJCOPY="llvm-objcopy" O=out Image
else
  make -j"$(nproc --all)" LLVM=1 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- CC="ccache clang" LD="ld.lld" HOSTLD=ld.lld O=out KCFLAGS+=-O2 KCFLAGS+=-Wno-error gki_defconfig &&
  make -j"$(nproc --all)" LLVM=1 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- CC="$(pwd)/cc-wrapper" LD="$(pwd)/ld-wrapper" HOSTLD=ld.lld O=out KCFLAGS+=-O2 KCFLAGS+=-Wno-error Image
fi

# 编译后时间劫持二次校验
echo "--- 编译后环境时间: $(LD_PRELOAD=$PRELOAD_LIBS date) ---"
echo "--- 编译后环境文件时间戳: ---"
LD_PRELOAD=$PRELOAD_LIBS stat ./Makefile
echo "内核编译完成！"
if [[ "$CCACHE_DEBUG" == "true" ]]; then
  echo "正在打包ccache日志及调试信息..."
  cd "$KS"
  cp ./common/out/vmlinux.symvers ./vmlinux.symvers
  cp ./common/out/.config ./config
  zip -r9 debug.zip ccache.log config vmlinux.symvers
fi
echo "ccache状态："
ccache -s
echo "编译后空间:"
df -h
