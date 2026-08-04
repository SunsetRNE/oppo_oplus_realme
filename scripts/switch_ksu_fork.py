#!/usr/bin/env python3
"""将 21 个 fastbuild workflow 的 ksu 分支从 tiann/KernelSU 切换到自持 SunsetRNE/KernelSU。
1. setup.sh URL → SunsetRNE，并在管道中 sed 替换 setup.sh 内部的 clone URL（tiann→SunsetRNE）
2. KSU_VERSION 计算 API → SunsetRNE
幂等：已含 SunsetRNE/KernelSU 的 setup.sh URL 则跳过。"""
import glob
import os

WORKFLOWS = sorted(glob.glob('.github/workflows/sm*_fastbuild_*.yml'))

OLD_SETUP = 'https://raw.githubusercontent.com/tiann/KernelSU/refs/heads/main/kernel/setup.sh'
NEW_SETUP = 'https://raw.githubusercontent.com/SunsetRNE/KernelSU/refs/heads/main/kernel/setup.sh'
# setup.sh 内部 git clone 的 URL 也要替换（sed 注入管道）
PIPE_SED = "sed 's|https://github.com/tiann/KernelSU|https://github.com/SunsetRNE/KernelSU|g' | "
OLD_VER = 'https://api.github.com/repos/tiann/KernelSU/commits?sha=main&per_page=1'
NEW_VER = 'https://api.github.com/repos/SunsetRNE/KernelSU/commits?sha=main&per_page=1'

changed = []
skipped = []
for path in WORKFLOWS:
    with open(path, encoding='utf-8') as f:
        text = f.read()
    if NEW_SETUP in text:
        skipped.append(os.path.basename(path))
        continue
    new_text = text
    # 1. setup.sh URL + 管道 sed（处理 setup.sh 内部 clone）
    new_text = new_text.replace(f'curl -LSs "{OLD_SETUP}" | bash -s main',
                                f'curl -LSs "{NEW_SETUP}" | {PIPE_SED}bash -s main')
    # 2. KSU_VERSION API
    new_text = new_text.replace(OLD_VER, NEW_VER)
    if new_text == text:
        print(f'[!] {path}: 无匹配，跳过')
        continue
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_text)
    changed.append(os.path.basename(path))

print(f'已切换 {len(changed)} 个:')
for c in changed:
    print('  +', c)
if skipped:
    print(f'跳过（已切换）{len(skipped)} 个:')
    for s in skipped:
        print('  =', s)