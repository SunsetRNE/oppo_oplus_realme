#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
链路 B 工作流生成器（薄壳化）
============================
从旧版完整 fastbuild 工作流中提取每个版本的参数（表单 inputs / env / 源码 URL /
发布文案），渲染为"薄壳工作流 + scripts/build/stages/* 共享编译脚本"的新结构。

用法（在仓库根目录）：
    python3 scripts/build/gen_workflows.py          # 生成全部 21 个工作流
    python3 scripts/build/gen_workflows.py --dry-run

平台差异由 sm*/build.conf 承载；本脚本只负责每版本差异（SUB_VERSION/KERNEL_NAME/
CCACHE_KEY/SRC_URL/发布文案/BETTERNET_BPF/表单默认值）。
"""
import glob
import os
import re
import sys

import yaml

DRY = "--dry-run" in sys.argv
WF_DIR = ".github/workflows"

# ---- 平台级常量（与 sm*/build.conf 对应）----
PLATFORMS = {
    "sm8650": {
        "setup_label": "安装环境依赖+初始化源码仓库及llvm-Clang20工具链",
        "iosched_step": "启用三星SSG IO调度器",
        "iosched_input": "ssg_enable",
        "clean_sub": False,
        "ksu_official": "KernelSU (Official)",
        "iosched_note": "三星SSG IO调度器支持",
    },
    "sm8750": {
        "setup_label": "安装环境依赖+初始化源码仓库及llvm-Clang18工具链",
        "iosched_step": "启用ADIOS IO调度器",
        "iosched_input": "adios_enable",
        "clean_sub": True,
        "ksu_official": "KSU",
        "iosched_note": "ADIOS IO调度器支持",
    },
    "sm8850": {
        "setup_label": "安装环境依赖+初始化源码仓库及llvm-clang19工具链",
        "iosched_step": "启用ADIOS IO调度器",
        "iosched_input": "adios_enable",
        "clean_sub": True,
        "ksu_official": "KSU",
        "iosched_note": "ADIOS IO调度器支持",
    },
}


def load_old(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    w = yaml.safe_load(text)
    trigger = (w or {}).get(True) or (w or {}).get("on") or {}
    inputs = trigger.get("workflow_dispatch", {}).get("inputs", {})
    env = (w or {}).get("env", {}) or {}
    return w, env, inputs, text


def extract_inputs_block(text):
    """提取 on: 到 jobs: 之间的原文（表单 inputs 原样保留）。"""
    m = re.search(r"(^on:\n.*?)^jobs:", text, re.S | re.M)
    if not m:
        raise ValueError("找不到 on:/jobs: 块")
    return m.group(1)


def extract_src(text, env):
    url = re.search(r"aria2c -s16 -x16 -k1M (https://[^\s]*\.zip) -o common\.zip", text)
    d = re.search(r'mv "([^"]+)" common', text)
    if url and d:
        return url.group(1), d.group(1)
    # 薄壳格式：参数在 env 头
    if env.get("SRC_URL") and env.get("SRC_DIRNAME"):
        return env["SRC_URL"], env["SRC_DIRNAME"]
    raise ValueError("找不到源码 URL / 目录名")


def extract_release_lines(text):
    title = re.search(r"(### 📱 [^\n]+)", text)
    device = re.search(r"(- 机型：[^\n]+)", text)
    if not title or not device:
        raise ValueError("找不到发布标题 / 机型行")
    return title.group(1), device.group(1)


def quote(s):
    return "'" + str(s).replace("'", "''") + "'"


def render(platform, w, env, inputs_block, src_url, src_dirname, title_line, device_line, bpf, lz4_clearmake):
    p = PLATFORMS[platform]
    iosched_in = p["iosched_input"]
    # 设置环境变量 step（发布 job）
    if p["clean_sub"]:
        clean_lines = (
            "          CLEAN_SUB_VERSION=\"${{ env.SUB_VERSION }}\"\n"
            "          CLEAN_SUB_VERSION=\"${CLEAN_SUB_VERSION%_mtk}\"\n"
        )
    else:
        clean_lines = ""
    if p["clean_sub"]:
        full_lines = (
            "          if [[ -n \"${{ github.event.inputs.kernel_suffix }}\" ]]; then\n"
            "            FULL_VERSION=${{ env.KERNEL_VERSION }}.${CLEAN_SUB_VERSION}-${{ github.event.inputs.kernel_suffix }}\n"
            "            echo \"FULL_VERSION=$FULL_VERSION\" >> $GITHUB_ENV\n"
            "            export FULL_VERSION=$FULL_VERSION\n"
            "          else\n"
            "            FULL_VERSION=${{ env.KERNEL_VERSION }}.${CLEAN_SUB_VERSION}-${{ env.KERNEL_NAME }}\n"
            "            echo \"FULL_VERSION=$FULL_VERSION\" >> $GITHUB_ENV\n"
            "            export FULL_VERSION=$FULL_VERSION\n"
            "          fi\n"
        )
    else:
        full_lines = (
            "          if [[ -n \"${{ github.event.inputs.kernel_suffix }}\" ]]; then\n"
            "            FULL_VERSION=${{ env.KERNEL_VERSION }}.${{ env.SUB_VERSION }}-${{ github.event.inputs.kernel_suffix }}\n"
            "            echo \"FULL_VERSION=$FULL_VERSION\" >> $GITHUB_ENV\n"
            "            export FULL_VERSION=$FULL_VERSION\n"
            "          else\n"
            "            FULL_VERSION=${{ env.KERNEL_VERSION }}.${{ env.SUB_VERSION }}-${{ env.KERNEL_NAME }}\n"
            "            echo \"FULL_VERSION=$FULL_VERSION\" >> $GITHUB_ENV\n"
            "            export FULL_VERSION=$FULL_VERSION\n"
            "          fi\n"
        )
    env_head = []
    for k in ("TZ", "ANDROID_VERSION", "KERNEL_VERSION", "SUB_VERSION", "KERNEL_NAME", "CCACHE_KEY"):
        if k in env:
            env_head.append(f"  {k}: {quote(env[k])}")
    env_head.append(f"  PLATFORM_DIR: {quote(platform)}")
    env_head.append(f"  SRC_URL: {quote(src_url)}")
    env_head.append(f"  SRC_DIRNAME: {quote(src_dirname)}")
    if bpf:
        env_head.append("  BETTERNET_BPF: '1'")
    if lz4_clearmake:
        env_head.append("  LZ4_CLEARMAKE: '1'")

    yml = f"""name: {w['name']}

# 薄壳工作流：全部编译逻辑位于 scripts/build/stages/（共享），
# 平台差异位于 {platform}/build.conf，本文件仅承载每版本参数与表单。
env:
{chr(10).join(env_head)}

{inputs_block}jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      ksuver: ${{{{ steps.ksu_version.outputs.ksuver }}}}
      ak3name: ${{{{ steps.create_zip.outputs.ak3name }}}}
    permissions:
      actions: write
      contents: read
    env:
      GH_TOKEN: ${{{{ github.token }}}}
      KSUTYPE: ${{{{ inputs.ksu_type }}}}
      SUSFS_ENABLE: ${{{{ inputs.susfs_enable }}}}
      KPM_ENABLE: ${{{{ inputs.kpm_enable }}}}
      LZ4_ENABLE: ${{{{ inputs.lz4_enable }}}}
      LZ4KD_ENABLE: ${{{{ inputs.lz4kd_enable }}}}
      BBR_ENABLE: ${{{{ inputs.bbr_enable }}}}
      DROIDSPACES_ENABLE: ${{{{ inputs.droidspaces_enable }}}}
      BETTER_NET: ${{{{ inputs.better_net }}}}
      {iosched_in.upper()}: ${{{{ inputs.{iosched_in} }}}}
      REKERNEL_ENABLE: ${{{{ inputs.rekernel_enable }}}}
      BASEBAND_GUARD: ${{{{ inputs.baseband_guard }}}}
      UNICODE_FIX: ${{{{ inputs.unicode_fix }}}}
      CCACHE_UPDATE: ${{{{ inputs.ccache_update }}}}
      CCACHE_DEBUG: ${{{{ inputs.ccache_debug }}}}
      KERNEL_SUFFIX: ${{{{ inputs.kernel_suffix }}}}
    steps:
      - name: 拉取仓库代码
        uses: actions/checkout@v4

      - name: {p['setup_label']}
        run: bash scripts/build/stages/00_setup.sh

      - name: 配置ccache目录
        run: bash scripts/build/stages/01_ccache_env.sh

      - name: 载入当前版本内核的 ccache缓存
        uses: actions/cache@v5
        id: ccache-restore
        with:
          path: ${{{{ env.CCACHE_DIR }}}}
          key: ${{{{ env.CCACHE_REAL_KEY }}}}-${{{{ runner.os }}}}-${{{{ github.ref_name }}}}
          restore-keys: |
            ${{{{ env.CCACHE_REAL_KEY }}}}-${{{{ runner.os }}}}-
            ${{{{ env.CCACHE_REAL_KEY }}}}-

      - name: 拉取公共预置 ccache 缓存
        run: bash scripts/build/stages/02_ccache_public.sh

      - name: 清除旧 ccache 缓存
        if: inputs.ccache_update
        run: bash scripts/build/stages/03_ccache_clear.sh

      - name: 初始化并配置ccache
        env:
          CACHE_HIT: ${{{{ steps.ccache-restore.outputs.cache-hit }}}}
        run: bash scripts/build/stages/04_ccache_init.sh

      - name: 添加KernelSU
        id: ksu_version
        run: bash scripts/build/stages/10_ksu.sh

      - name: 应用 KernelSU & SUSFS 补丁
        if: inputs.susfs_enable
        run: bash scripts/build/stages/11_susfs.sh

      - name: 应用lz4 1.10.0 & zstd 1.5.7补丁
        if: inputs.lz4_enable
        run: bash scripts/build/stages/12_lz4.sh

      - name: 应用 lz4kd 补丁
        if: inputs.lz4kd_enable
        run: bash scripts/build/stages/13_lz4kd.sh

      - name: 添加SUSFS 配置项
        if: inputs.susfs_enable
        run: bash scripts/build/stages/14_susfs_config.sh

      - name: 添加 KSU & 其他配置项
        run: bash scripts/build/stages/15_base_config.sh

      - name: 启用网络功能增强优化配置
        if: inputs.better_net
        run: bash scripts/build/stages/16_better_net.sh

      - name: 添加 BBR 等一系列拥塞控制算法
        run: bash scripts/build/stages/17_bbr.sh

      - name: 启用 Droidspaces 容器支持
        run: bash scripts/build/stages/18_droidspaces.sh

      - name: {p['iosched_step']}
        if: inputs.{iosched_in}
        run: bash scripts/build/stages/19_iosched.sh

      - name: 启用Re-Kernel支持
        if: inputs.rekernel_enable
        run: bash scripts/build/stages/20_rekernel.sh

      - name: 启用内核级基带保护
        if: inputs.baseband_guard
        run: bash scripts/build/stages/21_bbg.sh

      - name: 应用零宽字符漏洞修复补丁（可选）
        if: inputs.unicode_fix
        run: bash scripts/build/stages/22_unicode_fix.sh

      - name: 添加制作名称
        run: bash scripts/build/stages/23_version_name.sh

      - name: 构建内核
        run: bash scripts/build/stages/24_build.sh

      - name: 保存新的 ccache 缓存
        if: inputs.ccache_update || steps.ccache-restore.outputs.cache-hit != 'true'
        uses: actions/cache/save@v5
        with:
          path: ${{{{ env.CCACHE_DIR }}}}
          key: ${{{{ env.CCACHE_REAL_KEY }}}}-${{{{ runner.os }}}}-${{{{ github.ref_name }}}}

      - name: 应用KPM并修补内核
        if: inputs.kpm_enable
        run: bash scripts/build/stages/25_kpm.sh

      - name: 克隆 AnyKernel3 并打包
        id: create_zip
        run: bash scripts/build/stages/26_package.sh

      - name: 上传 Ccache 调试日志
        if: always() && inputs.ccache_debug
        uses: actions/upload-artifact@v7
        with:
          path: ${{{{ github.workspace }}}}/kernel_workspace/debug.zip
          archive: false

      - name: 上传 ZIP 工件
        uses: actions/upload-artifact@v7
        with:
          path: ${{{{ github.workspace }}}}/kernel_workspace/AnyKernel*.zip
          archive: false

  release:
    needs: build
    runs-on: ubuntu-latest
    permissions:
      contents: write
      packages: write
      actions: read

    steps:
      - name: 下载 ZIP 工件
        uses: actions/download-artifact@v8
        with:
          name: ${{{{ needs.build.outputs.ak3name }}}}
          path: ./release_zips
          skip-decompress: true

      - name: 设置环境变量
        run: |
{clean_lines}{full_lines}          TIME="$(TZ='Asia/Shanghai' date +'%y%m%d%H%M%S')"
          TIME_FORM="$(TZ='Asia/Shanghai' date +'%Y-%m-%d %H:%M:%S')"
          echo "TIME=$TIME" >> $GITHUB_ENV
          echo "TIME_FORM=$TIME_FORM" >> $GITHUB_ENV
          TAG_HEAD="OPPO-OPlus-Realme-build"
          echo "TAG_HEAD=$TAG_HEAD" >> $GITHUB_ENV
          if [[ ${{{{ github.event.inputs.ksu_type }}}} == "sukisu" ]]; then
            KSU_TYPENAME="SukiSU Ultra"
          elif [[ ${{{{ github.event.inputs.ksu_type }}}} == "resukisu" ]]; then
            KSU_TYPENAME="ReSukiSU"
          elif [[ ${{{{ github.event.inputs.ksu_type }}}} == "ksunext" ]]; then
            KSU_TYPENAME="KernelSU Next"
          elif [[ ${{{{ github.event.inputs.ksu_type }}}} == "ksu" ]]; then
            KSU_TYPENAME="{p['ksu_official']}"
          else
            KSU_TYPENAME="无内置KSU"
          fi
          echo "KSU_TYPENAME=$KSU_TYPENAME" >> $GITHUB_ENV

      - name: 计算产物哈希
        id: checksum
        run: |
          cd release_zips
          sha256sum AnyKernel3_*.zip > checksums.sha256
          cat checksums.sha256
          echo "sha256=$(sha256sum AnyKernel3_*.zip | awk '{{print $1}}')" >> $GITHUB_OUTPUT

      - name: 创建发布
        id: create_release
        env:
          GITHUB_TOKEN: ${{{{ secrets.GITHUB_TOKEN }}}}
        run: |
          cat << 'EOF' > release_notes.md
          {title_line}
          - 内核版本号: ${{{{ env.FULL_VERSION }}}}
          - 编译时间: ${{{{ env.TIME_FORM }}}}
          - SHA256: ${{{{ steps.checksum.outputs.sha256 }}}}
          {device_line}
          - KSU分支：${{{{ env.KSU_TYPENAME }}}}
          - susfs支持：${{{{ github.event.inputs.susfs_enable }}}}
          - KPM支持 ：${{{{ github.event.inputs.kpm_enable }}}}
          - LZ4支持：${{{{ github.event.inputs.lz4_enable }}}}
          - LZ4KD支持：${{{{ github.event.inputs.lz4kd_enable }}}}
          - 网络功能增强：${{{{ github.event.inputs.better_net }}}}
          - BBR/Brutal 等拥塞控制算法支持：${{{{ github.event.inputs.bbr_enable }}}}
          - Droidspaces 容器支持：${{{{ github.event.inputs.droidspaces_enable }}}}
          - {p['iosched_note']}：${{{{ github.event.inputs.{iosched_in} }}}}
          - Re-Kernel支持：${{{{ github.event.inputs.rekernel_enable }}}}
          - 内核级基带保护支持：${{{{ github.event.inputs.baseband_guard }}}}
          - ReSukiSU管理器下载：[ReSukiSU_CI](https://github.com/SunsetRNE/ReSukiSU_CI/releases)
          - SukiSU Ultra管理器下载：[SukiSU-Ultra](https://github.com/SukiSU-Ultra/SukiSU-Ultra/releases)
          - KernelSU Next管理器下载：[KernelSU-Next](https://github.com/KernelSU-Next/KernelSU-Next/releases)
          - KSU原版管理器下载：[KernelSU](https://github.com/tiann/KernelSU/releases)

          ### ⏫️ 更新内容：
          - 更新${{{{ env.KSU_TYPENAME }}}}至最新版本（${{{{ needs.build.outputs.ksuver }}}}）
          - (预留)

          ### 📋 安装方法 | Installation Guide
          1. 若你的手机已经安装了第三方Recovery（如TWRP)，可下载对应机型的AnyKernel刷机包后进入Recovery模式，通过Recovery刷入刷机包后重启设备；
          2. 若你的手机之前已有 root 权限，可在手机上安装[HorizonKernelFlasher](https://github.com/libxzr/HorizonKernelFlasher/releases)，在HorizonKernelFlasher中刷入AnyKernel刷机包并重启；
          3. 若你之前已刷入SukiSU Ultra内核，且SukiSU Ultra管理器已更新至最新版本，可在SukiSU Ultra管理器中直接刷入AnyKernel刷机包并重启；
          4. 刷入无lz4kd补丁版的内核前若刷入过lz4kd补丁版的内核，为避免出错，请先关闭zram模块；
          5. 由于KernelSU上游更新了元模块功能，最新版KSU管理器（包括除KernelSU Next以外的各分支）需要配合元模块(metamodule)才能正常挂载模块。目前的元模块包括[meta overlayfs](https://github.com/KernelSU-Modules-Repo/meta-overlayfs), [mountify](https://github.com/backslashxx/mountify), [meta magicmount](https://github.com/7a72/meta-magic_mount/), [meta magicmount rs](https://github.com/Tools-cx-app/meta-magic_mount/), [hybrid mount](https://github.com/YuzakiKokuban/meta-hybrid_mount)等。若你是第一次使用KSU或刚从旧版KSU管理器升级至新版，请先安装一个元模块，这样其他涉及系统挂载的模块才能正常运行；
          6. KernelPatch Next（即KPN）是一个独立于KSU的KPM实现，可以运行在任意KSU/面具环境中（不适用于Apatch），且不能与(Re)SukiSU内置的kpm功能共同使用，使用前请保证你的内核没有内置的kpm实现/修补。

          #### ※※※刷写内核有风险，为防止出现意外导致手机变砖，在刷入内核前请务必用[KernelFlasher](https://github.com/capntrips/KernelFlasher)等软件备份boot等关键启动分区!※※※
          EOF

          gh release create "${{{{ env.TAG_HEAD }}}}-${{{{ env.TIME }}}}" \
            --repo "${{{{ github.repository }}}}" \
            --title "${{{{ env.TAG_HEAD }}}}-${{{{ env.FULL_VERSION }}}}" \
            --notes-file release_notes.md \
            release_zips/AnyKernel3_*.zip release_zips/checksums.sha256

      - name: 产物完整性自检
        env:
          GITHUB_TOKEN: ${{{{ secrets.GITHUB_TOKEN }}}}
        run: |
          cd release_zips
          gh release download "${{{{ env.TAG_HEAD }}}}-${{{{ env.TIME }}}}" \
            --repo "${{{{ github.repository }}}}" \
            --pattern 'AnyKernel3_*.zip' \
            --dir verify --clobber
          cd verify
          sha256sum -c ../checksums.sha256
"""
    return yml


def main():
    files = sorted(glob.glob(os.path.join(WF_DIR, "sm*_fastbuild_*.yml")))
    generated = []
    for path in files:
        base = os.path.basename(path)
        platform = base.split("_")[0]
        if platform not in PLATFORMS:
            print(f"⚠️ 未知平台，跳过: {base}")
            continue
        w, env, inputs, text = load_old(path)
        inputs_block = extract_inputs_block(text)
        src_url, src_dirname = extract_src(text, env)
        title_line, device_line = extract_release_lines(text)
        bpf = "CONFIG_BPF_STREAM_PARSER" in text or env.get("BETTERNET_BPF") == "1"
        lz4_clearmake = "001-lz4-clearMake" in text or env.get("LZ4_CLEARMAKE") == "1"
        yml = render(platform, w, env, inputs_block, src_url, src_dirname,
                     title_line, device_line, bpf, lz4_clearmake)
        if DRY:
            print(f"[DRY-RUN] {base} → {len(yml.splitlines())} 行")
            continue
        with open(path, "w", encoding="utf-8") as f:
            f.write(yml)
        generated.append(base)
        print(f"✅ {base}（{len(yml.splitlines())} 行）")
    print(f"\n📊 已生成 {len(generated)} 个工作流" + ("（dry-run）" if DRY else ""))


if __name__ == "__main__":
    main()
