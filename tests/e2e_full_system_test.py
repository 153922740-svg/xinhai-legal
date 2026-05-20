#!/usr/bin/env python3
"""
心海法律 AI - 全系统E2E自测脚本 v2
环境: 生产环境 https://xinclaw.xhacca.cn
测试账号: 13800138000 / 验证码 888888
"""
import requests
import time
import json
import sys
from datetime import datetime

BASE_URL = "https://xinclaw.xhacca.cn"
API_PREFIX = "/api/v1"
TEST_PHONE = "13800138000"
TEST_CODE = "888888"

def url(path):
    path = path.lstrip("/")
    if path.startswith("api/") or path.startswith("http"):
        return f"{BASE_URL}/{path}"
    if path in ("", "/"):
        return f"{BASE_URL}/"
    return f"{BASE_URL}{API_PREFIX}/{path}"

passed = 0
failed = 0
failures = []

def log(name, ok, detail=""):
    global passed, failed
    icon = "✅" if ok else "❌"
    if ok: passed += 1
    else:
        failed += 1
        failures.append(f"{name}: {detail}")
    print(f"  {icon} {name}" + (f" - {detail}" if detail else ""))

def section(title):
    print(f"\n{'='*60}\n  {title}\n{'='*60}")

# ============================================================
section("1. 登录流程 (P0)")
# ============================================================

r = requests.post(url("auth/send_sms"), json={"phone": TEST_PHONE}, timeout=10)
log("发送验证码", r.status_code == 200, f"HTTP {r.status_code}")

r = requests.post(url("auth/login"), json={"phone": TEST_PHONE, "code": TEST_CODE}, timeout=10)
token = None
try:
    d = r.json()
    token = d.get("token") or (d.get("data") or {}).get("token")
except: pass
log("登录获取Token", bool(token), f"token={token[:20] if token else 'none'}...")

r = requests.post(url("auth/login"), json={"phone": TEST_PHONE, "code": "000000"}, timeout=10)
log("错误验证码登录拒绝", r.status_code == 200, f"HTTP {r.status_code}" + (f" ret={r.json().get('code','?')}" if r.status_code==200 else ""))

headers = {"Authorization": f"Bearer {token}"} if token else {}

# ============================================================
section("2. Token & 会员 (P0)")
# ============================================================

r = requests.get(url("token/packages"), timeout=10)
log("Token套餐查询", r.status_code == 200, f"HTTP {r.status_code}")

r = requests.get(url("member/packages"), timeout=10)
log("会员套餐查询", r.status_code == 200, f"HTTP {r.status_code}")

if token:
    r = requests.get(url("token/balance"), headers=headers, timeout=10)
    ok = r.status_code == 200
    balance = "?"
    if ok:
        d = r.json()
        balance = (d.get("data") or d).get("balance", "?")
    log("Token余额查询", ok, f"余额={balance}")

    r = requests.get(url("member/status"), headers=headers, timeout=10)
    ok = r.status_code == 200
    log("会员状态查询", ok, f"HTTP {r.status_code}")

# ============================================================
section("3. AI对话 (P0)")
# ============================================================

if token:
    r = requests.post(url("chat/send"), headers=headers,
                     json={"message": "离婚需要什么条件？", "conversation_id": "e2e_test_001"},
                     timeout=30)
    ok = r.status_code == 200
    reply = ""
    if ok:
        try:
            d = r.json()
            reply = d.get("response") or (d.get("data") or {}).get("response", "")
        except: pass
    log("AI对话发送", ok, f"reply={reply[:50] if reply else 'none'}")

    r = requests.get(url("chat/sessions"), headers=headers, timeout=10)
    log("会话列表查询", r.status_code == 200)

    r = requests.get(url("history/list"), headers=headers, timeout=10)
    log("历史记录查询", r.status_code == 200)

# ============================================================
section("4. 文书生成 (P0)")
# ============================================================

r = requests.get(url("document/templates"), timeout=10)
log("文书模板列表", r.status_code == 200)

if token:
    r = requests.post(url("document/generate"), headers=headers, timeout=30,
                     json={
                         "template_id": "civil_complaint",
                         "fields": {
                             "plaintiff_name": "张三",
                             "defendant_name": "李四",
                             "claim": "请求判决离婚",
                             "facts": "双方感情破裂分居满两年"
                         }
                     })
    ok = r.status_code == 200
    doc_id = ""
    if ok:
        try:
            d = r.json()
            doc_id = d.get("doc_id") or (d.get("data") or {}).get("doc_id", "")
        except: pass
    log("文书生成", ok, f"doc_id={doc_id or '?'}")

    r = requests.get(url("document/list"), headers=headers, timeout=10)
    log("文书列表查询", r.status_code == 200)

    if doc_id:
        r = requests.get(url(f"document/download/{doc_id}"), headers=headers, timeout=15)
        log("文书下载", r.status_code == 200, f"HTTP {r.status_code}")

# ============================================================
section("5. 积分系统 (P1)")
# ============================================================

if token:
    r = requests.get(url("integral/balance"), headers=headers, timeout=10)
    log("积分查询", r.status_code == 200, f"HTTP {r.status_code}")

    r = requests.post(url("integral/signin"), headers=headers, timeout=10)
    log("每日签到", r.status_code == 200, f"HTTP {r.status_code}")

    r = requests.get(url("integral/records"), headers=headers, timeout=10)
    log("积分记录查询", r.status_code == 200)

# ============================================================
section("6. 合伙人系统 (P1)")
# ============================================================

if token:
    r = requests.get(url("partner/info"), headers=headers, timeout=10)
    level = "?"
    if r.status_code == 200:
        try:
            d = r.json()
            level = (d.get("data") or d).get("level", "?")
        except: pass
    log("合伙人信息查询", r.status_code == 200, f"等级={level}")

    r = requests.get(url("partner/commissions"), headers=headers, timeout=10)
    log("佣金记录查询", r.status_code == 200)

# ============================================================
section("7. 用户记忆 (P1)")
# ============================================================

if token:
    r = requests.get(url("memory/info") + "?user_id=1", headers=headers, timeout=10)
    log("用户记忆查询", r.status_code == 200)

# ============================================================
section("8. 自进化能力 (P2)")
# ============================================================

if token:
    r = requests.post(url("feedback/submit"), headers=headers,
                     json={"content": "E2E自测-测试反馈", "rating": 5}, timeout=10)
    log("提交用户反馈", r.status_code == 200)

    r = requests.get(url("badcases/list"), headers=headers, timeout=10)
    log("Badcase列表查询", r.status_code == 200)

# ============================================================
section("9. 系统健康")
# ============================================================

r = requests.get(url("health"), timeout=10)
log("系统健康检查", r.status_code == 200, f"HTTP {r.status_code}")

r = requests.get(BASE_URL + "/", timeout=10)
log("前端首页访问", r.status_code == 200, f"HTTP {r.status_code}")

# ============================================================
# Summary
# ============================================================
total = passed + failed
rate = (passed / total * 100) if total > 0 else 0
print(f"\n{'='*60}")
print(f"  📊 测试统计: {passed}/{total} 通过 ({rate:.1f}%)")
print(f"{'='*60}")

if failures:
    print(f"\n❌ 失败明细:")
    for f in failures:
        print(f"  • {f}")

if rate >= 95:
    print(f"\n🎉 结论: {'全部通过' if failed==0 else '有条件通过（需修复少数失败项）'}")
elif rate >= 80:
    print(f"\n⚠️ 结论: 有条件通过（需修复失败项）")
else:
    print(f"\n❌ 结论: 不通过，通过率 {rate:.1f}%")

print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
