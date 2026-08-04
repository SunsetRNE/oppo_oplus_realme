#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
档案配置预览（只读）——选择工作流后展示其档案完整配置
======================================================
用法（GitHub Actions 中由 profile_preview.yml 调用，或本地直接运行）：
    python3 scripts/dispatcher/preview_profile.py
    WORKFLOW=sm8850_fastbuild_6.12.23.yml python3 scripts/dispatcher/preview_profile.py

env 入参：
    WORKFLOW  目标编译工作流文件名（必须，且必须有档案）

输出：markdown 配置表格（供 GITHUB_STEP_SUMMARY 展示）
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_profile, list_profile_workflows  # noqa: E402


def main():
    workflow_file = os.environ.get("WORKFLOW", "").strip()
    if not workflow_file:
        print("❌ 未指定工作流（WORKFLOW）。请选择要预览的编译工作流。")
        sys.exit(1)
    profile, errs = load_profile(workflow_file)
    if errs:
        for e in errs:
            print(f"❌ {e}")
        sys.exit(1)

    inputs = profile["variants"]["default"]
    lines = [
        "### 📋 档案配置预览", "",
        f"- **工作流**: `{workflow_file}`",
        f"- **平台/版本**: {profile.get('platform')} / {profile.get('version')}",
        f"- **档案状态**: {'✅ 已验证' if profile.get('verified') else '⚠️ 未验证（verified=false，待人工校准）'}",
        f"- **更新日期**: {profile.get('updated_at', '?')}",
        f"- **备注**: {profile.get('note', '')}",
        "", "**编译配置（variants.default，触发时解压注入）：**", "",
        "| 参数 | 值 |", "|---|---|",
    ]
    for k, v in inputs.items():
        lines.append(f"| `{k}` | `{v}` |")
    lines += [
        "", "> 微调配置 = 本地修改 `config/profiles/` 后 push（验证资产，改完需实测）；",
        "> 临时微调 = 直接手动触发对应编译 workflow（不分裂档案）。",
    ]
    print("\n".join(lines))


if __name__ == "__main__":
    main()