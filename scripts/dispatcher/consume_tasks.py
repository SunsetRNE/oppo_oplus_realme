#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一编译调度体系 · 触发器（Consumer）
====================================
职责：cron 定期执行 → 幂等恢复 running → 按到期时间消费 pending（每轮 N 个）→
      workflow_dispatch 注入参数触发编译 → 轮询结果写回 done/ 或按重试策略回 failed/

用法（GitHub Actions 中由 compile_trigger.yml 调用）：
    python3 scripts/dispatcher/consume_tasks.py [--batch N] [--dry-run]

设计要点：
  - 每轮只消费 N 个任务（默认2）→ 并发天然受限，不碰 runner 上限
  - running/ 幂等恢复：触发器崩溃后下次 cron 重扫 running 查 run 状态继续
  - delay_until 未到期的任务跳过（延迟触发）
  - 所有写操作走 Contents API；GITHUB_TOKEN 需 contents: write + actions: write
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (  # noqa: E402
    dispatch_workflow, find_release_tag, get_run_info, is_due, list_queue_files,
    move_task_file, now_iso, read_task_file, write_task_file, delete_task_file,
)

DRY = "--dry-run" in sys.argv
BOARD = "--board" in sys.argv
BATCH = 2
if "--batch" in sys.argv:
    BATCH = int(sys.argv[sys.argv.index("--batch") + 1])

# 失败结论集：这些结论视为"编译失败"，走重试/归档策略（success 之外均视为失败）
FAIL_CONCLUSIONS = {"failure", "cancelled", "timed_out", "action_required", "stale"}
DONE_MAX_AGE_DAYS = 30
DONE_CLEAN_LIMIT = 10


def summary_line():
    """输出当前队列概况。"""
    n_p = len(list_queue_files("pending"))
    n_r = len(list_queue_files("running"))
    n_d = len(list_queue_files("done"))
    n_f = len(list_queue_files("failed"))
    return f"📊 队列：pending={n_p} running={n_r} done={n_d} failed={n_f}"


def _find_run_by_time(task):
    """兜底：按 dispatched_at 查该 workflow 最新 run（dispatch 后未拿到 run_id 时用）。"""
    import urllib.parse
    from common import api, REPO, TOKEN
    anchor = task.get("dispatched_at") or task.get("created_at")
    if not anchor:
        return None
    wf = urllib.parse.quote(task["workflow"])
    status, data = api("GET", f"/actions/workflows/{wf}/runs?per_page=10")
    if status != 200 or not isinstance(data, dict):
        return None
    for r in data.get("workflow_runs", []):
        if r.get("created_at", "") >= anchor:
            return r["id"]
    return None


def reconcile_running():
    """幂等恢复：扫 running/，查 run 状态；success → done/（回填 Release tag），
    失败按 max_retry 策略重投 pending 或归档 failed/。"""
    moved = []
    for f in list_queue_files("running"):
        task, _ = read_task_file("running", f["name"])
        if not task:
            continue
        run_id = task.get("run_id")
        if not run_id:
            # 优先按触发时间兜底找回 run_id；找不到才补触发（防重复编译）
            run_id = _find_run_by_time(task)
            if run_id:
                task["run_id"] = run_id
                write_task_file("running", f["name"], task)
                moved.append(f"🔍 按时间找回 run_id={run_id}（{task['workflow']}）")
            else:
                ok = _dispatch(task)
                if ok:
                    moved.append(f"↻ 补触发 {task['workflow']} (run 待查)")
                else:
                    moved.append(f"❌ 补触发失败 {task['workflow']}")
                continue
        status, conclusion, head_sha = get_run_info(run_id)
        if status != "completed":
            moved.append(f"⏳ {task['workflow']} run={run_id} 仍在 {status}")
            continue
        # ---- 已完成：按结论分流 ----
        if conclusion == "success":
            task["status"] = status
            task["conclusion"] = conclusion
            task["finished_at"] = now_iso()
            # 尽力而为：回填正式发布 Release tag（匹配 head_sha）
            tag = find_release_tag(head_sha) if head_sha else None
            if tag:
                task["release_tag"] = tag
            if DRY:
                moved.append(f"[DRY] 完成 {task['workflow']} run={run_id} conclusion={conclusion} → done/")
                continue
            if move_task_file("running", f["name"], "done", task):
                moved.append(f"✅ 完成 {task['workflow']} run={run_id} conclusion={conclusion}"
                             + (f" tag={tag}" if tag else "") + " → done/")
            else:
                moved.append(f"⚠️ 写回失败 {task['workflow']}（下次 cron 重试）")
            continue
        # ---- 失败：重试策略 ----
        task["retry_count"] = task.get("retry_count", 0) + 1
        max_retry = task.get("max_retry", 2)
        if task["retry_count"] < max_retry:
            # 回 pending 重投：清 run_id/dispatched_at（重新 dispatch 拿新 run）
            task.pop("run_id", None)
            task.pop("dispatched_at", None)
            task["last_failure"] = conclusion or "unknown"
            task["last_failure_at"] = now_iso()
            if DRY:
                moved.append(f"[DRY] 失败重投 {task['workflow']} conclusion={conclusion}"
                             f"（{task['retry_count']}/{max_retry}）→ pending/")
                continue
            if move_task_file("running", f["name"], "pending", task):
                moved.append(f"↻ 失败重投 {task['workflow']} conclusion={conclusion}"
                             f"（{task['retry_count']}/{max_retry}）→ pending/")
            else:
                moved.append(f"⚠️ 重投写回失败 {task['workflow']}（下次 cron 重试）")
        else:
            # 重试耗尽：归档 failed/
            task["status"] = status
            task["conclusion"] = conclusion
            task["finished_at"] = now_iso()
            if DRY:
                moved.append(f"[DRY] 重试耗尽 {task['workflow']} conclusion={conclusion} → failed/")
                continue
            if move_task_file("running", f["name"], "failed", task):
                moved.append(f"❌ 重试耗尽 → failed/ {task['workflow']} conclusion={conclusion}"
                             f"（{task['retry_count']}/{max_retry}）")
            else:
                moved.append(f"⚠️ 归档失败 {task['workflow']}（下次 cron 重试）")
    return moved


def _dispatch(task):
    """触发编译并回填 run_id/dispatched_at；返回是否成功。"""
    dispatched_at = now_iso()
    run_id, ok = dispatch_workflow(task["workflow"], task.get("inputs") or {}, dispatched_at=dispatched_at)
    if ok:
        task["dispatched_at"] = dispatched_at
        if run_id:
            task["run_id"] = run_id
    return ok


def consume_pending():
    """消费到期任务：最多 BATCH 个 → 移 running + dispatch + 删 pending。"""
    done = []
    consumed = 0
    for f in list_queue_files("pending"):
        if consumed >= BATCH:
            break
        task, _ = read_task_file("pending", f["name"])
        if not task:
            continue
        if not is_due(task.get("delay_until")):
            done.append(f"⏸ 未到期 {task['workflow']}（delay_until={task.get('delay_until')}）")
            continue
        if DRY:
            print(f"[DRY-RUN] 将消费 {task['workflow']} inputs={json.dumps(task.get('inputs', {}), ensure_ascii=False)}")
            consumed += 1
            continue
        # 先写 running（占位，防重复消费）→ dispatch → 删 pending
        ok, st, dt = write_task_file("running", f["name"], task)
        if not ok:
            done.append(f"❌ 移入 running 失败 {task['workflow']} HTTP={st} {dt}（跳过本轮）")
            continue
        if not _dispatch(task):
            # dispatch 失败：回滚到 pending（补写回），下次再试
            write_task_file("pending", f["name"], task)
            delete_task_file("running", f["name"])
            done.append(f"❌ dispatch 失败 {task['workflow']}（已回滚 pending）")
            continue
        # 更新 running 里的 run_id（重新 PUT 同路径）
        write_task_file("running", f["name"], task)
        delete_task_file("pending", f["name"])
        done.append(f"🚀 已触发 {task['workflow']}（本轮第 {consumed + 1} 个）")
        consumed += 1
    return done


def cleanup_done(max_age_days=DONE_MAX_AGE_DAYS, limit=DONE_CLEAN_LIMIT):
    """定期清理超龄 done 任务（防仓库膨胀）。每轮限量 limit 个。"""
    import datetime
    from common import TZ_CN
    removed = []
    cutoff = datetime.datetime.now(TZ_CN) - datetime.timedelta(days=max_age_days)
    for f in list_queue_files("done"):
        if len(removed) >= limit:
            break
        task, _ = read_task_file("done", f["name"])
        if not task:
            continue
        ts = task.get("finished_at") or task.get("created_at")
        if not ts:
            continue
        try:
            t = datetime.datetime.fromisoformat(ts)
        except ValueError:
            continue
        if t < cutoff:
            if delete_task_file("done", f["name"]):
                removed.append(f["name"])
    return removed


def board():
    """输出队列看板（markdown，供 GITHUB_STEP_SUMMARY）。"""
    lines = ["### 📊 编译队列看板", ""]
    for sub in ("pending", "running", "done", "failed"):
        n = len(list_queue_files(sub))
        lines.append(f"- **{sub}**: {n}")
    # 最近完成记录
    done_files = sorted((f["name"] for f in list_queue_files("done")), reverse=True)[:5]
    if done_files:
        lines.append("")
        lines.append("**最近完成：**")
        for name in done_files:
            task, _ = read_task_file("done", name)
            if not task:
                continue
            tag = task.get("release_tag", "")
            lines.append(f"- `{task.get('workflow', '?')}` conclusion=`{task.get('conclusion', '?')}`"
                         + (f" tag=`{tag}`" if tag else ""))
    # 最近失败记录
    failed_files = sorted((f["name"] for f in list_queue_files("failed")), reverse=True)[:5]
    if failed_files:
        lines.append("")
        lines.append("**最近失败：**")
        for name in failed_files:
            task, _ = read_task_file("failed", name)
            if not task:
                continue
            lines.append(f"- `{task.get('workflow', '?')}` conclusion=`{task.get('conclusion', '?')}`"
                         f" retry={task.get('retry_count', '?')}/{task.get('max_retry', '?')}")
    print("\n".join(lines))


def main():
    if BOARD:
        board()
        return
    print(f"🔄 触发器开始 {now_iso()}  batch={BATCH}{' [DRY-RUN]' if DRY else ''}")
    print(summary_line())
    print("\n-- 恢复 running --")
    for line in reconcile_running():
        print(f"  {line}")
    print("\n-- 消费 pending --")
    for line in consume_pending():
        print(f"  {line}")
    print("\n-- 清理超龄 done --")
    cleaned = cleanup_done()
    print(f"  清理 {len(cleaned)} 个（超过 {DONE_MAX_AGE_DAYS} 天）" if cleaned else "  无需清理")
    print(f"\n{summary_line()}")
    print("🔄 触发器结束")


if __name__ == "__main__":
    main()