# 🧭 转化决策记录（Decision Log / ADR）

> 用途：记录"脱离上游、自持平台"过程中的**关键决策**及其理由，供后续变更优化参考
> 格式：ADR-xxx ｜ 状态（Accepted / Superseded）
> 原则：决策必须有理由、有替代方案、有后果

---

## ADR-001 ｜ 脱离 cctv18 依赖，建立自持仓库体系
- **状态**：Accepted（2026-08-03）
- **背景**：上游 cctv18 的仓库体系限制了构建的自主性（依赖其硬编码 URL、附件、分支）
- **决策**：fork 第一梯队（10 内核源码仓）+ 第二梯队（7 支撑仓）共 17 个仓库到 SunsetRNE 名下，脚本/workflow 的 URL、署名全部改为自持仓库
- **替代方案**：继续使用上游引用（否决：无法脱离限制）；全部自建源码（否决：内核源码无法自行重建）
- **后果**：✅ 运行时零上游依赖；⚠️ 需维护同步机制（TRACKING/SYNC_LOG）；⚠️ 附件需自持搬运（KPatch 44/44、toolchain 8/8、ccache 78 全量）

## ADR-002 ｜ 统一仓库承载三平台 workflow
- **状态**：Accepted（2026-08-03）
- **背景**：三平台各自独立仓库 + 独立 workflow，存在大量重复代码
- **决策**：新建 `SunsetRNE/oppo_oplus_realme` 统一仓库，三平台内容按 `sm8850/ sm8750/ sm8650/` 子目录整合，workflow 带平台前缀；补丁拉取 URL 加子目录前缀
- **替代方案**：维持三仓独立（否决：重复维护成本高）；monorepo 全量合并（否决：内核源码体积过大）
- **后果**：✅ workflow 从 30 个精简至 24 个；✅ 单仓库管理；⚠️ URL 需带平台前缀，新增版本时注意路径

## ADR-003 ｜ 清理类 workflow 合并为根级
- **状态**：Accepted（2026-08-04）
- **背景**：统一仓库后 `cleaner.yml` / `clean_workflow.yml` 每平台各一份（共 6 个），md5 确认内容完全相同
- **决策**：删除 6 个平台副本，合并为根级 2 个（全仓库级清理）
- **替代方案**：保持现状（否决：纯冗余）；按平台保留（否决：清理逻辑天然全仓库级）
- **后果**：✅ 30→26 workflows；✅ 触发方式统一

## ADR-004 ｜ build-test 矩阵化（三平台合一）
- **状态**：Accepted（2026-08-04）
- **背景**：三份 `sm*_build-test.yml` 仅 env 5 变量不同（219 行结构一致）
- **决策**：合并为单份矩阵版：`platform` 输入（all/单平台）+ matrix 参数化 + tag 带平台前缀防并行冲突
- **代价**：调试中发现两个 bug——GITHUB_ENV 同步骤读取为空（需拆分两步）、job 缺 `permissions: contents: write`（HTTP 403），已修复
- **后果**：✅ 26→24 workflows；✅ 触发一次测三平台；⚠️ sm8650 无 adios/lz4 输入（用 ssg_enable），矩阵参数需分平台定义

## ADR-005 ｜ 正式发布流程（先文档化，后沉淀 workflow）
- **状态**：Accepted（2026-08-04）
- **背景**：发布目前是"自动构建 + 人工眼检"，不可追溯、不可验证
- **决策**：先落地四阶段文档 checklist（准备→触发→验证→确认→记录），跑顺后再沉淀为 workflow 步骤；配套红线规则（>10MB / 无 dirty / 可回滚 / 参数留痕）
- **替代方案**：直接写 workflow 强制门禁（否决：约束过强，先轻量跑顺）；完全人工（否决：不可追溯）
- **后果**：✅ 发布可追溯可验证；⚠️ 当前依赖人工执行 checklist，后续可自动化

## ADR-006 ｜ 文档五件套体系
- **状态**：Accepted（2026-08-04）
- **背景**：脱离上游后需要长期运维记忆，防止"改了不知道、坏了找不到"
- **决策**：统一仓库 `docs/` 下五件套：
  - `RELEASE_PROCESS.md` — 发布流程与红线
  - `TRACKING.md` — 17 仓库同步状态表
  - `SYNC_LOG.md` — 每次同步的变更对照
  - `DECISIONS.md` — 本文件，决策记录
  - `RELEASE_LOG.md` — 历史发布记录
- **后果**：✅ 任何变更有据可查；⚠️ 需养成每次操作后更新的习惯

## ADR-007 ｜ 产物哈希由 workflow 自动验证
- **状态**：Accepted（2026-08-04）
- **背景**：发布验证原先只有">10MB"粗检查（人工眼检），无法证明产物完整性（上传损坏/篡改不可发现）
- **决策**：21 个 fastbuild workflow 统一加三件套：①发布前计算 `sha256sum` 并上传 `checksums.sha256` 到 Release；②SHA256 写入 Release notes；③发布后自动下载产物做 `sha256sum -c` 自检（失败则 job 失败）
- **替代方案**：人工计算哈希（否决：违背可验证初衷）；仅 notes 展示（否决：无独立校验文件，无法 `sha256sum -c`）
- **后果**：✅ 发布即自带完整性校验依据，任何人可复验；✅ 上传损坏自动拦截；⚠️ Release 多一个 asset（可忽略体积）；⚠️ 自检步骤多一次下载（~20MB）

## ADR-008 ｜ zram.zip 被 .gitignore 忽略导致打包 404
- **状态**：Accepted（2026-08-04）
- **背景**：统一仓库整合时 `.gitignore` 含 `*.zip`，三平台 `zram.zip` 从未入库；特定参数组合（ksu_type=none）打包时下载 `sm8850/zram.zip` 触发 404 → 构建失败（exit 8）
- **决策**：`git add -f` 强制添加三平台 zram.zip；后续新增二进制附件时注意检查 .gitignore 规则
- **替代方案**：改 .gitignore 规则（否决：会放开所有 zip 忽略，影响面大）；改为 release 附件分发（否决：workflow 已用 raw URL）
- **后果**：✅ 三平台 zram.zip 已入库（sm8850 298KB / sm8750+sm8650 各 194KB）；⚠️ raw CDN 对曾 404 的 URL 有负缓存，push 后需等待刷新（数分钟）

## ADR-009 ｜ 6.1.128 workflow 缺失 cd kernel_workspace
- **状态**：Accepted（2026-08-04）
- **背景**：批次C测试发现 6.1.128（天玑特供）默认参数构建失败——`[ERROR] "drivers/" directory not found`（exit 127）。排查：全量对比 21 个 workflow，「添加KernelSU」步骤开头仅 6.1.128 缺少 `cd kernel_workspace`（20/21 有），导致 ReSukiSU setup.sh 在源码父目录执行找不到 `./drivers/`
- **决策**：补上 `cd kernel_workspace`，与其余 20 个 workflow 对齐；该 bug 为上游 workflow 缺陷（非我们引入），修复后**回写上游友好提醒**（可选）
- **后果**：✅ 修复推送（51b5205）并重新触发验证；⚠️ 上游下次同步可能覆盖此修复，需注意（SYNC 时检查）

## ADR-010 ｜ ksu=原版 KernelSU 曾不可用 → 已解决（O=out 分离构建路径缺陷）
- **状态**：**Superseded（2026-08-04 晚，已修复并实测验证）**
- **背景**：批次D组合一（ksu原版+kpm+rekernel）编译失败：`drivers/kernelsu/feature/kernel_umount.c: fatal error: 'klog.h' not found`。初判为 tiann/KernelSU 上游漂移（klog.h 移到 `kernel/include/`）
- **根因（修正）**：上游 main 其实早已适配新布局（`kernel/` 根结构 + Kbuild `-I$(KSU_KERNEL_DIR)/include`），susfs4oki 的 KSU 补丁也适配新布局。真正的坑是**我们 workflow 使用 `O=out` 分离构建**，Kbuild 中 `$(src)` 变成 `../drivers/kernelsu`（相对 out 目录），与 `$(srctree)` 拼接后得到不存在的路径（`common/../drivers/kernelsu`），导致 `-I` 指向空目录 → klog.h 找不到。**上游自身 GKI 构建（源码树内）无此问题**
- **修复**：workflow 的 ksu 分支在 `cd ./KernelSU` 后注入绝对 include 路径（sed 替换 `-I$(KSU_KERNEL_DIR)` 为 `-I$(pwd)/kernel`），21 个 fastbuild 全部套用（脚本 `scripts/patch_ksu_absdir.py`）
- **验证**：sm8850 6.12.23 ksu_type=ksu 构建成功（run 30913997284），Release 产物 `AnyKernel3_KSU_32570_6.12_...zip` 18.8MB + checksums.sha256 ✅
- **教训**：遇到"上游漂移"类报错，先自查构建模式差异（O=out / 源码树内），再怪上游
- **遗留**：SunsetRNE/KernelSU fork（parent=rsuntk/KernelSU）Clippy 在 rustc 1.97 下有 2 个 `useless_borrows_in_formatting` lint 错误（上游代码 `&rule_file.display()` 未修），需 `&` 去掉或锁 1.96 toolchain——与本次内核构建无关，仅影响该 fork 的 CI

---

## 🔗 相关文档

- 发布流程：`docs/RELEASE_PROCESS.md`
- 同步跟踪：`docs/TRACKING.md`
- 同步变更：`docs/SYNC_LOG.md`
- 历史发布：`docs/RELEASE_LOG.md`