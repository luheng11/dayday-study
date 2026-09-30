"""一键验证真实 MySQL 仓储层（Docker 起库 → 跑集成测试 → 全链路冒烟）

用法（在 backend 目录下）：
    .\\.venv\\Scripts\\python scripts\\verify_mysql.py            # 起库 + 跑集成测试
    .\\.venv\\Scripts\\python scripts\\verify_mysql.py --e2e      # 额外跑用户系统端到端冒烟
    .\\.venv\\Scripts\\python scripts\\verify_mysql.py --no-start # 库已在跑，只跑测试

为什么需要这个脚本：
    tests/test_repositories_mysql.py 的 15 个用例默认被跳过（需要 RUN_MYSQL_TESTS=1），
    也就是建表 / 用户 CRUD / upsert 语义 / 分页与 range 过滤 / 跨用户隔离这些真实 SQL
    平时根本没被执行过。手动串起「起容器 → 等就绪 → 开关环境变量 → 跑测试 → 起服务 →
    跑 e2e」很容易漏步骤，这里一次做完并逐步打印结果。

注意：集成测试会用 MYSQL_TEST_DATABASE（默认 chuangguan_test）这个独立库，
      不会碰开发库 chuangguan_xuetang。
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CONTAINER = "chuangguan-mysql"
MYSQL_ROOT_PASSWORD = os.environ.get("MYSQL_PASSWORD", "123456")

CREATE_CMD = [
    "docker", "run", "-d",
    "--name", CONTAINER,
    "-e", "TZ=Asia/Shanghai",
    "-e", f"MYSQL_ROOT_PASSWORD={MYSQL_ROOT_PASSWORD}",
    "-p", "3306:3306",
    "mysql:8",
    "--character-set-server=utf8mb4",
    "--collation-server=utf8mb4_unicode_ci",
]


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=BACKEND_DIR, text=True, encoding="utf-8",
                          errors="replace", **kwargs)


def docker_available() -> bool:
    try:
        r = run(["docker", "info", "--format", "{{.ServerVersion}}"],
                capture_output=True, timeout=30)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return r.returncode == 0


def container_exists() -> bool:
    r = run(["docker", "ps", "-a", "--filter", f"name=^/{CONTAINER}$",
             "--format", "{{.Names}}"], capture_output=True)
    return CONTAINER in (r.stdout or "")


def container_running() -> bool:
    r = run(["docker", "ps", "--filter", f"name=^/{CONTAINER}$",
             "--format", "{{.Names}}"], capture_output=True)
    return CONTAINER in (r.stdout or "")


def start_mysql() -> bool:
    if container_running():
        print(f"[1/4] 容器 {CONTAINER} 已在运行，跳过创建")
    elif container_exists():
        print(f"[1/4] 启动已存在的容器 {CONTAINER} …")
        if run(["docker", "start", CONTAINER], capture_output=True).returncode != 0:
            print("      启动失败")
            return False
    else:
        print(f"[1/4] 创建并启动容器 {CONTAINER} …")
        if run(CREATE_CMD, capture_output=True).returncode != 0:
            print("      创建失败（端口 3306 被占用？）")
            return False

    print("[2/4] 等待 MySQL 就绪（最多 120s）…")
    for i in range(24):
        r = run(["docker", "exec", CONTAINER, "mysqladmin", "ping",
                 "-h", "127.0.0.1", f"-p{MYSQL_ROOT_PASSWORD}"],
                capture_output=True)
        if r.returncode == 0 and "alive" in (r.stdout or ""):
            print(f"      就绪（{(i + 1) * 5}s）")
            return True
        time.sleep(5)
    print("      超时：MySQL 未就绪，用 docker logs 查看")
    return False


def run_tests() -> bool:
    print("[3/4] 运行真实 MySQL 集成测试（RUN_MYSQL_TESTS=1）…")
    env = {**os.environ, "RUN_MYSQL_TESTS": "1"}
    r = run([sys.executable, "-m", "pytest", "tests/test_repositories_mysql.py",
             "-v", "-p", "no:cacheprovider"], env=env, capture_output=True)
    print(r.stdout[-6000:] if r.stdout else "")
    if r.stderr:
        print(r.stderr[-2000:])
    return r.returncode == 0


def run_e2e() -> bool:
    print("[4/4] 用户系统端到端冒烟（需服务已在 :8000 运行）…")
    r = run([sys.executable, "scripts/e2e_user_system.py"], capture_output=True)
    print(r.stdout[-4000:] if r.stdout else "")
    if r.stderr:
        print(r.stderr[-2000:])
    return r.returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-start", action="store_true", help="库已在跑，只跑测试")
    ap.add_argument("--e2e", action="store_true", help="额外跑用户系统 e2e 冒烟")
    args = ap.parse_args()

    if not args.no_start:
        if not docker_available():
            print("❌ 连不上 Docker daemon。先启动 Docker Desktop，再重跑本脚本。")
            print("   （若在受限沙箱/无桌面会话的环境里，daemon 起不来，请在普通终端执行）")
            return 2
        if not start_mysql():
            return 2
    else:
        print("[1-2/4] 跳过起库（--no-start）")

    ok = run_tests()
    print("\n" + "=" * 60)
    print("MySQL 集成测试：" + ("✅ 通过" if ok else "❌ 失败"))

    if args.e2e:
        e2e_ok = run_e2e()
        print("用户系统 e2e：" + ("✅ 通过" if e2e_ok else "❌ 失败"))
        ok = ok and e2e_ok

    if not ok:
        print("\n排查提示：确认 .env 的 MYSQL_HOST/PORT/USER/PASSWORD 与容器一致")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
