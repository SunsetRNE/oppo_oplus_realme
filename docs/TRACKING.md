# 🗂️ 上游同步跟踪表（Upstream Tracking）

> 用途：记录 17 个自持仓库与上游（cctv18）的同步状态
> 更新时机：每次同步后、每次发布前确认

## 同步方法

```bash
# 对每个 fork 仓库
git remote add upstream https://github.com/cctv18/<repo>.git   # 首次
git fetch upstream --prune
git push origin --all --tags --prune
```

> ⚠️ 网页版 "Sync fork" 只同步默认分支；全分支同步必须用 CLI（如上）。

## 跟踪表（截至 2026-08-04）

| # | 上游仓库 | 自持仓库 | 类型 | 同步点 | 状态 |
|---|---|---|---|---|---|
| 1 | cctv18/oppo_oplus_realme_sm8850 | SunsetRNE/oppo_oplus_realme_sm8850 | 框架主仓 | 2026-08-03（bea18f0→69ab979） | ✅ 已同步 |
| 2 | cctv18/oppo_oplus_realme_sm8750 | SunsetRNE/oppo_oplus_realme_sm8750 | 框架主仓 | 2026-08-03（b4f1ce4→21db9e7） | ✅ 已同步 |
| 3 | cctv18/oppo_oplus_realme_sm8650 | SunsetRNE/oppo_oplus_realme_sm8650 | 框架主仓 | 2026-08-03（c9f0da1 最新） | ✅ 已同步 |
| 4 | cctv18/android_kernel_common_oneplus_sm8850 | SunsetRNE/同左 | 内核源码 | 2026-08-03 fork 全分支 | ✅ |
| 5 | cctv18/android_kernel_common_oneplus_sm8750 | SunsetRNE/同左 | 内核源码 | 2026-08-03 fork 全分支 | ✅ |
| 6 | cctv18/android_kernel_common_oneplus_sm8650 | SunsetRNE/同左 | 内核源码 | 2026-08-03 fork 全分支 | ✅ |
| 7 | cctv18/android_kernel_common_oneplus_sm8845 | SunsetRNE/同左 | 内核源码 | 2026-08-03 fork 全分支 | ✅ |
| 8 | cctv18/android_gki_kernel_common | SunsetRNE/同左 | 内核源码(GKI) | 2026-08-03 fork 全分支 | ✅ |
| 9 | cctv18/android_kernel_oneplus_mt6993 | SunsetRNE/同左 | 内核源码(MTK) | 2026-08-03 fork 全分支 | ✅ |
| 10 | cctv18/android_kernel_oppo_mt6993 | SunsetRNE/同左 | 内核源码(MTK) | 2026-08-03 fork 全分支 | ✅ |
| 11 | cctv18/android_kernel_oneplus_mt6991 | SunsetRNE/同左 | 内核源码(MTK) | 2026-08-03 fork 全分支 | ✅ |
| 12 | cctv18/android_kernel_oneplus_mt6989 | SunsetRNE/同左 | 内核源码(MTK) | 2026-08-03 fork 全分支 | ✅ |
| 13 | cctv18/android_kernel_oneplus_mt6897 | SunsetRNE/同左 | 内核源码(MTK) | 2026-08-03 fork 全分支 | ✅ |
| 14 | cctv18/susfs4oki | SunsetRNE/susfs4oki | susfs 补丁 | 2026-08-03 fork 全分支（7） | ✅ |
| 15 | cctv18/oneplus_sm8650_toolchain | SunsetRNE/同左 | 工具链(附件) | 2026-08-04 附件 8/8 | ✅ |
| 16 | cctv18/public_ccache | SunsetRNE/public_ccache | ccache(附件) | 2026-08-04 附件 78/78（含4个断网失败后补传） | ✅ |
| 17 | cctv18/AnyKernel3 / Baseband-guard / KPatch-Next / ReSukiSU_CI | SunsetRNE/同左 | 组件 | 附件已全量（1848/44） | ✅ |

## 同步后必做

1. 更新本表"同步点"列
2. 检查是否有**补丁/脚本逻辑变化**（读上游 commit 摘要）→ 写 `docs/SYNC_LOG.md`
3. 如涉及 workflow/脚本 → 触发一次冒烟测试验证
4. 如涉及新内核版本 → 按 `docs/RELEASE_PROCESS.md` 走发布流程