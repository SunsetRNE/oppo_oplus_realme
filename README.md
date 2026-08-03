# 🌟 oppo_oplus_realme · 欧加真内核统一构建平台

> **脱离上游（cctv18）的自有内核编译平台** —— 所有依赖指向 SunsetRNE 名下自持仓库

本仓库整合了欧加（OPPO / 一加 / 真我）三代旗舰平台的自动化内核编译框架，基于 cctv18 开源方案重构自持，目标：**编译链路 100% 自主可控，上游仅作为可选的同步源**。

## 📱 平台支持

| 子目录 | 芯片平台 | 内核版本 | 工具链 | Android |
|---|---|---|---|---|
| `sm8850/` | 骁龙 8 Elite Gen5 (SM8850) / 天玑 9500 (MT6993) | 6.12.x | LLVM/Clang 19 + Rust 1.82 | A16 |
| `sm8750/` | 骁龙 8 Elite (SM8750) / 天玑 9400+ (MT6991) | 6.6.x（含风驰 scx 移植） | LLVM/Clang 18 | A15 |
| `sm8650/` | 骁龙 8 Gen3 (SM8650) / 天玑 9400e (MT6989) / 天玑 8350 (MT6897) | 6.1.x | LLVM/Clang 20 | A14/A15 |

## 🗂️ 仓库结构

```
oppo_oplus_realme/
├── sm8850/  sm8750/  sm8650/      # 三平台内容（local脚本/补丁/lib/zram）
├── .github/workflows/              # 30 个工作流（sm<平台>_<用途>.yml）
│   ├── sm8850_fastbuild_6.12.23.yml       # 在线构建（按平台+内核版本）
│   ├── sm8850_build-test.yml              # 发布测试
│   ├── sm8850_cleaner.yml                 # 清理 ccache（需 DELETE 确认）
│   └── ...
├── .ssh/                           # SSH 配置（git@github.com 443 隧道）
└── reports/                        # 解析/扫描/逻辑链报告
```

## 🚀 使用方式

### 在线编译（GitHub Actions）
1. 进入仓库 **Actions** 页 → 选择对应平台的 `fastbuild_<版本>` 工作流
2. **Run workflow** → 配置参数（KSU 分支 / susfs / lz4 / Droidspaces / BBR 等）
3. 构建完成后自动发布 Release（`OPPO-OPlus-Realme-build-*` tag）

### 本地编译
```bash
cd sm8850/local && bash builder_6.12.58.sh   # 按提示交互配置
# 产物: Anykernel3-oppo+oplus+realme-<特性标签>-v<日期>.zip
```

## 🔗 依赖自持清单（已全部迁移至 SunsetRNE）

| 依赖 | 自持仓库 | 状态 |
|---|---|---|
| 内核源码 ×10 | `SunsetRNE/android_kernel_*` | ✅ 已 fork（全部分支同步） |
| 编译工具链 | `SunsetRNE/oneplus_sm8650_toolchain` | ✅ 8/8 附件已搬运 |
| 公共 ccache | `SunsetRNE/public_ccache` | ✅ 78/78 附件已搬运 |
| susfs 补丁 | `SunsetRNE/susfs4oki` | ✅ 已 fork（7 分支） |
| KPM 模块 | `SunsetRNE/KPatch-Next` | ✅ 44/44 附件已搬运 |
| 刷机模板 | `SunsetRNE/AnyKernel3` | ✅ 已 fork |
| 基带保护 | `SunsetRNE/Baseband-guard` | ✅ 已 fork |
| KSU 管理器 | `SunsetRNE/ReSukiSU_CI` | ✅ 1848/1848 附件已搬运 |

## 🔄 上游同步（可选）

```bash
# 对每个 fork 仓库执行（建议放入 cron / Actions schedule）
git remote add upstream https://github.com/cctv18/<repo>.git
git fetch upstream --prune
git push origin --all --tags --prune
```

## 📌 当前工作流配置（对标上游基线）

- **补丁顺序链**：dirty清理 → 版本后缀 → KSU注入 → susfs → lz4/zstd → lz4kd → defconfig → config隐藏 → Droidspaces → BBG
- **ccache 三级缓存**：actions/cache → 公共 release → 上传覆盖（`ccache_update` 控制）
- **KSU 版本号**：ReSukiSU `rev-list+30700` / Next & KSU `分页数+30000`
- **产物命名**：`Anykernel3-<机型>-<特性标签>-v<日期>.zip`

> 注：`@cctv18` 署名已统一替换为 `@SunsetRNE`；本地脚本补丁 URL 已指向自持仓库。