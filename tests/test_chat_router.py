"""
心海法律 AI - ChatRouter 单元测试
测试对话路由系统的核心功能
"""

import unittest
import json
import sys
import os
import tempfile
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.chat_router import (
    ChatRouter, Message, ChatContext, MessageType,
    create_chat_router
)


class TestMessageTypes(unittest.TestCase):
    """测试消息类型"""
    
    def test_message_creation(self):
        """测试消息创建"""
        msg = Message(
            type=MessageType.TEXT.value,
            content="你好",
            metadata={"source": "test"}
        )
        
        self.assertEqual(msg.type, "text")
        self.assertEqual(msg.content, "你好")
        self.assertEqual(msg.metadata["source"], "test")
    
    def test_message_to_dict(self):
        """测试消息转字典"""
        msg = Message(
            type=MessageType.CARD_PRICING.value,
            content="报价信息",
            metadata={"price": 100}
        )
        
        result = msg.to_dict()
        self.assertEqual(result["type"], "card_pricing")
        self.assertEqual(result["content"], "报价信息")
        self.assertEqual(result["metadata"]["price"], 100)


class TestChatContext(unittest.TestCase):
    """测试对话上下文"""
    
    def setUp(self):
        """设置临时数据库"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.router = ChatRouter(db_path=self.temp_db.name)
    
    def tearDown(self):
        """清理临时文件"""
        os.unlink(self.temp_db.name)
    
    def test_create_context(self):
        """测试创建上下文"""
        ctx = self.router.get_or_create_context("test_session_001", user_id=1)
        
        self.assertEqual(ctx.session_id, "test_session_001")
        self.assertEqual(ctx.user_id, 1)
        self.assertEqual(ctx.current_intent, "general")
        self.assertEqual(len(ctx.messages), 0)
    
    def test_add_message(self):
        """测试添加消息"""
        session_id = "test_session_002"
        self.router.add_message(session_id, "user", "你好", "text")
        self.router.add_message(session_id, "assistant", "您好！", "text")
        
        ctx = self.router.get_or_create_context(session_id)
        self.assertEqual(ctx.message_count, 2)
        self.assertEqual(len(ctx.messages), 2)
        self.assertEqual(ctx.messages[0]["content"], "你好")
        self.assertEqual(ctx.messages[1]["content"], "您好！")
    
    def test_get_history(self):
        """测试获取历史"""
        session_id = "test_session_003"
        for i in range(25):
            self.router.add_message(session_id, "user", f"消息{i}")
        
        history = self.router.get_conversation_history(session_id, limit=20)
        self.assertEqual(len(history), 20)
        self.assertEqual(history[0]["content"], "消息 5")  # 跳过前 5 条
    
    def test_clear_context(self):
        """测试清除上下文"""
        session_id = "test_session_004"
        self.router.add_message(session_id, "user", "测试消息")
        
        self.router.clear_context(session_id)
        
        ctx = self.router.get_or_create_context(session_id)
        self.assertEqual(ctx.message_count, 0)
        self.assertEqual(len(ctx.messages), 0)


class TestIntentDetection(unittest.TestCase):
    """测试意图识别"""
    
    def setUp(self):
        self.router = ChatRouter()
    
    def test_pricing_intent(self):
        """测试报价意图"""
        self.assertEqual(self.router.detect_intent("这个服务多少钱？"), "pricing")
        self.assertEqual(self.router.detect_intent("费用是多少"), "pricing")
        self.assertEqual(self.router.detect_intent("what's the price"), "pricing")
    
    def test_product_intent(self):
        """测试产品意图"""
        self.assertEqual(self.router.detect_intent("你们有什么服务"), "product")
        self.assertEqual(self.router.detect_intent("会员套餐"), "product")
    
    def test_document_intent(self):
        """测试文档意图"""
        self.assertEqual(self.router.detect_intent("需要一份合同模板"), "document")
        self.assertEqual(self.router.detect_intent("法律文书"), "document")
    
    def test_order_intent(self):
        """测试订单意图"""
        self.assertEqual(self.router.detect_intent("我要下单"), "order")
        self.assertEqual(self.router.detect_intent("支付订单"), "order")
    
    def test_legal_consult_intent(self):
        """测试法律咨询意图"""
        self.assertEqual(self.router.detect_intent("我想咨询法律问题"), "legal_consult")
        self.assertEqual(self.router.detect_intent("怎么办"), "legal_consult")
    
    def test_general_intent(self):
        """测试一般意图"""
        self.assertEqual(self.router.detect_intent("你好"), "general")
        self.assertEqual(self.router.detect_intent("早上好"), "general")


class TestLegalDomainDetection(unittest.TestCase):
    """测试法律领域检测"""
    
    def setUp(self):
        self.router = ChatRouter()
    
    def test_marriage_domain(self):
        """测试婚姻家庭领域"""
        self.assertEqual(
            self.router.detect_legal_domain("我想离婚，财产怎么分割"),
            "婚姻家庭"
        )
    
    def test_labor_domain(self):
        """测试劳动争议领域"""
        self.assertEqual(
            self.router.detect_legal_domain("公司拖欠工资怎么办"),
            "劳动争议"
        )
    
    def test_contract_domain(self):
        """测试合同纠纷领域"""
        self.assertEqual(
            self.router.detect_legal_domain("合同违约了"),
            "合同纠纷"
        )
    
    def test_criminal_domain(self):
        """测试刑事辩护领域"""
        self.assertEqual(
            self.router.detect_legal_domain("被刑事拘留了"),
            "刑事辩护"
        )
    
    def test_unknown_domain(self):
        """测试未知领域"""
        self.assertIsNone(self.router.detect_legal_domain("今天天气不错"))


class TestPsychAssessment(unittest.TestCase):
    """测试心理画像评估"""
    
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.router = ChatRouter(db_path=self.temp_db.name)
    
    def tearDown(self):
        os.unlink(self.temp_db.name)
    
    def test_should_trigger_psych(self):
        """测试心理评估触发条件"""
        ctx = ChatContext(session_id="test_psych_001", user_id=1)
        
        # 消息数不足
        ctx.message_count = 2
        self.assertFalse(self.router.should_trigger_psych_assessment(ctx))
        
        # 消息数足够
        ctx.message_count = 5
        self.assertTrue(self.router.should_trigger_psych_assessment(ctx))
        
        # 刚触发过（5 分钟内）
        ctx.last_psych_trigger = datetime.now().isoformat()
        self.assertFalse(self.router.should_trigger_psych_assessment(ctx))
        
        # 超过 5 分钟
        ctx.last_psych_trigger = (datetime.now() - timedelta(minutes=6)).isoformat()
        self.assertTrue(self.router.should_trigger_psych_assessment(ctx))


class TestDynamicPricing(unittest.TestCase):
    """测试动态报价"""
    
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.router = ChatRouter(db_path=self.temp_db.name)
        
        # 创建测试用户
        conn = self.router._get_db()
        conn.execute("""
            INSERT INTO users (username, password_hash, membership)
            VALUES ('test_user', 'hash123', 'free')
        """)
        conn.commit()
        self.user_id = conn.execute(
            "SELECT id FROM users WHERE username='test_user'"
        ).fetchone()[0]
        conn.close()
    
    def tearDown(self):
        os.unlink(self.temp_db.name)
    
    def test_basic_pricing(self):
        """测试基础报价"""
        pricing = self.router.get_dynamic_pricing(self.user_id, "legal_consult")
        
        self.assertEqual(pricing["product_type"], "legal_consult")
        self.assertEqual(pricing["base_price"], 50)
        self.assertLessEqual(pricing["final_price"], pricing["base_price"])
        self.assertIn("discount_rate", pricing)
    
    def test_membership_discount(self):
        """测试会员折扣"""
        # 更新用户为会员
        conn = self.router._get_db()
        conn.execute("UPDATE users SET membership='monthly' WHERE id=?", (self.user_id,))
        conn.commit()
        conn.close()
        
        pricing = self.router.get_dynamic_pricing(self.user_id, "legal_consult")
        
        # 会员应该享受折扣
        self.assertLess(pricing["final_price"], pricing["base_price"])
        self.assertEqual(pricing["factors"]["membership"], "monthly")


class TestMessageRouting(unittest.TestCase):
    """测试消息路由"""
    
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.router = ChatRouter(db_path=self.temp_db.name)
    
    def tearDown(self):
        os.unlink(self.temp_db.name)
    
    def test_route_pricing_request(self):
        """测试报价请求路由"""
        result = self.router.route_message(
            user_input="这个服务多少钱",
            session_id="test_route_001",
            user_id=None
        )
        
        self.assertEqual(result["intent"], "pricing")
        self.assertGreater(len(result["messages"]), 0)
        
        # 应该包含报价卡片
        pricing_msgs = [
            m for m in result["messages"] 
            if m["type"] == "card_pricing"
        ]
        self.assertGreater(len(pricing_msgs), 0)
    
    def test_route_legal_consult(self):
        """测试法律咨询路由"""
        result = self.router.route_message(
            user_input="我想咨询离婚问题",
            session_id="test_route_002",
            user_id=None
        )
        
        self.assertEqual(result["intent"], "legal_consult")
        self.assertEqual(result["domain"], "婚姻家庭")
        self.assertGreater(len(result["messages"]), 0)
    
    def test_route_product_request(self):
        """测试产品咨询路由"""
        result = self.router.route_message(
            user_input="你们有什么会员服务",
            session_id="test_route_003",
            user_id=None
        )
        
        self.assertEqual(result["intent"], "product")
        
        # 应该包含产品卡片
        product_msgs = [
            m for m in result["messages"] 
            if m["type"] == "card_product"
        ]
        self.assertGreater(len(product_msgs), 0)
    
    def test_route_document_request(self):
        """测试文档请求路由"""
        result = self.router.route_message(
            user_input="我需要一份合同模板",
            session_id="test_route_004",
            user_id=None
        )
        
        self.assertEqual(result["intent"], "document")
        
        # 应该包含文档卡片和按钮
        doc_msgs = [
            m for m in result["messages"] 
            if m["type"] in ["card_document", "button"]
        ]
        self.assertGreater(len(doc_msgs), 0)


class TestChatRouterIntegration(unittest.TestCase):
    """ChatRouter 集成测试"""
    
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.router = ChatRouter(db_path=self.temp_db.name)
        
        # 创建测试用户
        conn = self.router._get_db()
        conn.execute("""
            INSERT INTO users (username, password_hash, membership, total_consultations)
            VALUES ('integration_test', 'hash456', 'free', 0)
        """)
        conn.commit()
        self.user_id = conn.execute(
            "SELECT id FROM users WHERE username='integration_test'"
        ).fetchone()[0]
        conn.close()
    
    def tearDown(self):
        os.unlink(self.temp_db.name)
    
    def test_full_conversation_flow(self):
        """测试完整对话流程"""
        session_id = "integration_session_001"
        
        # 第 1 条：问候
        result1 = self.router.route_message(
            user_input="你好",
            session_id=session_id,
            user_id=self.user_id
        )
        self.assertEqual(result1["intent"], "general")
        
        # 第 2 条：咨询价格
        result2 = self.router.route_message(
            user_input="法律咨询怎么收费",
            session_id=session_id,
            user_id=self.user_id
        )
        self.assertEqual(result2["intent"], "pricing")
        
        # 第 3 条：法律问题
        result3 = self.router.route_message(
            user_input="我想问离婚财产分割的问题",
            session_id=session_id,
            user_id=self.user_id
        )
        self.assertEqual(result3["domain"], "婚姻家庭")
        
        # 第 4 条：继续咨询（应该触发心理评估）
        result4 = self.router.route_message(
            user_input="我有点担心财产分不公平",
            session_id=session_id,
            user_id=self.user_id
        )
        
        # 验证上下文保持
        ctx = self.router.get_or_create_context(session_id)
        self.assertEqual(ctx.message_count, 4)
        self.assertEqual(ctx.legal_domain, "婚姻家庭")
    
    def test_session_persistence(self):
        """测试会话持久化"""
        session_id = "persistence_session_001"
        
        # 添加消息
        self.router.add_message(session_id, "user", "测试持久化")
        
        # 创建新 router 实例（模拟重启）
        new_router = ChatRouter(db_path=self.temp_db.name)
        
        # 验证消息仍然存在
        history = new_router.get_conversation_history(session_id)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["content"], "测试持久化")


class TestFactoryFunction(unittest.TestCase):
    """测试工厂函数"""
    
    def test_create_chat_router(self):
        """测试创建 router 实例"""
        router = create_chat_router()
        self.assertIsInstance(router, ChatRouter)
    
    def test_create_chat_router_with_db(self):
        """测试带数据库创建 router"""
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        try:
            router = create_chat_router(db_path=temp_db.name)
            self.assertIsInstance(router, ChatRouter)
            self.assertEqual(router.db_path, temp_db.name)
        finally:
            os.unlink(temp_db.name)


if __name__ == "__main__":
    # 运行测试
    unittest.main(verbosity=2)
