"""
心海法律 AI - API 集成测试
测试所有 FastAPI 端点
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestHealthAPI:
    """健康检查 API 测试"""

    def test_health_endpoint(self, client):
        """测试 /api/health 返回正确"""
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["app"] == "心海法律AI"
        assert "time" in data


class TestRegisterLoginAPI:
    """注册登录 API 测试"""

    def test_register_success(self, client):
        """测试注册成功"""
        resp = client.post("/api/register", json={
            "username": "new_user",
            "password": "password123"
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["message"] == "注册成功"
        assert data["user"]["username"] == "new_user"
        assert data["bonus_tokens"] > 0

    def test_register_duplicate(self, client):
        """测试重复注册"""
        client.post("/api/register", json={
            "username": "dup_user",
            "password": "password123"
        })
        resp = client.post("/api/register", json={
            "username": "dup_user",
            "password": "password123"
        })
        assert resp.status_code == 400
        assert "用户名已存在" in resp.text

    def test_register_missing_fields(self, client):
        """测试缺少必填字段"""
        resp = client.post("/api/register", json={"username": "u"})
        assert resp.status_code == 400

    def test_login_success(self, client):
        """测试登录成功"""
        client.post("/api/register", json={
            "username": "login_user",
            "password": "mypassword"
        })
        resp = client.post("/api/login", json={
            "username": "login_user",
            "password": "mypassword"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "登录成功"
        assert "tokens_balance" in data["user"]

    def test_login_wrong_password(self, client):
        """测试错误密码"""
        client.post("/api/register", json={
            "username": "wrong_pw",
            "password": "correct"
        })
        resp = client.post("/api/login", json={
            "username": "wrong_pw",
            "password": "wrong"
        })
        assert resp.status_code == 401


class TestUserInfoAPI:
    """用户信息 API 测试"""

    def test_user_info_without_auth(self, client):
        """测试未携带 auth 时被拒"""
        resp = client.get("/api/user/info")
        assert resp.status_code == 401

    def test_user_info_with_auth(self, client, sample_user, auth_headers):
        """测试获取用户信息"""
        resp = client.get("/api/user/info", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == sample_user["user"]["username"]


class TestBillingAPI:
    """计费 API 测试"""

    def test_get_plans(self, client):
        """测试获取会员方案"""
        resp = client.get("/api/billing/plans")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["plans"]) > 0
        assert "token_price_basic" in data
        assert data["plans"][0]["name"] in ["月度会员", "月卡"]

    def test_create_order_without_auth(self, client):
        """测试未登录创建订单"""
        resp = client.post("/api/billing/order", json={"plan": "monthly"})
        assert resp.status_code == 401

    def test_create_order(self, client, auth_headers):
        """测试创建会员订单"""
        resp = client.post("/api/billing/order",
                           json={"plan": "monthly"},
                           headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert "order_id" in data

    def test_pay_order(self, client, auth_headers):
        """测试支付订单"""
        # 先创建订单
        order_resp = client.post("/api/billing/order",
                                 json={"plan": "monthly"},
                                 headers=auth_headers)
        order_id = order_resp.json()["order_id"]

        # 支付
        resp = client.post(f"/api/billing/pay/{order_id}")
        assert resp.status_code == 200
        assert resp.json()["message"] == "支付成功，会员已激活"


class TestChatRouterAPI:
    """ChatRouter API 测试"""

    def test_chat_send(self, client):
        """测试发送消息"""
        resp = client.post("/api/v1/chat/send", json={
            "message": "你好，我想咨询法律问题"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "session_id" in data
        assert len(data["messages"]) > 0

    def test_chat_empty_message(self, client):
        """测试空消息"""
        resp = client.post("/api/v1/chat/send", json={
            "message": ""
        })
        assert resp.status_code == 400

    def test_chat_history(self, client):
        """测试获取对话历史"""
        # 先发一条消息
        send_resp = client.post("/api/v1/chat/send", json={
            "message": "测试历史记录",
            "session_id": "test_hist_001"
        })
        session_id = send_resp.json()["session_id"]

        # 获取历史
        resp = client.get(f"/api/v1/chat/history?session_id={session_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == session_id
        assert len(data["messages"]) > 0

    def test_chat_clear(self, client):
        """测试清除对话"""
        send_resp = client.post("/api/v1/chat/send", json={
            "message": "测试清除",
            "session_id": "test_clear_001"
        })
        session_id = send_resp.json()["session_id"]

        resp = client.post("/api/v1/chat/clear", json={
            "session_id": session_id
        })
        assert resp.status_code == 200
        assert resp.json()["success"] is True
