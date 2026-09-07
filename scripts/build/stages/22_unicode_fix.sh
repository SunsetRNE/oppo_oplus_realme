#!/bin/bash
# ============================================================
# 22 · 应用零宽字符漏洞修复补丁（仅 unicode_fix=true 时调用）
# ============================================================
source "$(dirname "$0")/../lib.sh"

echo "正在应用零宽字符漏洞修复补丁(fs/unicode ignorable特判移除, 防反作弊扫盘/黑名单文件名绕过)…"
cd "$COMMON"
apply_self_patch "$PLATFORM_DIR/other_patch/unicode-bypass_fix_5.10-6.12.patch" "-p1" "-N -F 3" && echo "✅ 零宽字符漏洞修复补丁应用成功" || echo "补丁未命中(内核可能已包含该修复)，自动跳过"
