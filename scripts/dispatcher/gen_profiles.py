#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
档案生成器：从编译 workflow YAML 的 inputs 默认值生成配置档案
==============================================================
用法（本地维护档案库时运行）：
    python3 scripts/dispatcher/gen_profiles.py [--dry-run]

规则：
  - 档案文件名 = workflow 文件名 + .json（严苛匹配键）
  - inputs 取各 workflow 的 YAML 默认值（verified=false，人工校准后置 true）
  - variants 结构预留（当前仅 default 单档）
"""
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import list_build_workflows, load_workflow_inputs  # noqa: E402

PROFILES_DIR = "config/profiles"
DRY = "--dry-run" in sys.argv


def extract_defaults(wf_inputs):
    """从 workflow inputs 定义提取默认值（choice/boolean/string/number 类型）。"""
    out = {}
    for key, meta in wf_inputs.items():
        default = meta.get("default")
        itype = meta.get("type", "string")
        if default is None or default == "":
            # 无默认值：choice 取第一个选项；其余跳过（不注入，用 workflow 内部默认）
            if itype == "choice" and meta.get("options"):
                out[key] = meta["options"][0]
            continue
        if itype == "boolean":
            out[key] = str(default).lower() == "true"
        else:
            out[key] = default
    return out


def main():
    today = datetime.date.today().isoformat()
    os.makedirs(PROFILES_DIR, exist_ok=True)
    generated, skipped = [], []
    for base, plat, ver in list_build_workflows():
        wf_path = os.path.join(".github/workflows", base)
        wf_inputs = load_workflow_inputs(wf_path)
        defaults = extract_defaults(wf_inputs)
        profile = {
            "workflow": base,          # 严苛匹配键：必须与文件名一致
            "platform": plat,
            "version": ver,
            "verified": False,         # 默认值建档，人工校准后置 True
            "note": "默认值建档（待人工校准）",
            "updated_at": today,
            "variants": {
                "default": defaults,   # 变体机制预留，当前单档
            },
        }
        path = os.path.join(PROFILES_DIR, base + ".json")
        if DRY:
            print(f"[DRY-RUN] 将生成 {path}  inputs={len(defaults)} 个")
            generated.append(base)
            continue
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)
        print(f"✅ {path}  inputs={len(defaults)} 个")
        generated.append(base)
    print(f"\n📊 档案生成：{len(generated)} 个（{len(skipped)} 个跳过）")
    print("   ⚠️ 全部 verified=false，请人工按实测校准后置 true")


if __name__ == "__main__":
    main()