#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
档案注册表同步器：把 config/profiles/ 的档案列表同步进生成器表单
================================================================
问题：GitHub workflow_dispatch 的 choice options 必须静态写在 YAML 里
      （无法运行时动态生成）——"有档案才显示"需要选项列表与档案库保持一致。

本脚本扫描 config/profiles/*.json，重写 compile_dispatcher.yml 中
workflow 选项块（BEGIN_PROFILE_OPTIONS / END_PROFILE_OPTIONS 标记之间）。

用法（档案增删后运行，自动同步表单选项）：
    python3 scripts/dispatcher/sync_profile_options.py [--dry-run]

gen_profiles.py 生成/删除档案后也会自动调用本脚本。
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import list_profile_workflows  # noqa: E402

DISPATCHER_YML = ".github/workflows/compile_dispatcher.yml"
BEGIN = "# BEGIN_PROFILE_OPTIONS"
END = "# END_PROFILE_OPTIONS"
DRY = "--dry-run" in sys.argv


def main():
    workflows = list_profile_workflows()
    if not workflows:
        print("❌ config/profiles/ 下没有档案。请先建档（gen_profiles.py）再同步。")
        sys.exit(1)

    with open(DISPATCHER_YML, encoding="utf-8") as f:
        content = f.read()

    # 定位选项块（匹配整行含行首缩进，避免替换时残留旧缩进）
    m = re.search(
        r"^[ \t]*" + re.escape(BEGIN) + r".*?^[ \t]*" + re.escape(END),
        content, re.S | re.M,
    )
    if not m:
        print(f"❌ {DISPATCHER_YML} 中找不到选项块标记（{BEGIN} / {END}）")
        sys.exit(1)

    # 生成新选项块（缩进对齐 options: 下的注释与选项项；BEGIN/END 已含 # 前缀）
    indent = "          "  # 10 空格
    lines = [f"{indent}{BEGIN}"]
    for w in workflows:
        lines.append(f"{indent}- '{w}'")
    lines.append(f"{indent}{END}")
    new_block = "\n".join(lines)

    if DRY:
        print(f"[DRY-RUN] 将同步 {len(workflows)} 个工作流选项到 {DISPATCHER_YML}")
        print(new_block)
        return

    content = content[: m.start()] + new_block + content[m.end():]
    with open(DISPATCHER_YML, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ 已同步 {len(workflows)} 个工作流选项 → {DISPATCHER_YML}")
    print("   有档案的工作流才出现在生成器表单；无档案不显示、不触发、不警告")


if __name__ == "__main__":
    main()