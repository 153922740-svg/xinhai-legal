#!/usr/bin/env python
"""快速测试 ChatRouter 功能"""

import sys
import os
sys.path.insert(0, '/root/xinhai-legal')

from services.chat_router import ChatRouter, MessageType

# 创建 router（不使用数据库）
router = ChatRouter()

print("=" * 50)
print("测试 1: 意图识别")
print("=" * 50)
test_inputs = [
    "这个服务多少钱",
    "你们有什么会员套餐",
    "我需要合同模板",
    "我要下单购买",
    "我想咨询离婚问题",
    "你好"
]

for text in test_inputs:
    intent = router.detect_intent(text)
    domain = router.detect_legal_domain(text)
    print(f"输入：{text}")
    print(f"  意图：{intent}, 领域：{domain}")
    print()

print("=" * 50)
print("测试 2: 消息路由")
print("=" * 50)

result = router.route_message(
    user_input="我想咨询离婚财产分割的问题",
    session_id="test_001",
    user_id=None
)

print(f"意图：{result['intent']}")
print(f"领域：{result['domain']}")
print(f"消息数量：{len(result['messages'])}")
print(f"响应时间：{result['response_time_ms']}ms")
print()

for msg in result['messages']:
    print(f"消息类型：{msg['type']}")
    print(f"消息内容：{msg['content'][:100]}...")
    print()

print("=" * 50)
print("测试 3: 对话上下文")
print("=" * 50)

# 模拟多轮对话
session_id = "multi_turn_test"
messages = [
    "你好",
    "我想咨询法律问题",
    "关于劳动合同的",
    "公司拖欠工资怎么办"
]

for msg in messages:
    result = router.route_message(
        user_input=msg,
        session_id=session_id,
        user_id=None
    )
    print(f"用户：{msg}")
    print(f"  意图：{result['intent']}, 领域：{result['domain']}")
    print()

ctx = router.get_or_create_context(session_id)
print(f"对话历史消息数：{ctx.message_count}")
print(f"当前领域：{ctx.legal_domain}")

print("=" * 50)
print("所有测试完成！")
print("=" * 50)
