#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一编译调度体系 · 生成器（Producer）— 档案驱动版
================================================
职责：根据用户中文表单（env 传入）→ 加载所选工作流的配置档案 → 严苛匹配校验 →
      解压完整 inputs → 后缀三分支特判 → 规则校验 → 写入 queue/pending/
      （只入队，不触发编译）

设计要点（链式触发器）：
  - 表单第一个选项 = 工作流（仅列有档案的；无档案的工作流不显示、不触发、不警告）
  - 选工作流 → 自动加载其档案 variants.default 的完整 inputs（解压在生成器内部完成）
  - queue/ 与触发器拿到的永远是展开后的完整标准 JSON（压缩表达→解压）
  - 档案由人工维护（config/profiles/），失效即删、靠 gen_profiles.py 重新生成

用法（GitHub Actions 中由 compile_dispatcher.yml 调用）：
    python3 scripts/dispatcher/generate_tasks.py [--dry-run]

env 入参（由 workflow inputs 透传）：
    WORKFLOW       目标编译工作流文件名（必须有档案，必填）
    SUFFIX_MODE    empty（用档案默认，通常无后缀）/ auto（生成SunsetRNE_时间戳_随机数）/ custom（手动填）
    SUFFIX_CUSTOM  自定义内核后缀文本（仅 custom 模式，禁止空格）
    DELAY_UNTIL    'YYYY-MM-DD HH:MM'（UTC+8），留空=立即
"""
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (  # noqa: E402
    clean_inputs_for, load_profile, load_workflow_inputs, list_profile_workflows,
    now_compact, now_iso, parse_delay, validate_inputs, write_task_file,
)

DRY = "--dry-run" in sys.argv


def main():
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

    # 2) 解压档案 → 完整 inputs（变体机制预留，当前单档 default）
    inputs = dict(profile["variants"]["default"])
    print(f"🔗 链式触发：{workflow_file} ← 档案 {workflow_file}.json"
          f"（verified={profile.get('verified', False)}）")

    # 3) 后缀三分支特判（kernel_suffix 是唯一带自由文本约束的 input）
    if suffix_mode == "auto":
        inputs["kernel_suffix"] = f"SunsetRNE_{now_compact()}_{random.randint(10000, 99999)}"
    elif suffix_mode == "custom":
        inputs["kernel_suffix"] = suffix_custom
    # empty：不注入 kernel_suffix → 用编译 workflow 内部默认（档案里通常也没有）

    # 4) 与编译 workflow 实际 inputs 做一致性校验（防档案漂移/422）
    wf_inputs = load_workflow_inputs(os.path.join(".github/workflows", workflow_file))
    if not wf_inputs:
        print(f"❌ 无法解析编译 workflow：.github/workflows/{workflow_file}（文件不存在或被改动）")
        sys.exit(1)
    missing = [k for k, m in wf_inputs.items()
               if m.get("required") and k not in inputs]
    if missing:
        print(f"❌ 档案 {workflow_file}.json 缺少编译 workflow 的必填 input：{missing}")
        print("   👉 档案已过期（workflow 新增了必填参数），请删除档案后重新生成校准")
        sys.exit(1)
    extra = [k for k in inputs if k not in wf_inputs]
    if extra:
        print(f"⚠️ 档案含编译 workflow 不存在的参数（将被丢弃）：{extra}")
        print("   👉 提示：workflow 可能已移除这些参数，建议人工校准档案")

    # 5) 规则校验（白名单 + choice + 互斥 + ksu禁用 + 后缀禁空格）
    clean = clean_inputs_for(inputs, wf_inputs)
    errs = validate_inputs(workflow_file, clean, wf_inputs)
    if errs:
        for e in errs:
            print(f"❌ [{workflow_file}] {e}")
        print("\n⚠️ 任务未通过校验，已中止入队（避免坏任务污染队列）")
        sys.exit(1)

    # 6) 组装任务（来源=档案，审计字段透传）
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

    # 8) 汇总
    suf = task["inputs"].get("kernel_suffix", "")
    print(f"\n📊 汇总：工作流 {task['workflow']} 已入队，等待触发器消费")
    print(f"   · inputs {len(task['inputs'])} 个（来自档案解压）")
    print(f"   · suffix={'空(用工作流默认)' if not suf else suf}")
    if not task["profile_verified"]:
        print("   ⚠️ 档案未验证（verified=false）——请以实测结果校准后置 true")
    avail = [w for w in list_profile_workflows() if w != workflow_file]
    if avail:
        print(f"   · 其他可选工作流（{len(avail)} 个）：{', '.join(avail[:5])}{'...' if len(avail) > 5 else ''}")


if __name__ == "__main__":
    main()