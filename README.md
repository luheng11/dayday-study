# 闯关学堂 · K12 AI 知识闯关学习小程序（M1 MVP）

把「想学的任何知识」变成可操作、可反馈、可复盘的严肃学习闭环。
面向中小学学生（K12），视觉风格「轻漫画风 · 校园闯关手账」。

> 依据：`需求分析文档.txt` V1.2 · `方案设计文档.md` V1.0 · UI 原型 `01–05*.html`
> 参考项目（只读基准）：`reference/yu-ai-learn`（鱼皮 yu-ai-learn）

---

## 一、本次交付范围（已与用户确认）

- **方案 A：M1 核心闭环（Phase 0–4）**，无登录、无数据库，仅需 DeepSeek Key（无 Key 可开 Mock 模式演示）
- ✅ 首页 4 态（默认 / 输入态 / AI 生成中 / 失败重试）+ 3 个 K12 示例主题
- ✅ 闯关答题（单选 / 多选 / 判断，即时判题 + 讲解气泡 + ❤ + ⭐）
- ✅ 通关结算 + 复盘报告（微信转发分享）
- ✅ 4 Tab（首页 / 闯关 / 报告 / 我的）；闯关 Tab 续答、报告 Tab 报告库
- ✅ 后端：health / quiz 同步 / quiz 异步+轮询 / report 四类接口，TDD 全量测试
- ✅ **Phase 5 用户系统**：MySQL 4 表持久化 + 微信静默登录（jscode2session+JWT，开发降级模式）+ 可选鉴权改造（匿名可用）+ 用户档案/闯关历史/学习统计/头像上传接口 + 前端「我的」学习档案（原型 4.1）、学习统计页（4.2）、报告 Tab 报告库（4.3）、首页真实昵称/成长值/最近学过
- ❌ 本版本不做：分享海报页（已确认）、原型 05 扩展功能（V2 前瞻）、MySQL quiz_tasks/kb_documents/生图表（对应 Phase 6–8）、联网搜索/RAG/AI 生图

**已确认的关键决策**：输入上限 2000 字；❤ 仅氛围不惩罚（扣完仍可答题）；分值 单选10/多选15/判断10⭐（服务端 XP 同规则累加）；3 题=1:1:1、5 题=3:1:1 配比；难度 入门/适中/挑战→easy/medium/hard（默认适中）；未登录隐藏「最近学过」、成长值从 0 起；等级表（0/100/300/600/1000/1500/2100/2800/3600/4500，Lv1 闯关新星→Lv10 闯关大师）；筛选 全部/最近7天/本月；报告库动作按钮（<60 重闯这一关 / 60-79 再次复习 / ≥80 查看完整报告）；星级（≥80 三颗 / 60-79 两颗 / <60 一颗）；微信登录本地开发用降级模式（`WECHAT_MOCK_LOGIN=true`，code 前缀 `dev_` 可模拟多用户）。

---

## 二、项目结构

```
ai_learn/
├── backend/                  # FastAPI 后端（Python 3.12）
│   ├── app/
│   │   ├── main.py           # 应用入口 + 统一异常处理 + /static 静态挂载
│   │   ├── core/             # 配置 / 异常 / 敏感词过滤 / JWT 鉴权 / MySQL 连接池 / 等级表
│   │   ├── models/           # Pydantic 领域模型（题库/报告/用户）
│   │   ├── prompts/          # 出题/报告 Prompt V1（K12 约束）
│   │   ├── llm/              # LangChain 工厂 / 出题链 / 报告链 / JSON 兜底 / Mock 数据
│   │   ├── services/         # 出题 / 报告 / 计分 / 用户 / 历史统计 / 题库校验 / 内存任务存储
│   │   ├── repositories/     # MySQL 仓储（用户 / 题库答题报告）
│   │   └── api/v1/routes/    # health / quiz / report / user 路由
│   ├── tests/                # 270 个测试（TDD，mock 大模型；RUN_MYSQL_TESTS=1 跑真实 MySQL 集成）
│   ├── scripts/              # e2e_smoke / e2e_user_system / e2e_avatar 端到端冒烟
│   ├── requirements.txt
│   └── .env                  # 环境变量（.env.example 为模板）
├── frontend/                 # Taro 4.1.11 + React 18 + TS + Sass
│   ├── src/pages/            # index(首页)/quiz(Tab)/report(Tab 报告库)/profile(Tab 学习档案)
│   │                         # gameplay(答题)/result(结算)/reportDetail(报告+历史回看)/stats(学习统计)
│   ├── src/components/       # Mascot(吉祥物闯闯)/TabBar/ReportView/Icon
│   ├── src/services/         # api.ts(请求封装+JWT+用户接口)/storage.ts(本地进度/报告/成长值)
│   ├── src/assets/icons/     # 15 个 PNG（tools/gen-icons.mjs 由 SVG 栅格化）
│   └── config/               # dev/prod 环境（API_BASE_URL）
├── 需求分析文档.txt
├── 方案设计文档.md
├── 01~05-*.html              # UI 原型（交付验收对照）
└── reference/                # 参考项目（只读）
```

---

## 三、后端运行

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env   # 或直接编辑 .env

# 用户系统需要 MySQL 8（docker 一键启动；数据目录在容器内，删容器即清空）
docker run -d --name chuangguan-mysql -e TZ=Asia/Shanghai `
  -e MYSQL_ROOT_PASSWORD=123456 -p 3306:3306 mysql:8 `
  --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci

# 运行测试（mock 大模型，不消耗 API 额度；MySQL 仓储集成测试需额外开关）
.\.venv\Scripts\python -m pytest              # 基础套件（265 passed / 15 skipped）
$env:RUN_MYSQL_TESTS='1'; .\.venv\Scripts\python -m pytest   # 含真实 MySQL 集成测试

# 一键验证真实 MySQL 仓储层（起容器 → 等就绪 → 跑集成测试 → 可选 e2e）
.\.venv\Scripts\python scripts\verify_mysql.py         # 需 Docker Desktop 已启动
.\.venv\Scripts\python scripts\verify_mysql.py --e2e   # 额外跑用户系统端到端

# 启动服务（自动建库建表；连不上 MySQL 不阻断启动，匿名模式仍可用）
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
# 接口文档：http://localhost:8000/docs
```

### .env 两种模式

| 模式 | 配置 | 用途 |
|---|---|---|
| 真实出题（**代码默认值**） | `LLM_MOCK=false` + 有效的 `DEEPSEEK_API_KEY` | 真实 AI 出题与报告 |
| Mock 模式（演示用，需手动开） | `LLM_MOCK=true`（无需 Key） | 首次联调 / 无 Key 演示完整闭环 |

> ⚠️ **注意默认值方向**：`app/core/config.py` 中 `llm_mock` 默认为 **`false`**，
> 即**不写 `LLM_MOCK` 就是真实调用 DeepSeek**，会消耗 API 额度。
> `.env.example` 里给出的也是 `LLM_MOCK=false`。想跑 Mock 演示必须显式写 `LLM_MOCK=true`。
> 另注意 `DEEPSEEK_MODEL` 需填**有效模型名**（`.env.example` 默认 `deepseek-chat`），
> 模型名无效时出题接口会返回 5001。

端到端冒烟（先启动服务）：

```powershell
.\.venv\Scripts\python scripts\e2e_smoke.py                # M1 核心闭环
.\.venv\Scripts\python scripts\e2e_user_system.py          # 用户系统全链路（登录/落库/回看/匿名回归）
.\.venv\Scripts\python scripts\e2e_avatar.py               # 头像上传链路
```

### 技术要点

- **LangChain 1.x**（langchain-openai 1.6.0 / langchain-core 1.6.0，2026 年最新大版本线）：`ChatOpenAI(base_url="https://api.deepseek.com")` 直连 DeepSeek OpenAI 兼容接口
- **JSON 五级保障**：Prompt 纯 JSON 约束 → markdown 代码块兼容提取 → Pydantic v2 校验 → 字段完整性校验（题数/选项/答案/题型/判断题 A正确B错误）→ 失败自动重试（3 次），绝不让脏数据到前端
- **服务端权威判分**：报告接口按 `selected_answers` 重判（不信任客户端 is_correct），正确率以本地统计覆盖 AI 输出
- **统一响应**：`{code, message, data}`；错误码 4000 内容安全 / 4001 参数 / 4002 任务不存在 / 5001 出题失败 / 5002 报告失败 / 5000 兜底

### API 清单

| 接口 | 方法 | 说明 |
|---|---|---|
| `/api/v1/health` | GET | 健康检查 |
| `/api/v1/quiz/generate` | POST | 同步出题（可选鉴权，登录则落库） |
| `/api/v1/quiz/generate/async` | POST | 异步出题，返回 task_id |
| `/api/v1/quiz/task/{task_id}` | GET | 轮询任务状态（pending/running/completed/failed） |
| `/api/v1/report/generate` | POST | 生成复盘报告（可选鉴权，登录则落答题记录/报告并累加 XP） |
| `/api/v1/user/login` | POST | 微信 code 换 openid + JWT（开发降级见 .env） |
| `/api/v1/user/profile` | GET/PUT | 用户档案（统计+等级）/ 更新昵称头像 |
| `/api/v1/user/avatar` | POST | 上传头像（chooseAvatar 临时文件 → 本地持久化） |
| `/api/v1/user/quizzes` | GET | 闯关历史分页（range=all/week/month、only_completed） |
| `/api/v1/user/quizzes/{quiz_id}` | GET | 单次闯关详情（题库+答题+报告，仅本人） |
| `/api/v1/user/stats` | GET | 学习统计（7 日正确率/知识点掌握度/薄弱点/连续打卡） |

错误码：4000 内容安全 / 4001 参数 / 4002 任务不存在 / 4004 记录不存在 / 4010 未登录 / 5001 出题失败 / 5002 报告失败 / 5000 兜底。

---

## 四、前端运行

```powershell
cd frontend
npm ci --legacy-peer-deps        # 或 npm install --legacy-peer-deps
npm run dev:weapp                # 本地联调：development 配置（API 指向 http://127.0.0.1:8000）+ watch
# 类型检查：npm run typecheck
# 生产构建：npm run build:weapp（注意！会注入 config/prod.ts 的生产域名占位符）
```

> ⚠️ **本地联调务必用 `npm run dev:weapp`，不要用 `build:weapp`**：
> Taro 按 NODE_ENV 注入 API 地址——`dev:weapp`（watch 模式）用 `config/dev.ts` 的 `http://127.0.0.1:8000/api/v1`；
> `build:weapp`（无 watch）会走 `config/prod.ts` 的占位域名 `https://your-domain.example.com`，
> 在开发者工具里表现为 `ERR_NAME_NOT_RESOLVED` /「网络开小差」。部署云托管前把 prod.ts 换成正式域名即可。

1. 打开**微信开发者工具** → 导入项目 → 目录选 `frontend/dist` → AppID 用测试号
2. 「详情 → 本地设置」勾选 **「不校验合法域名」**（否则 localhost 请求被拦截）
3. 后端地址：开发环境 `http://127.0.0.1:8000/api/v1`（`config/dev.ts`），生产环境改 `config/prod.ts`
4. 改了前端代码后 watch 会自动重编译，开发者工具里点「编译」即可看到最新效果

### 已知说明

- **标题字体**：`font-display` 类当前回退为系统粗体（未加载站酷快乐体）。原因：`wx.loadFontFace` 网络字体源会触发基础库的异步域名安全检查，域名未加入小程序 request 合法域名时控制台报 `webapi_getwxaasyncsecinfo:fail`。Phase 9 两种正式方案：① 字体文件放已备案 CDN + 加入合法域名白名单；② 字体子集化后以 base64 data URI 本地加载（免域名检查）
- **代理环境变量（Windows 常见坑）**：部分代理客户端会把 IPv6 回环写成方括号形式，得到 `NO_PROXY=localhost,127.0.0.1,::1,[::1]`。httpx 的 `URLPattern` 会把 `[::1]` 误当 `host:port` 解析并抛 `InvalidURL: Invalid port: ':1]'`；**异常发生在客户端构造阶段**，所以凡是走 httpx 的调用都会当场失败（微信登录，以及内部构造 httpx client 的 `ChatOpenAI` → 出题链/报告链全部不可用）。后端已在代码层做幂等规整（`app/core/proxy_env.py::sanitize_proxy_env`，在 `main` 启动、`get_chat_model`、`wx_code_to_openid` 三处调用）：方括号 IPv6 去括号、空条目与重复条目清理，真实代理地址原样保留，**无需修改机器环境变量**；如想从根上避免该写法，可把 `NO_PROXY` 改成 `localhost,127.0.0.1,::1`
- **图标**：`tools/gen-icons.mjs` 将 SVG 栅格化为 PNG（≤2KB 会被 webpack 内联为 base64，属正常现象）
- **npm 安装**：Taro 4.1.11 在 npm 11 下需 `--legacy-peer-deps`（peer 依赖校验变严所致）

---

## 五、UI 原型对照（逐帧验收）

| 原型文件 | 帧 | 实现位置 |
|---|---|---|
| 01 首页与出题流程 | 1 首页默认 / 2 输入态 / 3 AI 生成中 / 4 失败重试 | `pages/index` 四态（含示例主题卡、三步动效、进度条、失败双出口；登录后昵称/成长值/最近学过为真实数据） |
| 02 闯关答题流程 | 1~5 单选未答/答对/答错、多选、判断 | `pages/gameplay`（❤ 扣完仍可答、⭐+10/+15 浮动、讲解气泡 + 知识点标签、分段进度） |
| 03 通关与报告 | 1 结算 / 2 复盘报告 / 3 海报 | `pages/result` + `pages/reportDetail`；**海报页按确认不做**，报告页「分享给好友」走微信转发 |
| 04 个人学习后台 | 1 学习记录列表 / 2 数据统计 / 3 历史报告库 | `pages/profile`（档案+周统计+筛选+记录卡+分页+昵称头像编辑）、`pages/stats`（7 日柱图/掌握度/打卡/薄弱）、`pages/report`（报告库+动作按钮+分享）；统计入口在「我的」页顶部 |
| 05 扩展功能 | 全部 V2 前瞻 | 明确不进入 MVP（文件自标注） |

---

## 六、测试策略（TDD）

- 后端全部功能代码**先写失败测试再实现**：模型/统一响应/JSON 兜底/敏感词/计分/题库完整性校验 → 出题链/报告链（FakeListChatModel mock + 重试断言）→ 服务层与路由（httpx ASGI + 注入 mock）
- **用户系统（Phase 5）**：JWT 签发/解析/必选与可选鉴权依赖、等级表、微信登录（mock/真实/异常分支）、档案聚合、历史分页与 range 过滤、统计纯函数（掌握度/薄弱点/连续打卡/7 日补齐）、头像上传、出题/报告落库钩子与 XP 规则（含重复报告不重复计 XP）
- **真实 MySQL 仓储集成测试**（`RUN_MYSQL_TESTS=1`，独立测试库 `chuangguan_test`）：建表、用户 CRUD、upsert 语义、详情回查、分页/过滤/统计 SQL 与跨用户隔离
- **Prompt 契约测试**：固定输入断言输出 Schema 字段完整，防改 Prompt 回归
- **代理环境变量回归**（`tests/test_proxy_env.py`）：宿主 `NO_PROXY` 含方括号 IPv6 时
  httpx 会在构造阶段崩溃，这里固化行为（含一条刻意断言故障本身的用例）
- 真实 DeepSeek 联调：填入 Key 后 `LLM_MOCK=false` 重启，用 `/docs`、`scripts/e2e_user_system.py` 或小程序实测

### 当前验证状态（2026-09-30 实测）

| 项目 | 结果 |
|---|---|
| 基础套件 | ✅ `265 passed, 15 skipped, 3 errors` |
| 真实 DeepSeek 出题 | ✅ `scripts/verify_deepseek.py`（模型 `deepseek-v4-flash` 有效，返回结构合规） |
| 真实 DeepSeek 报告 | ✅ `scripts/verify_deepseek.py --report`（10.1s，在 20s 超时预算内） |
| 真实 MySQL 仓储集成测试 | ⚠️ **未验证**（15 个用例长期 skipped，开发机 MySQL 未启动）→ 见 `TODO.md` A1 |
| 微信开发者工具人工验收 | ⚠️ **未做** → 见 `TODO.md` A3 |
| 前端类型检查 | ✅ `npx tsc --noEmit` 通过 |

> `3 errors` 全部是 `test_avatar_api.py` 因沙箱/受限环境把 `TEMP` 重定向到不可写目录
> 导致的 `tmp_path` 失败，**非代码缺陷**，普通终端下通过。
> 15 个 skipped 是等待 `RUN_MYSQL_TESTS=1` 的 MySQL 集成测试。

> 未完成事项与技术债统一登记在 **`TODO.md`**（按 🔴 阻断上线 / 🟠 上线前必做 / 🟡 应做 分级）。

---

## 七、后续阶段（按方案设计第 10 章）

| 阶段 | 内容 |
|---|---|
| ~~Phase 5~~ | ✅ 已完成：MySQL 4 表 + 微信静默登录 + 个人学习后台（原型 04）+ 历史回看 + 头像上传 |
| Phase 6–7 | Tavily 联网搜索（LangGraph ReAct）+ 文档上传/RAG 知识库（kb_documents 表、Chroma、百炼 Embedding） |
| Phase 8–9 | AI 生图配图 + COS + 分享海报（Canvas）+ 视觉打磨 |
| Phase 10 | 微信云托管部署 + 类目资质 + ICP 备案 + 审核发布（生产注意：`WECHAT_MOCK_LOGIN=false`、强随机 `JWT_SECRET`、头像建议换对象存储） |

> 合规提醒（K12）：上线前需完成「深度合成 - AI 问答」类目申请、AI 生成内容标识、隐私政策与未成年人保护说明（详见方案设计第 11 章）。
