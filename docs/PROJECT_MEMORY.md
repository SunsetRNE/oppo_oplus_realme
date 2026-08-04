# 🧠 项目记忆（Project Memory）

> 用途：脱离上游（cctv18）、建立自有内核编译平台的**完整状态记忆**，供后续开发延续
> 最后更新：2026-08-04
> 维护原则：每次变更/决策后同步更新本文件，保持与真实状态一致

---

## 1. 项目目标与架构

**目标**：完全脱离 cctv18 上游依赖，构建属于自己的编译平台（源码/补丁/工具链/ccache 全自持），并建立可追溯、可验证的正式发布流程。

**架构**：三平台（sm8850/sm8750/sm8650）统一由 `SunsetRNE/oppo_oplus_realme` 单仓库承载 workflow 与脚本，内核源码与支撑组件分散在 17 个自持仓库。

## 2. 仓库矩阵（17 自持 + 1 统一）

### 统一仓库（主战场）
| 仓库 | 说明 |
|---|---|
| `SunsetRNE/oppo_oplus_realme` | workflow 24 个、sm8850/sm8750/sm8650 子目录、docs 六件套、.ssh |

### 第一梯队：内核源码（10，只能 fork 跟随上游，不可自建）
android_kernel_common_oneplus_sm8850 / sm8750 / sm8650 / sm8845、android_gki_kernel_common、android_kernel_oneplus_mt6993 / mt6991 / mt6989 / mt6897、android_kernel_oppo_mt6993

### 第二梯队：支撑仓（7）
susfs4oki（补丁，7 分支）、oneplus_sm8650_toolchain（附件 8/8，含 1.1GB clang）、public_ccache（附件 78/78，24.83GB，**2026-08-04 全量完成**）、AnyKernel3、Baseband-guard、KPatch-Next（附件 44/44）、ReSukiSU_CI（附件 1848/1848）

> 同步方法：`git fetch upstream --prune; git push origin --all --tags --prune`（网页 Sync fork 只同步默认分支，不可用）

## 3. 认证与凭证

| 项 | 值/说明 |
|---|---|
| SSH 密钥 | `id_ed25519`，隧道 `ssh.github.com:443`，可 push/fetch 代码，**不能调 REST API** |
| PAT | `ghp_***`（SunsetRNE，repo 权限，7 天有效；**明文勿写入任何文档/仓库**，用完可在 settings/tokens 撤销。需要时向用户索要） |
| Git 用户 | SunsetREN / z100o190zgxc@163.com |
| 统一仓库 remote | `git@github.com:SunsetRNE/oppo_oplus_realme.git` |

## 4. 工作区环境（Android）

- 根目录：`/data/user/0/com.ai.assistance.operit/files/workspace/oppo_oplus_realme/`
  - `oppo_oplus_realme/`（统一仓库）
  - `oppo_oplus_realme_sm8850|8750|8650/`（平台仓库，含 .local/patches）
  - `reports/`（01-04 号报告）
- 双通道：`super_admin:terminal`（Ubuntu proot，可访问 sdcard，**无法读应用沙箱 600 权限文件**）；`super_admin:shell`（Android root，可读沙箱）
- **大文件**：上传用 `curl -T`（流式，避免 `--data-binary` OOM）；下载用 `curl -C -` 断点续传 + `--retry`
- **终端坑**：禁止 `set -e`（会退出终端会话）；heredoc 写入大段代码可能双重转义（`\n` 变 `\\n`），复杂脚本用 create_file 写入最稳

## 5. Workflow 体系（24 个）

| 类型 | 数量 | 说明 |
|---|---|---|
| `sm*_fastbuild_*.yml` | 21 | 真实构建+发布；每版本 env 组（TZ/ANDROID_VERSION/KERNEL_VERSION/SUB_VERSION/KERNEL_NAME/CCACHE_KEY）；**2026-08-04 已加哈希三件套** |
| `build-test.yml` | 1 | 三平台矩阵（platform: all/单个），只测发布管线不真编译，tag 带平台前缀 |
| `cleaner.yml` | 1 | 根级清 ccache（DELETE 确认） |
| `clean_workflow.yml` | 1 | 根级清运行记录 |

**哈希验证三件套（ADR-007）**：①计算产物哈希（sha256sum → checksums.sha256 + GITHUB_OUTPUT）②SHA256 写入 Release notes ③发布后下载产物 `sha256sum -c` 自检（失败则 job 失败）。已实战验证（run 30872517396，10min 缓存命中构建，自检通过）。

## 6. 构建流水线（主循环）

```
本地改脚本 → git push（SSH）→ GitHub Actions 触发（PAT API）→ 构建 → Release 发布（带 checksums.sha256）→ 文档记录（RELEASE_LOG）
```

## 7. 文档体系（docs/ 六件套）

| 文档 | 内容 |
|---|---|
| RELEASE_PROCESS.md | 四阶段发布流程 + 红线（>10MB/无dirty/可回滚/参数留痕） |
| TRACKING.md | 17 仓库同步状态表（状态快照） |
| SYNC_LOG.md | 同步变更对照（事件日志，时间倒序；与 TRACKING 分工：事件 vs 状态） |
| DECISIONS.md | ADR-001~007 决策记录 |
| RELEASE_LOG.md | 历史发布台账（正式包 + 测试包区分） |
| PROJECT_MEMORY.md | 本文件，总记忆 |

## 8. 技术要点与坑（务必记住）

1. **sm8650 workflow inputs**：用 `ssg_enable`（非 adios），无 lz4 选项；传不存在的 input 报 422 `Unexpected inputs provided`
2. **GITHUB_ENV 时序**：同一 step 内 `${{ env.xxx }}` 读不到刚写入的值，必须拆两步（写入 step → 使用 step）
3. **job 缺 permissions**：release 类 job 必须 `permissions: contents: write`，否则 HTTP 403
4. **补丁拉取 URL**：统一仓库下需加平台子目录前缀 `$GITHUB_REPOSITORY/raw/refs/heads/$GITHUB_REF_NAME/sm8850/...`
5. **ccache 搬运**：断网导致 curl 55 上传失败时脚本 keep local 不重试（migrate2.py 的已知缺陷），补传用 `curl -T` + 3 次重试即可
6. **build-test 产物**：0.0MB 测试包正常（只测管线），不可刷入设备；正式包必须 fastbuild + >10MB
7. **Release 排序**：GitHub API 默认排序可能把 build-test 的 tag 排前面，查"最新"要用发布时间判断
8. **上游迭代模式**：以"新增内核小版本+CVE 补丁"为主，极少改既有脚本 → 快进合并风险低；新版本脚本可用模板化生成（潜在优化方向）
9. **lz4 与 lz4kd 互斥**：两者都修改 `fs/f2fs/compress.c`，同时开启会补丁冲突（Hunk FAILED → .rej），触发组合参数时二选一（lz4kd=true 须配 lz4_enable=false）
10. **组合测试注意**：批量触发不同参数组合时，先核对 inputs 互斥关系（参考各 workflow inputs 描述），避免无效失败浪费构建时间

## 9. 当前进度（截至 2026-08-04）

**✅ 已完成**
- 17 仓库 fork/复刻 + 附件全量搬运（ccache 78/78、toolchain 8/8、KPatch 44/44、ReSukiSU_CI 1848/1848）
- 统一仓库搭建，cctv18 引用清零，workflow 30→24（清理合并 + build-test 矩阵化）
- 三平台正式发布 ×3（6.12.23 / 6.6.89 / 6.1.141，17-19MB 可刷入包）
- 哈希自动验证上线并实战验证（run 30872517396，10min 缓存命中）
- 文档六件套建齐

**🔄 进行中**
- 批量测试批次 A：sm8850(6.12.58, 6.12.23_mtk)、sm8750(6.6.118, 6.6.89_mtk)、sm8650(6.1.141, 6.1.57) 触发中（部分 204 已触发，需确认全部入队）
- 批次 B 组合测试待触发（sm8850 6.12.23: ksu=none+lz4kd+susfs=false；sm8750 6.6.89: sukisu+droidspaces=standard；sm8650 6.1.141: ksunext+kpm+bbr=default）

**📋 待办**
- 批次 A/B 结果监控与验证（success + >10MB + SHA256 自检）
- 新版本首次构建会生成新 ccache 并回传自持（自动）
- PAT 撤销（7 天自动过期）

## 10. 后续开发路径（循环）

1. 本地改脚本/workflow → 语法验证（bash -n / yaml.safe_load）
2. git commit + push（SSH）
3. PAT API 触发 workflow_dispatch
4. 监控 run → 验证 Release（>10MB + checksums.sha256 + notes SHA256 一致）
5. 更新 RELEASE_LOG.md / TRACKING.md / DECISIONS.md（如涉及）
6. 循环

---

## 🔗 相关文档

- 发布流程：`docs/RELEASE_PROCESS.md`
- 同步跟踪：`docs/TRACKING.md`
- 同步变更：`docs/SYNC_LOG.md`
- 决策记录：`docs/DECISIONS.md`
- 历史发布：`docs/RELEASE_LOG.md`