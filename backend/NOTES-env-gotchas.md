# 环境坑与排障记录（开发笔记）

本文件记录**宿主环境相关**、容易反复踩的坑与排查结论。
（意图被未来会话检索：搜 `NO_PROXY`、`httpx`、`InvalidURL`、`pytest` 即可命中。）

---

## 1. NO_PROXY 里的方括号 IPv6 会让 httpx 在「构造阶段」崩溃

**现象**：6 个后端测试失败，报

```
httpx.InvalidURL: Invalid port: ':1]'
```

- `tests/test_langchain_factory.py` ×3（`TestGetChatModel` 全部）
- `tests/test_user_service.py` ×3（`TestWxCodeToOpenid.test_real_call_*`）

**根因**：宿主环境变量为

```
NO_PROXY=localhost,127.0.0.1,::1,[::1]
```

httpx 0.28.1 与 httpx2 2.12.0 都会把 `NO_PROXY` 的每一项当作 URL pattern 解析，
方括号 IPv6 字面量 `[::1]` 被误解析成 `host:port`，于是端口成了 `:1]`。
栈顶在 `httpx/_urlparse.py::normalize_port`，由 `httpx/_utils.py` 的
`URLPattern(key)` 触发。

实测只有**方括号形式**有毒（`NO_PROXY` 才有这个问题，`HTTP_PROXY` 用方括号没事）：

| NO_PROXY 取值 | httpx.Client() |
|---|---|
| `localhost,127.0.0.1,::1` | ✅ |
| `localhost,127.0.0.1,::1,[::1]` | ❌ |
| `[2001:db8::1]` | ❌ |
| `""` / `"   "` / `"localhost,,"` / `"*"` | ✅ |

**致命点**：异常发生在**客户端构造阶段**，所以不是某个请求失败，而是所有走 httpx
的调用当场全灭——`httpx.Client()`、`httpx.AsyncClient()`，以及内部会创建 httpx
client 的 `langchain_openai.ChatOpenAI(...)`。对应业务链路：微信登录、出题链、报告链。

**修复（代码层，不改机器环境变量）**：
`backend/app/core/proxy_env.py::sanitize_proxy_env()`，幂等：

- 方括号 IPv6 去括号（`[::1]` → `::1`），并按出现顺序去重
- 清掉空的代理条目（`HTTP_PROXY=""` 之类无意义且干扰库判定）
- 真实代理地址原样保留（企业代理场景不受影响）
- 不存在的变量不会被凭空创建

接入点（都在构造 httpx client 之前）：

1. `app/main.py` 模块级（进程启动即规整）
2. `app/llm/langchain_factory.py::get_chat_model`
3. `app/services/user_service.py::wx_code_to_openid`

测试：`backend/tests/test_proxy_env.py`（12 个）。其中一条**刻意固化故障现象**
（`pytest.raises(httpx.InvalidURL)`），以防上游日后修复解析导致测试失真。

**效果**：后端 `247 passed / 6 failed` → `265 passed / 0 failed`。

---

## 1b. 推送 GitHub 被拒：现有 SSH key 是**只读 deploy key**

推送到 `git@github.com:luheng11/dayday-study.git` 时报：

```
ERROR: Permission to luheng11/dayday-study.git denied to deploy key
```

**根因**：`C:\Users\14314\.ssh\` 下有两个 key，身份完全不同：

| key | 在 GitHub 上的身份 | 能否 push |
|---|---|---|
| `id_ed25519` | **未注册**（`ssh -T` 报 `Permission denied (publickey)`） | ❌ |
| `id_ed25519_github` | **deploy key**，且只绑在 BidLens 仓库上 | ❌ 只读，且仅限那一仓库 |

判断技巧：`ssh -T git@github.com` 的欢迎语如果是
`Hi <owner>/<repo>! You've successfully authenticated...`，说明用的是 **deploy key**
（仓库级、可通过 "Allow write access" 控制读写）；
如果是 `Hi <username>!`，那才是**账号级** key，可以推任意仓库。

另外 `~/.ssh/config` 里**没有 github.com 的 Host 条目**，所以默认不会用
`id_ed25519_github`，必须显式 `-i` 或补 config。

**解法（二选一，都需要在 GitHub 网页端操作）**：
1. 把 `id_ed25519_github.pub` 加到 **账号级** SSH keys
   （Settings → SSH and GPG keys → New SSH key，类型选 Authentication Key）。
   加完后同一个 key 就能推任意仓库。
2. 或给 `dayday-study` 单独加一个 **勾选 "Allow write access"** 的 deploy key。

**先查身份再重试**（本机已配好 `-i` 时可直接用）：
```powershell
ssh -T git@github.com          # 期望看到 "Hi luheng11!"（账号级）
git push -u origin main
```

**顺带**：本机**没有** `gh` CLI、**没有** credential helper、**没有** 任何
`GITHUB_TOKEN`/`GH_TOKEN`，所以无法走 HTTPS 令牌方式，也没有可用的交互式登录途径。

---

## 2. 测试数量口径：15 skipped + 3 errors 分别是什么

```
265 passed, 15 skipped, 3 errors
```

- **15 skipped**：`tests/test_repositories_mysql.py` 的真实 MySQL 集成测试，由
  `RUN_MYSQL_TESTS=1` 开关控制；需要 Docker 里的 MySQL 8 在跑。未开启时跳过属正常。
- **3 errors**：`tests/test_avatar_api.py` 报
  `PermissionError: [WinError 5] ...\Temp\dsh-*\pytest-of-14314`。
  这是 **DSH 沙箱**把 `TEMP`/`TMP` 重定向到不可写的按进程临时目录导致的
  `tmp_path` fixture 失败，**不是代码问题**，在普通终端下会通过。

---

## 3. 沙箱下的操作注意（仅影响在 DSH 沙箱内干活时）

- `git checkout -- <file>` **不可靠**：本次排查中它没有把文件真正写回磁盘，
  导致一度误判「去掉 sanitize 调用测试仍通过」。改用 Python
  `Path.write_text(..., newline="\n")` 写回则生效。
- PowerShell `Set-Content -Encoding UTF8` 会写 **BOM**，会污染仓库源码文件，别用。
- PowerShell **不支持 heredoc**（`<<'EOF'`）。提交信息先写文件再 `git commit -F <file>`。
- `Get-ChildItem env:` 在本环境会报 `An item with the same key has already been added`，
  直接读 `$env:NAME` 即可。
- 想验证「修复是否真的必需」时，用**绝对路径**做文件改写并**单独跑目标测试文件**；
  在同一次 pytest 进程里跑多个文件会因全局 `os.environ` 被前面的测试改过而串味。
