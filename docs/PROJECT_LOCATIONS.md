# 📍 项目地址索引（Project Locations）

> 用途：本地工作区 ↔ 实际 GitHub 项目地址映射，供后续开发快速定位
> 最后更新：2026-08-04（开发阶段收尾）
> 注：所有仓库 remote 均为 SSH（`git@github.com:...`），API 操作用 PAT

---

## 本地工作区根目录

```
/data/user/0/com.ai.assistance.operit/files/workspace/oppo_oplus_realme/
```

## 仓库映射表

| 本地路径（相对根目录） | 实际 GitHub 地址（SSH） | 分支 | 用途 |
|---|---|---|---|
| `oppo_oplus_realme/` | `git@github.com:SunsetRNE/oppo_oplus_realme.git` | main | **统一构建仓库**：workflow 24 个 + 三平台脚本 + docs 文档体系 |
| `oppo_oplus_realme_sm8850/` | `git@github.com:SunsetRNE/oppo_oplus_realme_sm8850.git` | main | sm8850 平台仓（上游同步源，fork 自 cctv18） |
| `oppo_oplus_realme_sm8750/` | `git@github.com:SunsetRNE/oppo_oplus_realme_sm8750.git` | main | sm8750 平台仓（上游同步源） |
| `oppo_oplus_realme_sm8650/` | `git@github.com:SunsetRNE/oppo_oplus_realme_sm8650.git` | main | sm8650 平台仓（上游同步源） |
| `reports/` | （本地，不入库） | — | 01解析/02扫描/03逻辑链/04执行状态报告 |

## 自持依赖仓库（17 个，均在 SunsetRNE 名下）

统一仓库的 workflow/脚本运行时依赖这些仓库（不直接操作本地）：

**内核源码（10）**：`android_kernel_common_oneplus_sm8850|8750|8650|8845`、`android_gki_kernel_common`、`android_kernel_oneplus_mt6993|6991|6989|6897`、`android_kernel_oppo_mt6993`

**支撑仓（7）**：`susfs4oki`（补丁）、`oneplus_sm8650_toolchain`（工具链 8/8）、`public_ccache`（ccache 78/78）、`AnyKernel3`、`Baseband-guard`、`KPatch-Next`（44/44）、`ReSukiSU_CI`（1848/1848）

> 全部为 `https://github.com/SunsetRNE/<repo>`，SSH 为 `git@github.com:SunsetRNE/<repo>.git`

## 上游源（仅作同步参考，不参与运行时）

`https://github.com/cctv18/<repo>`（17 个仓库的 fork 上游）

## 认证速查

- SSH 密钥：`id_ed25519`（443 隧道 `ssh.github.com`），用于 git 传输
- PAT：`ghp_***`（7 天有效，用时向用户索要），用于 GitHub API
- Git 身份：SunsetREN / z100o190zgxc@163.com

## 常用操作

```bash
# 同步上游（对 3 个平台仓 + 17 个 fork）
git fetch upstream --prune && git push origin --all --tags --prune

# 本地改统一仓库脚本 → 发布
cd oppo_oplus_realme && git add -A && git commit -m "..." && git push origin main
# 然后 PAT 触发 workflow_dispatch（见 docs/PROJECT_MEMORY.md 第 6/10 节）
```

---

## 🔗 相关文档

- 总记忆：`docs/PROJECT_MEMORY.md`（统一仓库内）