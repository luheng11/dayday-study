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
- ✅ 4 Tab（首页 / 闯关 / 报告 / 我的）；闯关 Tab 续答、报告 Tab 最近报告
- ✅ 后端：health / quiz 同步 / quiz 异步+轮询 / report 四类接口，TDD 全量测试
- ❌ 本版本不做：分享海报页（已确认）、原型 05 扩展功能（V2 前瞻）、「我的」Tab 内容页（Phase 5）、MySQL/微信登录、联网搜索/RAG/AI 生图

**已确认的关键决策**：输入上限 2000 字；❤ 仅氛围不惩罚（扣完仍可答题）；分值 单选10/多选15/判断10⭐；3 题=1:1:1、5 题=3:1:1 配比；难度 入门/适中/挑战→easy/medium/hard（默认适中）；未登录隐藏「最近学过」、成长值从 0 起。

---

## 二、项目结构

```
ai_learn/
├── backend/                  # FastAPI 后端（Python 3.12）
│   ├── app/
│   │   ├── main.py           # 应用入口 + 统一异常处理
│   │   ├── core/             # 配置 / 异常 / 敏感词过滤
│   │   ├── models/           # Pydantic 领域模型（与方案设计 6.1 一致）
│   │   ├── prompts/          # 出题/报告 Prompt V1（K12 约束）
│   │   ├── llm/              # LangChain 工厂 / 出题链 / 报告链 / JSON 兜底 / Mock 数据
│   │   ├── services/         # 出题服务 / 报告服务 / 计分 / 题库校验 / 内存任务存储
│   │   └── api/v1/routes/    # health / quiz / report 路由
│   ├── tests/                # 167 个测试（TDD，mock 大模型，不耗 API 额度）
│   ├── scripts/e2e_smoke.py  # 端到端冒烟（模拟小程序完整调用链）
│   ├── requirements.txt
│   └── .env                  # 环境变量（.env.example 为模板）
├── frontend/                 # Taro 4.1.11 + React 18 + TS + Sass
│   ├── src/pages/            # index(首页)/quiz(Tab)/report(Tab)/profile(Tab)
│   │                         # gameplay(答题)/result(结算)/reportDetail(报告)
│   ├── src/components/       # Mascot(吉祥物闯闯)/TabBar/ReportView/Icon
│   ├── src/services/         # api.ts(请求封装)/storage.ts(本地进度/报告/成长值)
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

# 运行测试（mock 大模型，不消耗 API 额度）
.\.venv\Scripts\python -m pytest          # 167 passed

# 启动服务
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
# 接口文档：http://localhost:8000/docs
```

### .env 两种模式

| 模式 | 配置 | 用途 |
|---|---|---|
| Mock 模式（默认已配好） | `LLM_MOCK=true`（无需 Key） | 首次联调 / 演示完整闭环 |
| 真实出题 | `LLM_MOCK=false` + `DEEPSEEK_API_KEY=你的Key` | 真实 AI 出题与报告 |

端到端冒烟（先启动服务）：

```powershell
.\.venv\Scripts\python scripts\e2e_smoke.py
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
| `/api/v1/quiz/generate` | POST | 同步出题（调试用） |
| `/api/v1/quiz/generate/async` | POST | 异步出题，返回 task_id |
| `/api/v1/quiz/task/{task_id}` | GET | 轮询任务状态（pending/running/completed/failed） |
| `/api/v1/report/generate` | POST | 生成复盘报告 |

---

## 四、前端运行

```powershell
cd frontend
npm ci --legacy-peer-deps        # 或 npm install --legacy-peer-deps
npm run dev:weapp                # 编译到 dist/ 并监听
# 生产构建：npm run build:weapp
# 类型检查：npm run typecheck
```

1. 打开**微信开发者工具** → 导入项目 → 目录选 `frontend/dist` → AppID 用测试号
2. 「详情 → 本地设置」勾选 **「不校验合法域名」**（否则 localhost 请求被拦截）
3. 后端地址：开发环境 `http://127.0.0.1:8000/api/v1`（`config/dev.ts`），生产环境改 `config/prod.ts`

### 已知说明

- **标题字体**：站酷快乐体通过 `wx.loadFontFace` 从 jsDelivr CDN 加载，加载失败自动回退系统字体（不影响功能）；正式上线需将该字体文件放入合法域名/本地包
- **图标**：`tools/gen-icons.mjs` 将 SVG 栅格化为 PNG（≤2KB 会被 webpack 内联为 base64，属正常现象）
- **npm 安装**：Taro 4.1.11 在 npm 11 下需 `--legacy-peer-deps`（peer 依赖校验变严所致）

---

## 五、UI 原型对照（逐帧验收）

| 原型文件 | 帧 | 实现位置 |
|---|---|---|
| 01 首页与出题流程 | 1 首页默认 / 2 输入态 / 3 AI 生成中 / 4 失败重试 | `pages/index` 四态（含示例主题卡、三步动效、进度条、失败双出口） |
| 02 闯关答题流程 | 1~5 单选未答/答对/答错、多选、判断 | `pages/gameplay`（❤ 扣完仍可答、⭐+10/+15 浮动、讲解气泡 + 知识点标签、分段进度） |
| 03 通关与报告 | 1 结算 / 2 复盘报告 / 3 海报 | `pages/result` + `pages/reportDetail`；**海报页按确认不做**，报告页「分享给好友」走微信转发 |
| 04 个人学习后台 | 1~3 档案/统计/报告库 | Phase 5 交付；本轮「我的」Tab 为空态页（M1 范围外） |
| 05 扩展功能 | 全部 V2 前瞻 | 明确不进入 MVP（文件自标注） |

---

## 六、测试策略（TDD）

- 后端全部功能代码**先写失败测试再实现**：模型/统一响应/JSON 兜底/敏感词/计分/题库完整性校验 → 出题链/报告链（FakeListChatModel mock + 重试断言）→ 服务层与路由（httpx ASGI + 注入 mock）
- **Prompt 契约测试**：固定输入断言输出 Schema 字段完整，防改 Prompt 回归
- 真实 DeepSeek 联调：填入 Key 后 `LLM_MOCK=false` 重启，用 `/docs` 或小程序实测

---

## 七、后续阶段（按方案设计第 10 章）

| 阶段 | 内容 |
|---|---|
| Phase 5 | MySQL 7 表 + 微信静默登录（jscode2session+JWT）+ 个人学习后台（原型 04） |
| Phase 6–7 | Tavily 联网搜索（LangGraph ReAct）+ 文档上传/RAG 知识库 |
| Phase 8–9 | AI 生图配图 + COS + 分享海报（Canvas）+ 视觉打磨 |
| Phase 10 | 微信云托管部署 + 类目资质 + ICP 备案 + 审核发布 |

> 合规提醒（K12）：上线前需完成「深度合成 - AI 问答」类目申请、AI 生成内容标识、隐私政策与未成年人保护说明（详见方案设计第 11 章）。
