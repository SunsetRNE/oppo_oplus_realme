#!/usr/bin/env python3
"""批量给 21 个 fastbuild workflow 的 ksu 分支注入绝对 include 路径修复（O=out 分离构建 KSU_KERNEL_DIR 缺陷）。
幂等：已含 KSU_ABS_DIR 的文件跳过。"""
import glob
import os

WORKFLOWS = sorted(glob.glob('.github/workflows/sm*_fastbuild_*.yml'))
ANCHOR = 'curl -LSs "https://raw.githubusercontent.com/tiann/KernelSU/refs/heads/main/kernel/setup.sh" | bash -s main'
CD_LINE = '            cd ./KernelSU'
PATCH = [
    '            # 修复 O=out 分离构建下 KSU_KERNEL_DIR 相对路径解析错误（$(src) 为 ../drivers/kernelsu 时拼接出错，-I 指向不存在目录导致 klog.h 找不到）',
    '            # 改为注入绝对 include 路径，稳定命中 KernelSU/kernel/include',
    '            KSU_ABS_DIR="$(pwd)/kernel"',
    '            sed -i "s|ccflags-y += -I\\$(KSU_KERNEL_DIR) -I\\$(KSU_KERNEL_DIR)/include|ccflags-y += -I${KSU_ABS_DIR} -I${KSU_ABS_DIR}/include|" kernel/Kbuild || true',
    '            grep -n "ccflags-y += -I" kernel/Kbuild | head -5',
]

changed = []
skipped = []
for path in WORKFLOWS:
    with open(path, encoding='utf-8') as f:
        lines = f.readlines()
    text = ''.join(lines)
    if 'KSU_ABS_DIR' in text:
        skipped.append(os.path.basename(path))
        continue
    # 定位锚点行索引
    anchor_idx = None
    for i, line in enumerate(lines):
        if ANCHOR in line:
            anchor_idx = i
            break
    if anchor_idx is None:
        print(f'[!] {path}: 未找到锚点，跳过')
        continue
    # 在 cd ./KernelSU 行之后插入（anchor 下一行应为 cd 行）
    cd_idx = anchor_idx + 1
    assert CD_LINE in lines[cd_idx], f'{path}: 锚点下一行不是 cd 行: {lines[cd_idx]!r}'
    new_lines = lines[:cd_idx + 1] + [p + '\n' for p in PATCH] + lines[cd_idx + 1:]
    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    changed.append(os.path.basename(path))

print(f'已修改 {len(changed)} 个:')
for c in changed:
    print('  +', c)
if skipped:
    print(f'跳过（已含修复）{len(skipped)} 个:')
    for s in skipped:
        print('  =', s)
