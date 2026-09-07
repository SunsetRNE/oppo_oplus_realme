#!/bin/bash
# ============================================================
# 10 · 添加 KernelSU（5 分支：ReSukiSU / SukiSU / Next / 原版 / 无）
# 输出：ksuver → GITHUB_OUTPUT / KSUVER → GITHUB_ENV
# ============================================================
source "$(dirname "$0")/../lib.sh"

cd "$KS"
if [[ "$KSUTYPE" == "sukisu" || "$KSUTYPE" == "resukisu" ]]; then
  echo "正在配置ReSukiSU（由于SukiSU长期未维护无法正常编译，且ReSukiSU兼容sukisu管理器，故SukiSU源码仓库已重定向为resukisu）..."
  curl -LSs "https://raw.githubusercontent.com/ReSukiSU/ReSukiSU/refs/heads/main/kernel/setup.sh" | bash -s main
  echo 'CONFIG_KSU_FULL_NAME_FORMAT="%TAG_NAME%-%COMMIT_SHA%@SunsetRNE"' >> "$DEFCONFIG"
  cd ./KernelSU
  # 生成自定义版本号（基于提交计数）, 失败时使用 114514
  KSU_VERSION=$(expr $(git rev-list --count main) + 30700 2>/dev/null || echo 114514)
  # 存储版本号到 GitHub 环境变量
  echo "KSUVER=$KSU_VERSION" >> "$GITHUB_ENV"
  echo "ksuver=$KSU_VERSION" >> "$GITHUB_OUTPUT"
elif [[ "$KSUTYPE" == "ksunext" ]]; then
  echo "正在配置KernelSU Next..."
  curl -LSs "https://raw.githubusercontent.com/pershoot/KernelSU-Next/refs/heads/dev-susfs/kernel/setup.sh" | bash -s dev-susfs
  cd KernelSU-Next
  rm -rf .git
  KSU_VERSION=$(expr $(curl -sI "https://api.github.com/repos/pershoot/KernelSU-Next/commits?sha=dev&per_page=1" | grep -i "link:" | sed -n 's/.*page=\([0-9]*\)>; rel="last".*/\1/p') "+" 30000)
  echo "KSUVER=$KSU_VERSION" >> "$GITHUB_ENV"
  echo "ksuver=$KSU_VERSION" >> "$GITHUB_OUTPUT"
  sed -i "s/KSU_VERSION_FALLBACK := 1/KSU_VERSION_FALLBACK := $KSU_VERSION/g" kernel/Kbuild
  KSU_GIT_TAG=$(curl -sL "https://api.github.com/repos/KernelSU-Next/KernelSU-Next/tags" | grep -o '"name": *"[^"]*"' | head -n 1 | sed 's/"name": "//;s/"//')
  sed -i "s/KSU_VERSION_TAG_FALLBACK := v0.0.1/KSU_VERSION_TAG_FALLBACK := $KSU_GIT_TAG/g" kernel/Kbuild
  #为KernelSU Next添加WildKSU管理器支持
  cd ../common/drivers/kernelsu
  apply_self_patch "$PLATFORM_DIR/other_patch/apk_sign.patch" "-p2" "-N -F 3" || true
elif [[ "$KSUTYPE" == "ksu" ]]; then
  echo "正在配置原版 KernelSU (tiann/KernelSU)..."
  curl -LSs "https://raw.githubusercontent.com/SunsetRNE/KernelSU/refs/heads/main/kernel/setup.sh" | sed 's|https://github.com/tiann/KernelSU|https://github.com/SunsetRNE/KernelSU|g' | bash -s main
  cd ./KernelSU
  # 修复 O=out 分离构建下 KSU_KERNEL_DIR 相对路径解析错误（$(src) 为 ../drivers/kernelsu 时拼接出错，-I 指向不存在目录导致 klog.h 找不到）
  # 改为注入绝对 include 路径，稳定命中 KernelSU/kernel/include
  KSU_ABS_DIR="$(pwd)/kernel"
  sed -i "s|ccflags-y += -I\$(KSU_KERNEL_DIR) -I\$(KSU_KERNEL_DIR)/include|ccflags-y += -I${KSU_ABS_DIR} -I${KSU_ABS_DIR}/include|" kernel/Kbuild || true
  grep -n "ccflags-y += -I" kernel/Kbuild | head -5
  KSU_VERSION=$(expr $(curl -sI "https://api.github.com/repos/SunsetRNE/KernelSU/commits?sha=main&per_page=1" | grep -i "link:" | sed -n 's/.*page=\([0-9]*\)>; rel="last".*/\1/p') "+" 30000)
  echo "KSUVER=$KSU_VERSION" >> "$GITHUB_ENV"
  echo "ksuver=$KSU_VERSION" >> "$GITHUB_OUTPUT"
  sed -i "s/DKSU_VERSION=16/DKSU_VERSION=${KSU_VERSION}/" kernel/Kbuild
else
  echo "已选择无内置KernelSU模式，跳过KernelSU配置..."
fi
