#!/usr/bin/env python3
"""
全系统E2E测试脚本 — 通过域名 https://xinclaw.xhacca.cn 测试所有API
"""
import requests
import json
import sys
import time

BASE = "https://xinclaw.xhacca.cn/api/v1"
USER_ID = 4

results = []  # list of (method, path, status_or_error, passed)

def req(method, path, **kwargs):
    url = f"{BASE}{path}"
    try:
        r = requests.request(method, url, timeout=15, **kwargs)
        status = r.status_code
        try:
            data = r.json()
        except Exception:
            data = {}
        # 只要不报 500 就算通过
        if status < 500:
            return status, data, True
        else:
            return status, data, False
    except requests.exceptions.Timeout:
        return "TIMEOUT", {}, False
    except requests.exceptions.ConnectionError as e:
        return f"CONN_ERR({e})", {}, False
    except Exception as e:
        return str(e), {}, False

def record(method, path, status, passed):
    tag = "✅" if passed else "❌"
    print(f"{tag} {method:4s} {path} → {status}")
    results.append((method, path, status, passed))

def test_auth():
    """P0 - 认证模块"""
    print("\n========== P0 - 认证模块 ==========")
    # 1. send_sms
    status, data, ok = req("POST", "/auth/send_sms", json={"phone": "13800000000"})
    record("POST", "/auth/send_sms", status, ok)
    # 2. login (可能验证码错误，但不应该500)
    status, data, ok = req("POST", "/auth/login", json={"phone": "13800000000", "code": "000000"})
    record("POST", "/auth/login", status, ok)
    # 3. wx_login
    status, data, ok = req("POST", "/auth/wx_login", json={"code": "test_wx_code_e2e"})
    record("POST", "/auth/wx_login", status, ok)
    # 4. me — 带token (如果没有有效token，预期400，但不500)
    fake_token = "Bearer test_e2e_token_dummy"
    status, data, ok = req("GET", "/auth/me", headers={"Authorization": fake_token})
    record("GET", "/auth/me", status, ok)

def test_chat():
    """P0 - AI对话"""
    print("\n========== P0 - AI对话 ==========")
    status, data, ok = req("POST", "/chat/send", json={"message": "你好", "user_id": USER_ID})
    record("POST", "/chat/send", status, ok)
    status, data, ok = req("GET", "/chat/history", params={"session_id": "test_e2e"})
    record("GET", "/chat/history", status, ok)

def test_token():
    """P0 - Token"""
    print("\n========== P0 - Token ==========")
    status, data, ok = req("GET", "/token/packages")
    record("GET", "/token/packages", status, ok)
    status, data, ok = req("POST", "/token/balance", json={"user_id": USER_ID})
    record("POST", "/token/balance", status, ok)
    status, data, ok = req("POST", "/token/consume", json={"user_id": USER_ID, "amount": 1})
    record("POST", "/token/consume", status, ok)

def test_member():
    """P0 - 会员"""
    print("\n========== P0 - 会员 ==========")
    status, data, ok = req("GET", "/member/packages")
    record("GET", "/member/packages", status, ok)
    status, data, ok = req("POST", "/member/status", json={"user_id": USER_ID})
    record("POST", "/member/status", status, ok)
    status, data, ok = req("POST", "/member/order", json={"user_id": USER_ID, "plan": "basic_monthly"})
    record("POST", "/member/order", status, ok)

def test_document():
    """P1 - 文书"""
    print("\n========== P1 - 文书 ==========")
    status, data, ok = req("GET", "/document/templates")
    record("GET", "/document/templates", status, ok)
    status, data, ok = req("POST", "/document/generate", json={"user_id": USER_ID, "template_type": "test"})
    record("POST", "/document/generate", status, ok)

def test_integral():
    """P1 - 积分"""
    print("\n========== P1 - 积分 ==========")
    status, data, ok = req("GET", "/integral/balance", params={"user_id": USER_ID})
    record("GET", "/integral/balance", status, ok)
    status, data, ok = req("POST", "/integral/sign", json={"user_id": USER_ID})
    record("POST", "/integral/sign", status, ok)
    status, data, ok = req("GET", "/integral/records", params={"user_id": USER_ID})
    record("GET", "/integral/records", status, ok)
    status, data, ok = req("GET", "/integral/tasks")
    record("GET", "/integral/tasks", status, ok)
    status, data, ok = req("GET", "/integral/shop")
    record("GET", "/integral/shop", status, ok)

def test_partner():
    """P1 - 合伙人"""
    print("\n========== P1 - 合伙人 ==========")
    status, data, ok = req("GET", "/partner/level", params={"user_id": USER_ID})
    record("GET", "/partner/level", status, ok)
    status, data, ok = req("GET", "/partner/status", params={"user_id": USER_ID})
    record("GET", "/partner/status", status, ok)

def test_payment():
    """P1 - 支付"""
    print("\n========== P1 - 支付 ==========")
    status, data, ok = req("GET", "/payment/health")
    record("GET", "/payment/health", status, ok)

def test_user_memory():
    """P2 - 用户记忆"""
    print("\n========== P2 - 用户记忆 ==========")
    status, data, ok = req("GET", "/user/memory", params={"user_id": USER_ID})
    record("GET", "/user/memory", status, ok)
    status, data, ok = req("POST", "/user/memory", json={"user_id": USER_ID, "key": "test", "value": "e2e"})
    record("POST", "/user/memory", status, ok)

def test_evolution():
    """P2 - 自进化"""
    print("\n========== P2 - 自进化 ==========")
    status, data, ok = req("GET", "/evolution/stats")
    record("GET", "/evolution/stats", status, ok)
    status, data, ok = req("POST", "/feedback/submit", json={"user_id": USER_ID, "content": "E2E test feedback"})
    record("POST", "/feedback/submit", status, ok)
    status, data, ok = req("GET", "/badcases/list")
    record("GET", "/badcases/list", status, ok)

def test_dashboard():
    """P2 - 数据看板"""
    print("\n========== P2 - 数据看板 ==========")
    status, data, ok = req("GET", "/dashboard/overview")
    record("GET", "/dashboard/overview", status, ok)

def test_recommend():
    """P2 - 推荐系统"""
    print("\n========== P2 - 推荐系统 ==========")
    status, data, ok = req("POST", "/recommend/user", json={"user_id": USER_ID})
    record("POST", "/recommend/user", status, ok)

def test_ai_validated():
    """P3 - 三模型验证"""
    print("\n========== P3 - 三模型验证 ==========")
    status, data, ok = req("POST", "/ai/chat/validated", json={"message": "你好", "user_id": USER_ID})
    record("POST", "/ai/chat/validated", status, ok)
    status, data, ok = req("POST", "/model/stats")
    record("POST", "/model/stats", status, ok)


def main():
    print("=" * 70)
    print("全系统 E2E 测试 — xinclaw.xhacca.cn")
    print("=" * 70)
    print(f"测试用户ID: {USER_ID}")

    # 按分组顺序执行
    test_auth()
    test_chat()
    test_token()
    test_member()
    test_document()
    test_integral()
    test_partner()
    test_payment()
    test_user_memory()
    test_evolution()
    test_dashboard()
    test_recommend()
    test_ai_validated()

    # 汇总
    print("\n" + "=" * 70)
    print("📊 测试汇总")
    print("=" * 70)
    total = len(results)
    passed = sum(1 for _, _, _, ok in results if ok)
    failed = total - passed
    print(f"共计接口: {total}")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    if failed > 0:
        print("\n失败详情:")
        for method, path, status, ok in results:
            if not ok:
                print(f"  ❌ {method:4s} {path} → {status}")
    print("=" * 70)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
