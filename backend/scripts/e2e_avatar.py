"""头像上传实测：登录 → 上传 PNG → 校验返回 URL 可访问（静态服务）"""
import httpx

BASE = "http://127.0.0.1:8000"

# 最小合法 PNG（1x1 透明像素）
PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c626001000000ffff03000006000557bfabd40000000049454e44ae426082"
)

with httpx.Client(timeout=30, trust_env=False) as client:
    login = client.post(f"{BASE}/api/v1/user/login", json={"code": "dev_openid_e2e"}).json()
    token = login["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(
        f"{BASE}/api/v1/user/avatar",
        headers=headers,
        files={"file": ("avatar.png", PNG_BYTES, "image/png")},
    )
    resp.raise_for_status()
    avatar_url = resp.json()["data"]["avatar_url"]
    print(f"1. AVATAR UPLOAD OK: {avatar_url}")

    # 静态访问
    r = client.get(avatar_url)
    r.raise_for_status()
    print(f"2. STATIC ACCESS OK: HTTP {r.status_code} bytes={len(r.content)}")

    # 档案已更新
    profile = client.get(f"{BASE}/api/v1/user/profile", headers=headers).json()["data"]
    assert profile["avatar_url"] == avatar_url
    print(f"3. PROFILE avatar_url UPDATED OK: {profile['avatar_url']}")

    # 非图片拒绝
    bad = client.post(
        f"{BASE}/api/v1/user/avatar",
        headers=headers,
        files={"file": ("a.txt", b"hello", "text/plain")},
    )
    assert bad.status_code == 400 and bad.json()["code"] == 4001
    print("4. NON-IMAGE REJECTED: 400/4001")

print("========== AVATAR ACCEPTANCE PASSED ==========")
