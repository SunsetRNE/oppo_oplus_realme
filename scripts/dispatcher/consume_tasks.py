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
    dispatch_workflow, get_run_status, is_due, list_queue_files, move_task_file,
    now_iso, read_task_file, write_task_file, delete_task_file,
)

DRY = "--dry-run" in sys.argv
BATCH = 2
if "--batch" in sys.argv:
    BATCH = int(sys.argv[sys.argv.index("--batch") + 1])


def summary_line():
    """输出当前队列概况。"""
    n_p = len(list_queue_files("pending"))
    n_r = len(list_queue_files("running"))
    n_d = len(list_queue_files("done"))
    n_f = len(list_queue_files("failed"))
    return f"📊 队列：pending={n_p} running={n_r} done={n_d} failed={n_f}"


def reconcile_running():
    """幂等恢复：扫 running/，查 run 状态；completed → done/，失败按重试策略。"""
    moved = []
    for f in list_queue_files("running"):
        task, _ = read_task_file("running", f["name"])
        if not task:
            continue
        run_id = task.get("run_id")
        if not run_id:
            # 已写 running 但 dispatch 未完成（极端情况）→ 补触发
            ok = _dispatch(task)
            if ok:
                moved.append(f"↻ 补触发 {task['workflow']} (run 待查)")
            else:
                moved.append(f"❌ 补触发失败 {task['workflow']}")
            continue
        status, conclusion = get_run_status(run_id)
        if status != "completed":
            moved.append(f"⏳ {task['workflow']} run={run_id} 仍在 {status}")
            continue
        # 完成：写回 done（含结果）
        task["status"] = status
        task["conclusion"] = conclusion
        task["finished_at"] = now_iso()
        if DRY:
            moved.append(f"[DRY] 完成 {task['workflow']} run={run_id} conclusion={conclusion} → done/")
            continue
        if move_task_file("running", f["name"], "done", task):
            moved.append(f"✅ 完成 {task['workflow']} run={run_id} conclusion={conclusion} → done/")
        else:
            moved.append(f"⚠️ 写回失败 {task['workflow']}（下次 cron 重试）")
    return moved


def _dispatch(task):
    """触发编译并记录 run_id；返回是否成功。"""
    ok = dispatch_workflow(task["workflow"], task.get("inputs") or {})
    if ok:
        task["dispatched_at"] = now_iso()
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
        if not write_task_file("running", f["name"], task):
            done.append(f"❌ 移入 running 失败 {task['workflow']}（跳过本轮）")
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


def main():
    print(f"🔄 触发器开始 {now_iso()}  batch={BATCH}{' [DRY-RUN]' if DRY else ''}")
    print(summary_line())
    print("\n-- 恢复 running --")
    for line in reconcile_running():
        print(f"  {line}")
    print("\n-- 消费 pending --")
    for line in consume_pending():
        print(f"  {line}")
    print(f"\n{summary_line()}")
    print("🔄 触发器结束")


if __name__ == "__main__":
    main()