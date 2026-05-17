#!/usr/bin/env python
"""
心海法律 AI - ChatRouter API 测试脚本
测试所有 ChatRouter 相关 API 端点
"""

import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8081"

def test_chat_send():
    """测试发送消息 API"""
    print("=" * 60)
    print("测试 1: POST /api/v1/chat/send")
    print("=" * 60)
    
    payload = {
        "message": "我想咨询离婚财产分割的问题",
        "session_id": "api_test_001"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/chat/send",
            json=payload,
            timeout=30
        )
        result = response.json()
        
        print(f"状态码：{response.status_code}")
        print(f"意图：{result.get('intent')}")
        print(f"领域：{result.get('domain')}")
        print(f"消息数量：{len(result.get('messages', []))}")
        print(f"响应时间：{result.get('response_time_ms')}ms")
        
        if result.get('success'):
            print("✓ 测试通过")
        else:
            print("✗ 测试失败")
            
    except Exception as e:
        print(f"✗ 请求失败：{e}")
    
    print()


def test_chat_history():
    """测试获取历史 API"""
    print("=" * 60)
    print("测试 2: GET /api/v1/chat/history")
    print("=" * 60)
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/chat/history",
            params={"session_id": "api_test_001"},
            timeout=10
        )
        result = response.json()
        
        print(f"状态码：{response.status_code}")
        print(f"消息总数：{result.get('total')}")
        
        if response.status_code == 200:
            print("✓ 测试通过")
        else:
            print(f"✗ 测试失败：{result.get('error')}")
            
    except Exception as e:
        print(f"✗ 请求失败：{e}")
    
    print()


def test_intent_detection():
    """测试意图识别 API"""
    print("=" * 60)
    print("测试 3: POST /api/v1/chat/intent")
    print("=" * 60)
    
    test_cases = [
        "这个服务多少钱",
        "你们有什么会员套餐",
        "我需要合同模板",
        "公司拖欠工资怎么办"
    ]
    
    for text in test_cases:
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/chat/intent",
                json={"message": text},
                timeout=10
            )
            result = response.json()
            print(f"输入：{text}")
            print(f"  意图：{result.get('intent')}, 领域：{result.get('domain')}")
        except Exception as e:
            print(f"  ✗ 失败：{e}")
    
    print("✓ 测试完成")
    print()


def test_pricing():
    """测试动态报价 API"""
    print("=" * 60)
    print("测试 4: POST /api/v1/chat/pricing")
    print("=" * 60)
    
    # 需要先登录获取 user_id
    print("注意：此接口需要登录后使用")
    print("跳过测试（需要有效用户会话）")
    print()


def test_multi_turn_conversation():
    """测试多轮对话"""
    print("=" * 60)
    print("测试 5: 多轮对话测试")
    print("=" * 60)
    
    session_id = "multi_turn_api_test"
    messages = [
        "你好",
        "我想咨询法律问题",
        "关于劳动合同纠纷",
        "公司不交社保怎么办"
    ]
    
    for i, text in enumerate(messages, 1):
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/chat/send",
                json={
                    "message": text,
                    "session_id": session_id
                },
                timeout=30
            )
            result = response.json()
            print(f"第{i}轮：{text}")
            print(f"  意图：{result.get('intent')}, 领域：{result.get('domain')}")
        except Exception as e:
            print(f"  ✗ 失败：{e}")
    
    print("✓ 多轮对话测试完成")
    print()


def test_message_types():
    """测试不同消息类型"""
    print("=" * 60)
    print("测试 6: 消息类型测试")
    print("=" * 60)
    
    test_cases = [
        ("价格咨询", "这个服务怎么收费", "card_pricing"),
        ("产品咨询", "你们有什么会员服务", "card_product"),
        ("文档需求", "我需要一份合同模板", "card_document"),
        ("法律咨询", "离婚财产怎么分割", "text")
    ]
    
    for name, text, expected_type in test_cases:
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/chat/send",
                json={
                    "message": text,
                    "session_id": f"type_test_{name}"
                },
                timeout=30
            )
            result = response.json()
            
            msg_types = [m['type'] for m in result.get('messages', [])]
            has_expected = expected_type in msg_types
            
            print(f"{name}: {text[:20]}...")
            print(f"  消息类型：{msg_types}")
            print(f"  {'✓' if has_expected else '⚠'} 期望类型：{expected_type}")
            
        except Exception as e:
            print(f"  ✗ 失败：{e}")
    
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("心海法律 AI - ChatRouter API 测试套件")
    print("=" * 60 + "\n")
    
    # 检查服务是否运行
    try:
        health = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if health.status_code != 200:
            print(f"⚠️  服务可能未运行 (状态码：{health.status_code})")
            print("请先启动服务：python app/main.py")
            sys.exit(1)
        print("✓ 服务运行正常\n")
    except Exception as e:
        print(f"⚠️  无法连接到服务：{e}")
        print("请先启动服务：python app/main.py")
        sys.exit(1)
    
    # 运行测试
    test_chat_send()
    test_chat_history()
    test_intent_detection()
    test_pricing()
    test_multi_turn_conversation()
    test_message_types()
    
    print("=" * 60)
    print("所有测试完成！")
    print("=" * 60)
