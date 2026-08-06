#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一编译调度体系 · 生成器（Producer）— 表单参数驱动
==================================================
职责：用户表单（env 传入，含全部编译参数预设默认值）→ 档案严苛匹配校验 →
      参数校验 → 平台白名单自动适配 → 写入 queue/pending/（只入队，不触发编译）

设计要点（链式触发器）：
  - 表单第一项 = 工作流（仅列有档案的；无档案 = 无链 = 不显示/不触发/不警告）
  - 表单预设参数 = 编译工作流的默认值（与档案一致）；参数可改，改后自负验证责任
  - 平台差异自动适配：sm8650→ssg_enable、sm8750/sm8850→adios_enable
    （两个参数都在表单，clean 按所选工作流白名单自动过滤）
  - 与档案对比：偏离档案默认值时提示并记录（deviated_from_profile）

用法（GitHub Actions 中由 compile_dispatcher.yml 调用）：
    python3 scripts/dispatcher/generate_tasks.py [--dry-run|--summary]

env 入参（workflow inputs 透传）：
    WORKFLOW / KSU_TYPE / SUSFS_ENABLE / KPM_ENABLE / LZ4_ENABLE / LZ4KD_ENABLE /
    BBR_ENABLE / DROIDSPACES_ENABLE / BETTER_NET / ADIOS_ENABLE / SSG_ENABLE /
    REKERNEL_ENABLE / BASEBAND_GUARD / UNICODE_FIX / CCACHE_UPDATE / CCACHE_DEBUG /
    SUFFIX_MODE / SUFFIX_CUSTOM / DELAY_UNTIL
"""
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (  # noqa: E402
    clean_inputs_for, list_profile_workflows, load_profile, load_workflow_inputs,
    now_compact, now_iso, parse_delay, validate_inputs, write_task_file,
)

DRY = "--dry-run" in sys.argv
SUMMARY = "--summary" in sys.argv

# 表单参数 → env 键映射（布尔类与字符串类分开处理）
BOOL_INPUTS = [
    "SUSFS_ENABLE", "KPM_ENABLE", "LZ4_ENABLE", "LZ4KD_ENABLE",
    "BETTER_NET", "ADIOS_ENABLE", "SSG_ENABLE", "REKERNEL_ENABLE",
    "BASEBAND_GUARD", "UNICODE_FIX", "CCACHE_UPDATE", "CCACHE_DEBUG",
]
STR_INPUTS = ["KSU_TYPE", "BBR_ENABLE", "DROIDSPACES_ENABLE"]


def collect_inputs():
    """从 env 组装 inputs（表单预设参数 → 标准 JSON 值）。"""
    inputs = {}
    for key in STR_INPUTS:
        inputs[key.lower()] = os.environ.get(key, "").strip()
    for key in BOOL_INPUTS:
        inputs[key.lower()] = os.environ.get(key, "").strip().lower() == "true"
    return inputs


def print_summary():
    """输出最近入队任务的完整配置（markdown，供 GITHUB_STEP_SUMMARY 展示）。"""
    from common import list_queue_files, read_task_file
    files = sorted((f["name"] for f in list_queue_files("pending")), reverse=True)
    if not files:
        print("### 🎛️ 生成器执行完成\n\n暂无 pending 任务。")
        return
    name = files[0]
    task, _ = read_task_file("pending", name)
    if not task:
        print("### 🎛️ 生成器执行完成\n\n⚠️ 无法读取最近任务。")
        return
    dev = "✅ 与档案一致" if not task.get("deviated_from_profile") else "⚠️ 已偏离档案默认值（请确认）"
    lines = [
        "### 🎛️ 生成器执行完成", "",
        f"- **任务**: `{name}`",
        f"- **工作流**: `{task.get('workflow')}`",
        f"- **平台/版本**: {task.get('platform')} / {task.get('version')}",
        f"- **档案状态**: {'✅ 已验证' if task.get('profile_verified') else '⚠️ 未验证（verified=false）'}",
        f"- **档案对比**: {dev}",
        f"- **延迟触发**: {task.get('delay_until') or '立即'}",
        "", "**注入配置（完整 inputs）：**", "",
        "| 参数 | 值 |", "|---|---|",
    ]
    for k, v in (task.get("inputs") or {}).items():
        lines.append(f"| `{k}` | `{v}` |")
    lines += ["", "> 任务已写入 `queue/pending/`，由触发器（每5分钟）自动消费。"]
    print("\n".join(lines))


def main():
    if SUMMARY:
        print_summary()
        return

    workflow_file = os.environ.get("WORKFLOW", "").strip()
    suffix_mode = os.environ.get("SUFFIX_MODE", "empty").strip()
    suffix_custom = os.environ.get("SUFFIX_CUSTOM", "").strip()
    delay_raw = os.environ.get("DELAY_UNTIL", "").strip()

    # 0) 延迟触发解析（格式错则直接中文报错）
    try:
        delay_until = parse_delay(delay_raw)
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

    # 1) 工作流必选 + 档案加载（严苛匹配：无档案 = 不触发）
    if not workflow_file:
        print("❌ 未指定工作流（WORKFLOW）。请选择目标编译工作流。")
        sys.exit(1)
    profile, errs = load_profile(workflow_file)
    if errs:
        for e in errs:
            print(f"❌ {e}")
        print("   👉 无档案或档案无效 = 无链 = 不触发。请人工维护 config/profiles/（失效即删）")
        sys.exit(1)
    print(f"🔗 链式触发：{workflow_file} ← 档案 {workflow_file}.json"
          f"（verified={profile.get('verified', False)}）")

    # 2) 表单预设参数 → 标准 inputs
    inputs = collect_inputs()

    # 3) 后缀三分支特判（kernel_suffix 是唯一带自由文本约束的 input）
    if suffix_mode == "auto":
        inputs["kernel_suffix"] = f"SunsetRNE_{now_compact()}_{random.randint(10000, 99999)}"
    elif suffix_mode == "custom":
        inputs["kernel_suffix"] = suffix_custom
    # empty：不注入 kernel_suffix → 用编译 workflow 内部默认

    # 4) 与档案默认值对比（偏离提示，审计留痕）
    profile_inputs = profile.get("variants", {}).get("default", {})
    deviated = False
    for k, v in inputs.items():
        if k == "kernel_suffix":
            continue  # 后缀是每次触发的临时选择，不算偏离
        pv = profile_inputs.get(k)
        if pv is not None and str(pv).lower() != str(v).lower():
            deviated = True
            print(f"⚠️ 参数 [{k}] = {v} ≠ 档案默认 {pv}（已偏离，请确认此改动）")
    if not deviated:
        print("✅ 表单参数与档案默认值一致")

    # 5) 与编译 workflow 实际 inputs 一致性校验 + 规则校验
    wf_inputs = load_workflow_inputs(os.path.join(".github/workflows", workflow_file))
    if not wf_inputs:
        print(f"❌ 无法解析编译 workflow：.github/workflows/{workflow_file}（文件不存在或被改动）")
        sys.exit(1)
    clean = clean_inputs_for(inputs, wf_inputs)  # 白名单：平台差异参数自动过滤
    errs = validate_inputs(workflow_file, clean, wf_inputs)
    if errs:
        for e in errs:
            print(f"❌ [{workflow_file}] {e}")
        print("\n⚠️ 任务未通过校验，已中止入队（避免坏任务污染队列）")
        sys.exit(1)

    # 6) 组装任务（审计字段透传）
    plat = profile.get("platform", "")
    ver = profile.get("version", "")
    task = {
        "task_id": f"{now_compact()}_{plat}_{ver.replace('.', '')}",
        "workflow": workflow_file,
        "platform": plat,
        "version": ver,
        "ref": "main",
        "inputs": clean,
        "delay_until": delay_until,
        "max_retry": 2,
        "retry_count": 0,
        "source": "profile",
        "profile_verified": bool(profile.get("verified", False)),
        "deviated_from_profile": deviated,
        "created_by": "compile_dispatcher",
        "created_at": now_iso(),
    }

    # 7) 入队（或 dry-run 打印）
    name = f"{task['task_id']}.json"
    if DRY:
        print(f"[DRY-RUN] 将入队 queue/pending/{name}")
        print(json.dumps(task, ensure_ascii=False, indent=2))
        return
    ok, status, detail = write_task_file("pending", name, task)
    if ok:
        print(f"✅ 已入队 queue/pending/{name}  ({task['workflow']})")
    else:
        print(f"❌ 入队失败 queue/pending/{name}  HTTP={status}")
        print(f"   响应: {detail}")
        sys.exit(1)

    # 8) 汇总（含完整配置清单）
    suf = task["inputs"].get("kernel_suffix", "")
    print(f"\n📊 汇总：工作流 {task['workflow']} 已入队，等待触发器消费")
    print(f"   · inputs {len(task['inputs'])} 个（表单预设参数 + 自动平台适配）")
    for k, v in task["inputs"].items():
        print(f"     - {k} = {v}")
    print(f"   · suffix={'空(用工作流默认)' if not suf else suf}")
    if deviated:
        print("   ⚠️ 本次参数已偏离档案默认值——黑屏/无限重启风险自负，请确认")
    if not task["profile_verified"]:
        print("   ⚠️ 档案未验证（verified=false）——请以实测结果校准后置 true")
    avail = [w for w in list_profile_workflows() if w != workflow_file]
    if avail:
        print(f"   · 其他可选工作流（{len(avail)} 个）：{', '.join(avail[:5])}{'...' if len(avail) > 5 else ''}")


if __name__ == "__main__":
    main()