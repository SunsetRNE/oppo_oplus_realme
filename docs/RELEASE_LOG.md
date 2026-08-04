# 📜 历史发布记录（Release Log）

> 用途：全部 Release 的可追溯台账（正式包 + 测试包）
> 更新时机：每次发布后按 `docs/RELEASE_PROCESS.md` 阶段 4 追加
> 红线验证：产物 >10MB = 正式包通过；<10MB = 仅管线测试（不得视为正式发布）

---

## 📦 正式构建发布（可刷入内核包）

| 日期(UTC) | 平台 | 内核版本 | Tag | 产物大小 | Run | 验证 |
|---|---|---|---|---|---|---|
| 2026-08-04 04:25 | sm8650 | 6.1.128（天玑） | `...-260804122547` | 17.2MB ✅ | 30877293605 | ✅ 修复cd后成功 |
| 2026-08-04 03:46 | sm8850 | 6.12.23（无KSU+lz4kd） | `OPPO-OPlus-Realme-build-260804114617` | 18.9MB ✅ | 30875455740 | ✅ 组合B修正（ksu=none/lz4kd/susfs=false） |
| 2026-08-04 03:35 | sm8750 | 6.6.89（SukiSU+droidspaces） | `OPPO-OPlus-Realme-build-260804113538` | 17.8MB ✅ | 30874068565 | ✅ 组合B（sukisu/standard） |
| 2026-08-04 03:25 | sm8850 | 6.12.23 | `OPPO-OPlus-Realme-build-260804112518` | 19.3MB ✅ | — | ✅ 批次A默认参数 |
| 2026-08-04 02:45 | sm8850 | 6.12.23-android16-5-ga8f88ad96df3 | `OPPO-OPlus-Realme-build-260804104533` | 18.8MB ✅ | 30872517396 | ✅ >10MB + SHA256自检（缓存命中10min） |
| 2026-08-03 20:02 | sm8850 | 6.12.23-android16-5-ga8f88ad96df3 | `OPPO-OPlus-Realme-build-260804040203` | 18.8MB ✅ | fastbuild | ✅ >10MB |
| 2026-08-03 20:33 | sm8650 | 6.1.141-android14-11-o-gca13bffobf09 | `OPPO-OPlus-Realme-build-260804043309` | 17.3MB ✅ | fastbuild | ✅ >10MB |
| 2026-08-03 20:33 | sm8750 | 6.6.89-android15-8-g29d86c5fc9dd | `OPPO-OPlus-Realme-build-260804043353` | 17.7MB ✅ | fastbuild | ✅ >10MB |

> 参数快照：KSU 分支 / susfs / lz4 / Droidspaces / kernel_suffix 以各 fastbuild workflow 触发时输入为准（GitHub Actions 运行历史可查）。

## 🧪 发布管线测试（build-test 矩阵，非正式包）

| 日期(UTC) | 平台 | Tag | 产物 | 说明 |
|---|---|---|---|---|
| 2026-08-04 01:16 | sm8850 | ~~`OPPO-OPlus-Realme-build-sm8850-260804091613`~~ | 0.0MB 测试包 | 矩阵版首次全绿验证（**已删除**） |
| 2026-08-04 01:16 | sm8750 | ~~`OPPO-OPlus-Realme-build-sm8750-260804091613`~~ | 0.0MB 测试包 | 同上（**已删除**） |
| 2026-08-04 01:16 | sm8650 | ~~`OPPO-OPlus-Realme-build-sm8650-260804091615`~~ | 0.0MB 测试包 | 同上（**已删除**） |

> ⚠️ 2026-08-04 起 build-test 已**取消 Release 发布**（仅保留打包/管线测试），正式包一律走 fastbuild 流程并满足 >10MB 红线。

---

## 发布速查

- 命名规范：`OPPO-OPlus-Realme-build-<yyMMddHHmmss>`（fastbuild）/ `...-build-<platform>-<yyMMddHHmmss>`（矩阵）
- 回滚方式：Delete release + 删 tag（GitHub 允许，见 RELEASE_PROCESS 红线）
- 记录要求：日期 / 平台 / 版本 / tag / run id / 参数摘要 / 产物（每行一条）

---

## 🔗 相关文档

- 发布流程：`docs/RELEASE_PROCESS.md`
- 决策记录：`docs/DECISIONS.md`
- 同步状态：`docs/TRACKING.md`