# 待办与技术债清单

> 状态基准：`master` @ Phase 5 完成（M1 核心闭环 + 用户系统）。
> 后端 265 passed / 15 skipped / 3 errors（skip 与 error 原因见下）。
> 本文件只记录**已知未完成 / 未验证**的事项，完成后请更新状态并注明验证方式。

图例：🔴 阻断上线 · 🟠 上线前必做 · 🟡 应做 · ⚪ 可选

---

## A. 验证缺口（"写了但从没真跑过"）

### A1 🟠 真实 MySQL 仓储层未验证 —— **15 个集成测试长期被跳过**

- **现状**：`tests/test_repositories_mysql.py` 全部用例由 `RUN_MYSQL_TESTS=1` 守卫，
  默认跳过。开发机上 MySQL 从未跑起来（Docker daemon 未运行），因此
  **建表 / 用户 CRUD / upsert 语义 / 历史分页与 range 过滤 / 统计聚合 SQL /
  跨用户数据隔离** 这些真实 SQL 一行都没执行过，只有 mock 测试背书。
- **影响**：Phase 5 持久化是本项目唯一的真实数据库逻辑，SQL 写错（字段名、
  索引、`ON DUPLICATE KEY` 语义、时区/日期边界）测试完全发现不了。
- **怎么验**：已在 `backend/scripts/verify_mysql.py` 里串好一键流程：
  ```powershell
  cd backend
  .\.venv\Scripts\python scripts\verify_mysql.py        # 起库 + 跑集成测试
  .\.venv\Scripts\python scripts\verify_mysql.py --e2e  # 额外跑用户系统 e2e
  ```
  若提示连不上 Docker daemon，先在**普通终端**启动 Docker Desktop。
  集成测试用独立库 `chuangguan_test`，不会碰开发库。
- **静态复查发现的隐患（尚未被任何测试覆盖，跑集成测试时重点看）**：
  1. **时区口径不一致（最可疑）**：`created_at` 用 MySQL 的 `CURRENT_TIMESTAMP`
     （服务器时区），而过滤/聚合的"起点"用 Python 的朴素 `datetime.now()`
     （操作系统本地时区）—— 见 `quiz_repository.get_user_answer_stats` /
     `get_user_quiz_list` / `get_user_daily_stats`、`history_service`、
     `user_service._week_start`。**系统未做任何时区归一化**（无 `SET time_zone`、
     无 `init_command`，仅靠 README 里 `docker run -e TZ=Asia/Shanghai` 兜着）。
     若 MySQL 实际按 UTC 跑而机器是 UTC+8，则"最近 7 天""本周""连续打卡"
     会有 8 小时偏移，**且现有 mock 测试原理上无法发现**。建议显式统一
     （连接层 `init_command="SET time_zone='+08:00'"`，或改用 UTC 存储 + 应用侧换算）。
  2. `ON DUPLICATE KEY UPDATE` 的 `VALUES ... AS new` 别名语法需 MySQL **≥ 8.0.19**；
     且 `return cur.rowcount == 1` 依赖 PyMySQL 对 rowcount 的语义（插入=1、
     更新=2、值无变化=0）。这直接决定 XP 是否重复累加，必须真机核对。
  3. `answer_records` / `reports` 都有指向 `quiz_sessions(quiz_id)` 的外键，
     因此落库顺序必须严格是"先 quiz_sessions 后 answer_records/reports"；
     若顺序颠倒会抛外键错误（当前被 `except Exception` 吞掉只记日志，
     表现为**静默不落库**）。
  4. `docker run` 的 `--character-set-server` 等参数写在镜像名之后，传参正确；
     但容器首次初始化若失败会反复重启，`docker logs` 优先看。

- [ ] 跑通 15 个 MySQL 集成测试并记录结果
- [ ] 跑 `scripts/e2e_user_system.py`（登录 → 落库 → 回看 → 匿名回归）
- [ ] 跑 `scripts/e2e_avatar.py`（头像上传链路）
- [ ] 核对上面 4 条隐患（尤其时区口径）并修复
- [ ] 把 `RUN_MYSQL_TESTS=1` 纳入 CI（见 C1）

### A2 🟡 真实微信登录（jscode2session）未验证

- **现状**：`.env` 里 `WECHAT_APP_ID`/`WECHAT_APP_SECRET` 为空，
  `WECHAT_MOCK_LOGIN=true` → 走的是开发降级分支（固定 `dev_openid_default`）。
  真实 `jscode2session` 调用路径只有单测（mock httpx）覆盖。
- **怎么验**：填入真实小程序 AppID/AppSecret，`WECHAT_MOCK_LOGIN=false`，
  在微信开发者工具里走一次登录，确认 openid 落库且多次登录是同一用户。
- [ ] 真实 AppID/Secret 下验证登录

### A3 🟡 微信开发者工具里的人工验收未做

- **现状**：自动化只覆盖后端与类型检查，视觉与真机交互没人看过。
- **注意**：务必用 `npm run dev:weapp`（**不要** `build:weapp`，否则注入
  `config/prod.ts` 的占位域名 `https://your-domain.example.com`，表现为
  `ERR_NAME_NOT_RESOLVED`），并在「详情 → 本地设置」勾选**不校验合法域名**。
- [ ] 走通 M1 闭环：输入 → 出题 → 答题讲解 → 结算 → 报告 → 分享
- [ ] 逐帧对照原型 01–04（含 `pages/stats` 学习统计页）
- [ ] 真机（非模拟器）验证一次

### A4 ⚪ 报告链真实调用仅验证过单次

- `scripts/verify_deepseek.py --report` 已跑通；出题链的**结构稳定性**建议按
  方案设计第 12 章的做法做「同主题连续 10 次出题」检查，确认 JSON 五级保障
  在真实脏数据下不翻车。
- [ ] 连续 10 次真实出题，统计失败率与重试次数

---

## B. 上线前必做

### B1 🔴 `JWT_SECRET` 仍是默认值

- **现状**：`app/core/config.py` 默认 `"change-me-in-production"`，
  且 `.env` 未覆盖 → 当前签发/校验用的是这个公开常量。
  任何人都能伪造 JWT 冒充任意 `user_id`。
- [ ] 生成强随机值并写入生产环境变量（`JWT_SECRET`），确认 `.env` 不进仓库

### B2 🔴 生产环境必须关掉微信登录降级

- [ ] `WECHAT_MOCK_LOGIN=false` + 真实 AppID/Secret（否则任何人都能免登录拿 token）

### B3 🟠 头像本地磁盘存储，多实例部署会失效

- **现状**：`backend/data/avatars/` 本地落盘，`/static` 由单进程挂载。
- **影响**：微信云托管多实例/重启后用户头像 404。
- [ ] 换对象存储（腾讯云 COS），或在部署方案里明确单实例 + 持久化卷

### B4 🟠 生产域名占位符未替换

- `frontend/config/prod.ts` → `API_BASE_URL: '"https://your-domain.example.com/api/v1"'`
- [ ] 换成正式域名（需先完成 ICP 备案 + 云托管部署）

### B5 🟠 K12 合规项未办

- [ ] 「深度合成 - AI 问答」类目申请
- [ ] AI 生成内容标识（出题/报告均需明示 AI 生成）
- [ ] 隐私政策 + 未成年人保护说明（小程序后台需配置）
- 依据：方案设计文档第 11 章

---

## C. 工程质量

### C1 🟡 无 CI，全部验证靠手动

- **现状**：没有 `.github/workflows` 等任何流水线；265 个测试要人工记得跑。
- [ ] 加 CI：`pytest`（含 `RUN_MYSQL_TESTS=1` + MySQL service 容器）
- [ ] 加前端 `npx tsc --noEmit` 到 CI
- [ ] 建议同时把「代理环境变量」回归测试纳入（`tests/test_proxy_env.py`）

### C2 🟡 无远程仓库（**当前最高风险项**）

- **现状**：`git remote -v` 为空，全部提交只存在本地磁盘一份。
- [ ] `git remote add origin <url>` 并推送（建议私有仓库）

### C3 🟡 沙箱/新机器上 3 个头像测试会误报

- **现象**：`test_avatar_api.py` 报 `PermissionError: [WinError 5] ...\Temp\...\pytest-of-*`
- **原因**：`TEMP`/`TMP` 被重定向到不可写目录，`tmp_path` fixture 失败 ——
  **环境问题，非代码缺陷**。
- [ ] 可选：让测试不依赖系统 temp（fixture 显式指定 `tmp_path_factory` 到项目内目录）

### C4 ⚪ 标题字体仍是系统粗体回退

- `font-display`（站酷快乐体）未加载。原因是 `wx.loadFontFace` 网络字体源会触发
  基础库异步域名安全检查，报 `webapi_getwxaasyncsecinfo:fail`。
- 两种正式方案：① 字体放已备案 CDN 并加入 request 合法域名白名单；
  ② 字体子集化后以 base64 data URI 本地加载（免域名检查）。
- [ ] Phase 9 视觉打磨时一并处理

### C5 ⚪ 体量增长后的技术债

- `app/main.py` 已同时承担路由注册、异常处理、静态挂载、启动编排，后续可拆
- `task_store` 仍是内存字典（异步出题任务），多实例部署需落 `quiz_tasks` 表
- 无请求级 trace_id / 结构化日志关联

---

## D. 尚未开始的功能阶段

按 `方案设计文档.md` 第 10 章：

| 阶段 | 内容 | 状态 |
|---|---|---|
| Phase 6 | Tavily 联网搜索（LangGraph ReAct Agent） | 未开始 |
| Phase 7 | 文档上传 + RAG 知识库（Chroma + 百炼 Embedding） | 未开始 |
| Phase 8 | AI 生图配图 + COS（`qwen-image-2.0`，20 张/日额度） | 未开始 |
| Phase 9 | 分享海报（Canvas 长图）+ 视觉打磨 | 未开始 |
| Phase 10 | 微信云托管部署 + 审核发布 | 未开始 |

- [ ] **建议顺序**：先把 A1/A2/A3 与 B1/B2 做掉再开 Phase 6。
  理由：真实 MySQL 或真实模型一旦暴露问题，此时改动成本远低于在 Phase 6/7
  之上再发现。

---

## E. 已确认不做（避免重复讨论）

- 分享海报页（原型的第 3 帧）→ 已确认不做，报告页走微信转发
- 原型 05 全部扩展功能 → V2 前瞻，不进 MVP
- 原型 04 的知识库入口 → 随 Phase 7 引入
