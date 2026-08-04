#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一编译调度体系 · 生成器（Producer）
====================================
职责：根据用户中文表单（env 传入）→ 动态解析编译 workflow → 规则校验 →
      组装标准任务 JSON → 写入 queue/pending/（只入队，不触发编译）

用法（GitHub Actions 中由 compile_dispatcher.yml 调用）：
    python3 scripts/dispatcher/generate_tasks.py [--dry-run]

env 入参（由 workflow inputs 透传）：
    PLATFORM      all / sm8850 / sm8750 / sm8650
    VERSIONS      逗号分隔版本过滤（如 6.12.23,6.12.58），留空=全部
    PARAM_MODE    default（编译workflow默认参数）/ custom（覆盖常用参数）
    KSU_TYPE      resukisu / sukisu / ksunext / none（仅 custom 模式）
    SUSFS_ENABLE  true / false（仅 custom 模式）
    SUFFIX_MODE   empty（留空默认）/ auto（自动生成）/ custom（手动填）
    SUFFIX_CUSTOM 自定义后缀文本（仅 custom 模式，禁止空格）
    DELAY_UNTIL   'YYYY-MM-DD HH:MM'（UTC+8），留空=立即
"""
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (  # noqa: E402
    clean_inputs_for, list_build_workflows, load_workflow_inputs,
    now_compact, now_iso, parse_delay, validate_inputs, write_task_file,
)

DRY = "--dry-run" in sys.argv


def main():
    platform = os.environ.get("PLATFORM", "all").strip()
    versions_raw = os.environ.get("VERSIONS", "").strip()
    param_mode = os.environ.get("PARAM_MODE", "default").strip()
    ksu_type = os.environ.get("KSU_TYPE", "resukisu").strip()
    susfs = os.environ.get("SUSFS_ENABLE", "true").strip()
    suffix_mode = os.environ.get("SUFFIX_MODE", "empty").strip()
    suffix_custom = os.environ.get("SUFFIX_CUSTOM", "").strip()
    delay_raw = os.environ.get("DELAY_UNTIL", "").strip()

    # 0) 延迟触发解析（格式错则直接中文报错）
    try:
        delay_until = parse_delay(delay_raw)
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

    # 1) 动态列出目标编译 workflow（按平台/版本过滤）
    versions = [v.strip() for v in versions_raw.split(",") if v.strip()]
    targets = []
    for base, plat, ver in list_build_workflows():
        if platform != "all" and plat != platform:
            continue
        if versions and ver not in versions:
            continue
        targets.append((base, plat, ver))
    if not targets:
        print(f"❌ 没有匹配的编译 workflow（platform={platform}, versions={versions or '全部'}）")
        print("   可用版本示例：", [v for _, _, v in list_build_workflows()])
        sys.exit(1)

    # 2) 组装注入参数
    inputs = {}
    if param_mode == "custom":
        inputs["ksu_type"] = ksu_type
        inputs["susfs_enable"] = susfs == "true"
        if suffix_mode == "auto":
            inputs["kernel_suffix"] = f"SunsetRNE_{now_compact()}_{random.randint(10000, 99999)}"
        elif suffix_mode == "custom":
            inputs["kernel_suffix"] = suffix_custom

    # 3) 逐任务：白名单清洗 + 规则校验（任一失败 → 整体中止，坏任务不进队）
    created, errors = [], []
    for base, plat, ver in targets:
        wf_inputs = load_workflow_inputs(os.path.join(".github/workflows", base))
        clean = clean_inputs_for(inputs, wf_inputs)
        errs = validate_inputs(base, clean, wf_inputs)
        if errs:
            errors.append((base, errs))
            continue
        task = {
            "task_id": f"{now_compact()}_{plat}_{ver.replace('.', '')}",
            "workflow": base,
            "platform": plat,
            "version": ver,
            "ref": "main",
            "inputs": clean,
            "delay_until": delay_until,
            "max_retry": 2,
            "retry_count": 0,
            "created_by": "compile_dispatcher",
            "created_at": now_iso(),
        }
        created.append(task)

    if errors:
        for base, errs in errors:
            for e in errs:
                print(f"❌ [{base}] {e}")
        print(f"\n⚠️ 共 {len(errors)} 个任务未通过校验，已中止入队（避免坏任务污染队列）")
        sys.exit(1)

    # 4) 入队（或 dry-run 打印）
    for t in created:
        name = f"{t['task_id']}.json"
        if DRY:
            print(f"[DRY-RUN] 将入队 queue/pending/{name}")
            print(json.dumps(t, ensure_ascii=False, indent=2))
            continue
        ok, status, detail = write_task_file("pending", name, t)
        if ok:
            print(f"✅ 已入队 queue/pending/{name}  ({t['workflow']})")
        else:
            print(f"❌ 入队失败 queue/pending/{name}  HTTP={status}")
            print(f"   响应: {detail}")
            sys.exit(1)

    # 5) 汇总
    print(f"\n📊 汇总：目标 {len(targets)} 个，入队 {len(created)} 个"
          f"{'（dry-run，未实际写入）' if DRY else '，等待触发器消费'}")
    if created:
        print("   任务清单：")
        for t in created:
            suf = t["inputs"].get("kernel_suffix", "")
            print(f"   · {t['workflow']:<40s} suffix={'空(默认)' if not suf else suf}")


if __name__ == "__main__":
    main()