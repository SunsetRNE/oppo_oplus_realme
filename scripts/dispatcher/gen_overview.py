#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
档案配置总览生成器：把 config/profiles/ 全部档案渲染成 docs/档案配置总览.md
====================================================================
用法：python3 scripts/dispatcher/gen_overview.py [--dry-run]
档案变更后重跑本脚本，总览文档自动更新（人工维护档案库的一部分）。
"""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import list_profile_workflows, load_profile  # noqa: E402

OUT = "docs/档案配置总览.md"
DRY = "--dry-run" in sys.argv


def main():
    workflows = list_profile_workflows()
    if not workflows:
        print("❌ config/profiles/ 下没有档案。请先建档（gen_profiles.py）。")
        sys.exit(1)

    # 按平台分组（sm8850 / sm8750 / sm8650）
    groups = {}
    for wf in workflows:
        profile, _ = load_profile(wf)
        if not profile:
            continue
        groups.setdefault(profile.get("platform", "?"), []).append((wf, profile))

    lines = [
        "# 📋 档案配置总览",
        "",
        f"> 由 `scripts/dispatcher/gen_overview.py` 自动生成 · 更新于 {datetime.date.today().isoformat()}",
        f"> 共 {len(workflows)} 个档案（人工维护的验证资产；无档案的工作流不显示、不触发、不警告）",
        "",
        "## 说明",
        "",
        "- **verified**：`✅` = 已实测能开机（校准完成）；`⚠️` = 默认值建档，待人工校准",
        "- **微调配置**：本地修改 `config/profiles/` 后 push（改完需实测）；临时微调直接手动触发编译 workflow",
        "",
    ]
    for plat in sorted(groups.keys(), reverse=True):
        lines.append(f"## {plat}（{len(groups[plat])} 个工作流）")
        lines.append("")
        lines.append("| 工作流 | 版本 | verified | ksu | susfs | kpm | lz4 | lz4kd | bbr | droidspaces | better_net | 平台特性 | rekernel | baseband_guard | ccache_upd | ccache_dbg |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for wf, profile in sorted(groups[plat]):
            v = profile["variants"]["default"]
            vmark = "✅" if profile.get("verified") else "⚠️"
            feat = v.get("adios_enable", v.get("ssg_enable", "?"))  # 平台差异参数
            lines.append(
                f"| `{wf}` | {profile.get('version')} | {vmark} | {v.get('ksu_type', '?')} "
                f"| {v.get('susfs_enable', '?')} | {v.get('kpm_enable', '?')} "
                f"| {v.get('lz4_enable', '?')} | {v.get('lz4kd_enable', '?')} "
                f"| {v.get('bbr_enable', '?')} | {v.get('droidspaces_enable', '?')} "
                f"| {v.get('better_net', '?')} | {feat} "
                f"| {v.get('rekernel_enable', '?')} | {v.get('baseband_guard', '?')} "
                f"| {v.get('ccache_update', '?')} | {v.get('ccache_debug', '?')} |"
            )
        lines.append("")

    content = "\n".join(lines)
    if DRY:
        print(f"[DRY-RUN] 将生成 {OUT}（{len(workflows)} 个档案，{len(groups)} 个平台）")
        print(content[:800])
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ 已生成 {OUT}（{len(workflows)} 个档案）")


if __name__ == "__main__":
    main()