# 📦 正式发布流程（Release Process）

> 目的：让每次内核发布可追溯、可验证、可复现
> 适用范围：`sm*_fastbuild_*.yml` 真实构建发布的正式版本

---

## 阶段 0｜发布前准备（Checklist）

- [ ] **上游同步确认**：核对 `docs/TRACKING.md`，涉及的源码仓/补丁仓是否已同步到目标版本
- [ ] **工作区干净**：`git status` 无未提交变更（除 `.ssh/` 等被忽略文件）
- [ ] **参数确认**：明确本次发布的 KSU 分支 / susfs / lz4 / Droidspaces / kernel_suffix
- [ ] **版本目标**：确认内核版本（如 6.12.58）与源码分支对应（见 `sm<平台>/README.md`）

## 阶段 1｜触发构建

1. 打开仓库 **Actions** → 选择 `sm<平台>_fastbuild_<版本>` 工作流
2. **Run workflow** → 填写参数（与阶段 0 确认一致）
3. 记录：`Run ID`（Actions 页 URL 末尾数字）→ 填入 `docs/RELEASE_LOG.md`

## 阶段 2｜构建验证（产物检查单）

- [ ] workflow 结论 = **success**
- [ ] Release tag 已创建，命名规范：`OPPO-OPlus-Realme-build-<yyMMddHHmmss>`（fastbuild）或 `OPPO-OPlus-Realme-build-<platform>-<yyMMddHHmmss>`（矩阵 build-test）
- [ ] 产物 zip 存在且 **大小 > 10MB**（小于 10MB 说明内核未正确打包，警惕）
- [ ] （可选）下载 zip 检查 `Image` 文件存在
- [ ] Release notes 关键信息正确（内核版本 / KSU 分支 / 特性开关）

## 阶段 3｜发布确认

- [ ] 确认 Release 为 **latest**（非 draft / prerelease）
- [ ] 确认 tag 指向的 commit 是期望版本
- [ ] 如发现异常：在 Release 页 **Delete release + 删 tag**，修复后重新走阶段 1

## 阶段 4｜发布后记录

- [ ] 更新 `docs/RELEASE_LOG.md`（追加一行：日期 / 平台 / 版本 / tag / run id / 参数摘要 / 产物）
- [ ] 如本次发布涉及上游同步：同步更新 `docs/SYNC_LOG.md` 与 `docs/TRACKING.md`
- [ ] 如有设计/流程变更：追加 `docs/DECISIONS.md`

---

## ⚠️ 红线规则

| 规则 | 说明 |
|---|---|
| 禁止发布空包 | 产物 <10MB 视为异常，禁止标记 latest |
| 禁止带 dirty 构建发布 | 构建日志中出现 `-dirty` 需确认非预期 |
| 发布必须可回滚 | tag + release 删除即可回滚（GitHub 允许） |
| 参数必须留痕 | 发布日志必须记录本次参数快照 |

## 🔗 相关文档

- 同步状态表：`docs/TRACKING.md`
- 同步变更对照：`docs/SYNC_LOG.md`
- 转化决策记录：`docs/DECISIONS.md`
- 历史发布记录：`docs/RELEASE_LOG.md`