#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一编译调度体系 · 公共库
=========================
职责：GitHub API 封装 / 编译 workflow 动态解析 / 业务规则表（校验）/ 队列文件读写
设计原则：
  - 中文只出现在"生成器"这一层；queue 内任务一律为标准 JSON（英文 key）
  - 触发器只消费标准 JSON，不接触中文解析
  - 所有写操作走 GitHub Contents API（不依赖本地 git，竞态面最小）
"""
import base64
import datetime
import json
import os
import re
import urllib.error
import urllib.request

# ---------------- 基础信息 ----------------
REPO = os.environ.get("GITHUB_REPOSITORY", "SunsetRNE/oppo_oplus_realme")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
BRANCH = os.environ.get("GITHUB_REF_NAME", "main")
WORKFLOW_DIR = os.environ.get("WORKFLOW_DIR", ".github/workflows")
QUEUE_DIR = os.environ.get("QUEUE_DIR", "queue")
TZ_CN = datetime.timezone(datetime.timedelta(hours=8))  # UTC+8


def api(method, path, data=None, timeout=30):
    """GitHub REST API 调用。返回 (status, json或文本)。"""
    if not TOKEN:
        return 0, "NO_TOKEN"
    url = f"https://api.github.com/repos/{REPO}{path}"
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "operit-dispatcher")
    body = json.dumps(data).encode("utf-8") if data is not None else None
    try:
        with urllib.request.urlopen(req, body, timeout=timeout) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:400]


# ---------------- 时间工具 ----------------
def now_iso():
    return datetime.datetime.now(TZ_CN).isoformat(timespec="seconds")


def now_compact():
    return datetime.datetime.now(TZ_CN).strftime("%Y%m%d%H%M%S")


def parse_delay(text):
    """解析用户延迟触发文本 'YYYY-MM-DD HH:MM'（UTC+8），返回 ISO8601 或 None。"""
    if not text or not text.strip():
        return None
    try:
        dt = datetime.datetime.strptime(text.strip(), "%Y-%m-%d %H:%M").replace(tzinfo=TZ_CN)
        return dt.isoformat(timespec="seconds")
    except ValueError:
        raise ValueError(f"延迟触发时间格式错误: {text}（应为 YYYY-MM-DD HH:MM，UTC+8）")


def is_due(iso_text):
    """任务是否到期（delay_until 为空或已到）。"""
    if not iso_text:
        return True
    return datetime.datetime.fromisoformat(iso_text) <= datetime.datetime.now(TZ_CN)


# ---------------- 编译 workflow 动态解析 ----------------
def load_workflow_inputs(wf_path):
    """
    解析编译 workflow 的 on.workflow_dispatch.inputs 定义。
    注意：PyYAML 会把 'on' 解析为布尔 True，需兼容两种。
    返回 {input_key: {type, default, options, required, description}}
    """
    import yaml
    with open(wf_path, encoding="utf-8") as f:
        w = yaml.safe_load(f)
    trigger = (w or {}).get(True) or (w or {}).get("on") or {}
    dispatch = trigger.get("workflow_dispatch", {}) if isinstance(trigger, dict) else {}
    inputs = dispatch.get("inputs", {}) if isinstance(dispatch, dict) else {}
    return inputs or {}


def list_build_workflows():
    """扫描 sm*_fastbuild_*.yml，返回 [(文件名, 平台, 版本)] 按文件名排序。"""
    import glob
    out = []
    for f in sorted(glob.glob(os.path.join(WORKFLOW_DIR, "sm*_fastbuild_*.yml"))):
        base = os.path.basename(f)
        m = re.match(r"(sm\d+)_fastbuild_(.+)\.yml$", base)
        if m:
            out.append((base, m.group(1), m.group(2)))
    return out


# ---------------- 业务规则表（稳定业务知识，硬编码） ----------------
RULES = {
    # kernel_suffix：唯一带自由文本约束的 input，必须特判（动态解析拿不到语义约束）
    "kernel_suffix": {
        "pattern": re.compile(r"^[A-Za-z0-9_]+$"),   # 字母数字下划线；禁空格/禁连字符开头/禁特殊字符
        "max_len": 64,                                # 防产物文件名超长（AK3_NAME 拼接）
        "empty_ok": True,                             # 留空 = 用默认 KERNEL_NAME，合法
        "hint": "禁止空格！建议格式: SunsetRNE_时间戳_随机数",
    },
    # lz4 与 lz4kd 互斥（两者都改 fs/f2fs/compress.c，同开会补丁冲突）
    "lz4_mutex": ("lz4_enable", "lz4kd_enable"),
    # 原版 KernelSU 因上游漂移暂不可用（ADR-010）
    "ksu_banned": ("ksu",),
}


def validate_inputs(workflow_file, inputs, wf_inputs):
    """
    校验注入参数。返回错误列表（空 = 通过）。
    校验点：input 存在性（防422）/ choice 合法性 / 互斥 / ksu禁用 / 后缀规则。
    """
    errs = []
    # 1) input 存在性（动态白名单，根除 422）
    for k in inputs:
        if k not in wf_inputs:
            errs.append(f"参数 [{k}] 不在 {workflow_file} 的 inputs 中（已忽略，避免 422）")
    # 2) choice 值合法性
    for k, v in inputs.items():
        opts = wf_inputs.get(k, {}).get("options")
        if opts and str(v) not in opts:
            errs.append(f"参数 [{k}]={v} 不在合法选项 {opts} 中")
    # 3) lz4 / lz4kd 互斥
    a, b = RULES["lz4_mutex"]
    if inputs.get(a) and inputs.get(b):
        errs.append("lz4 与 lz4kd 互斥（都修改 fs/f2fs/compress.c），不能同时开启")
    # 4) ksu 原版禁用（ADR-010）
    if str(inputs.get("ksu_type", "")) in RULES["ksu_banned"]:
        errs.append("原版 KernelSU(ksu) 因上游漂移暂不可用（ADR-010），请用 resukisu/sukisu/ksunext/none")
    # 5) kernel_suffix 规则引擎
    ks = str(inputs.get("kernel_suffix", "") or "")
    rule = RULES["kernel_suffix"]
    if ks:
        if not rule["pattern"].match(ks):
            errs.append(f"内核后缀 [{ks}] 不合法：只能含字母/数字/下划线，禁止空格、连字符开头、特殊字符（{rule['hint']}）")
        if len(ks) > rule["max_len"]:
            errs.append(f"内核后缀过长（>{rule['max_len']} 字符），会撑爆产物文件名")
    return errs


def clean_inputs_for(inputs, wf_inputs):
    """只保留目标 workflow 白名单内的参数（防 422）。"""
    return {k: v for k, v in inputs.items() if k in wf_inputs}


# ---------------- 队列文件读写（GitHub Contents API） ----------------
def _b64(s):
    return base64.b64encode(s.encode("utf-8")).decode("ascii")


def list_queue_files(subdir):
    """列出 queue/<subdir>/ 下的文件名（不含 .gitkeep）。"""
    status, data = api("GET", f"/contents/{QUEUE_DIR}/{subdir}")
    if status != 200 or not isinstance(data, list):
        return []
    return [f for f in data if f["name"].endswith(".json")]


def read_task_file(subdir, name):
    """读取任务 JSON 文件内容 + sha。"""
    status, data = api("GET", f"/contents/{QUEUE_DIR}/{subdir}/{name}")
    if status != 200 or not data:
        return None, None
    content = base64.b64decode(data["content"]).decode("utf-8")
    return json.loads(content), data["sha"]


def write_task_file(subdir, name, task):
    """创建任务文件（入队/写回）。返回是否成功。"""
    status, _ = api("PUT", f"/contents/{QUEUE_DIR}/{subdir}/{name}", {
        "message": f"queue: {subdir}/{name}",
        "content": _b64(json.dumps(task, ensure_ascii=False, indent=2)),
        "branch": BRANCH,
    })
    return status == 201


def move_task_file(src_subdir, name, dst_subdir, task):
    """移动任务文件 = 创建目标 + 删除源（非原子，幂等处理）。"""
    if not write_task_file(dst_subdir, name, task):
        return False
    return delete_task_file(src_subdir, name)


def delete_task_file(subdir, name):
    """删除任务文件（需 sha）。"""
    _, sha = read_task_file(subdir, name)
    if not sha:
        return False
    status, _ = api("DELETE", f"/contents/{QUEUE_DIR}/{subdir}/{name}", {
        "message": f"queue: 删除 {subdir}/{name}",
        "sha": sha,
        "branch": BRANCH,
    })
    return status == 200


def dispatch_workflow(wf_file, inputs=None):
    """触发编译 workflow（GITHUB_TOKEN, 需 actions: write）。"""
    status, _ = api("POST", f"/actions/workflows/{wf_file}/dispatches", {
        "ref": BRANCH,
        "inputs": inputs or {},
    })
    return status == 204


def get_run_status(run_id):
    """查询 run 状态，返回 (status, conclusion)。"""
    status, data = api("GET", f"/actions/runs/{run_id}")
    if status != 200 or not data:
        return None, None
    return data.get("status"), data.get("conclusion")
