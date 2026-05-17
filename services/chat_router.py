"""
心海法律 AI - ChatRouter 对话路由服务
PRD v4.0 核心实现：支持多种消息类型、对话上下文管理、心理画像、动态报价
"""

import json
import uuid
import time
import re
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import sqlite3
import os


# ========== 消息类型定义 ==========

class MessageType(Enum):
    """支持的消息类型"""
    TEXT = "text"
    CARD_PRICING = "card_pricing"
    CARD_PRODUCT = "card_product"
    CARD_DOCUMENT = "card_document"
    CARD_ORDER = "card_order"
    BUTTON = "button"


@dataclass
class Message:
    """消息数据结构"""
    type: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "type": self.type,
            "content": self.content,
            "metadata": self.metadata
        }


@dataclass
class ChatContext:
    """对话上下文"""
    session_id: str
    user_id: Optional[int]
    messages: List[Dict] = field(default_factory=list)
    current_intent: str = "general"
    legal_domain: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_activity: str = field(default_factory=lambda: datetime.now().isoformat())
    message_count: int = 0
    psych_trigger_count: int = 0
    last_psych_trigger: Optional[str] = None


# ========== ChatRouter 核心类 ==========

class ChatRouter:
    """
    对话路由引擎
    - 支持多种消息类型
    - 会话上下文管理
    - 心理画像触发（每 5 分钟最多 1 次）
    - 动态报价集成
    - AI 模型调用
    """
    
    # API 配置
    AI_API_URL = "http://127.0.0.1:8642/v1/chat/completions"
    AI_API_KEY = "xinclaw-law-2026-secret"
    
    # 心理画像触发间隔（秒）
    PSYCH_TRIGGER_INTERVAL = 300  # 5 分钟
    
    # 法律领域关键词映射
    LEGAL_DOMAIN_KEYWORDS = {
        "婚姻家庭": ["离婚", "结婚", "婚姻", "抚养", "赡养", "财产分割", "婚前", "婚后"],
        "劳动争议": ["工资", "加班", "裁员", "辞退", "工伤", "劳动合同", "社保", "公积金"],
        "合同纠纷": ["合同", "违约", "协议", "签约", "条款", "解除", "履行"],
        "侵权责任": ["侵权", "赔偿", "损害", "名誉", "肖像", "隐私"],
        "刑事辩护": ["犯罪", "刑事", "逮捕", "拘留", "判刑", "律师辩护"],
        "行政诉讼": ["行政", "政府", "处罚", "复议", "诉讼"],
        "房产纠纷": ["房产", "房屋", "购房", "租房", "物业", "产权"],
        "知识产权": ["专利", "商标", "版权", "著作权", "侵权"],
        "公司法务": ["公司", "股权", "股东", "法人", "注册", "注销"],
        "债权债务": ["债务", "债权", "欠款", "借贷", "催收", "担保"],
        "交通事故": ["交通", "事故", "车祸", "赔偿", "责任认定"],
        "医疗纠纷": ["医疗", "医院", "医生", "医疗事故", "诊疗"],
        "遗产继承": ["继承", "遗产", "遗嘱", "法定继承", "分配"],
        "消费维权": ["消费", "维权", "投诉", "假货", "欺诈", "退款"],
        "互联网金融": ["网贷", "金融", "理财", "投资", "平台"]
    }
    
    def __init__(self, db_path: str = None):
        """初始化 ChatRouter"""
        self.db_path = db_path
        self.contexts: Dict[str, ChatContext] = {}
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        if not self.db_path:
            return
        
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_contexts (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER,
                messages TEXT,
                current_intent TEXT DEFAULT 'general',
                legal_domain TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                message_count INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()
    
    def _get_db(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    # ========== 会话管理 ==========
    
    def get_or_create_context(self, session_id: str, user_id: Optional[int] = None) -> ChatContext:
        """获取或创建对话上下文"""
        if session_id in self.contexts:
            ctx = self.contexts[session_id]
            ctx.last_activity = datetime.now().isoformat()
            return ctx
        
        # 从数据库加载
        if self.db_path:
            conn = self._get_db()
            row = conn.execute(
                "SELECT * FROM chat_contexts WHERE session_id=?", (session_id,)
            ).fetchone()
            conn.close()
            
            if row:
                messages = json.loads(row['messages']) if row['messages'] else []
                ctx = ChatContext(
                    session_id=session_id,
                    user_id=user_id or row['user_id'],
                    messages=messages,
                    current_intent=row['current_intent'] or 'general',
                    legal_domain=row['legal_domain'],
                    created_at=row['created_at'],
                    last_activity=datetime.now().isoformat(),
                    message_count=row['message_count'] or 0
                )
                self.contexts[session_id] = ctx
                return ctx
        
        # 创建新上下文
        ctx = ChatContext(
            session_id=session_id,
            user_id=user_id
        )
        self.contexts[session_id] = ctx
        return ctx
    
    def save_context(self, ctx: ChatContext):
        """保存对话上下文到数据库"""
        if not self.db_path:
            return
        
        conn = self._get_db()
        conn.execute("""
            INSERT OR REPLACE INTO chat_contexts 
            (session_id, user_id, messages, current_intent, legal_domain, 
             created_at, last_activity, message_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ctx.session_id,
            ctx.user_id,
            json.dumps(ctx.messages),
            ctx.current_intent,
            ctx.legal_domain,
            ctx.created_at,
            ctx.last_activity,
            ctx.message_count
        ))
        conn.commit()
        conn.close()
    
    def add_message(self, session_id: str, role: str, content: str, 
                    message_type: str = "text", metadata: Dict = None):
        """添加消息到对话历史"""
        ctx = self.get_or_create_context(session_id)
        ctx.messages.append({
            "role": role,
            "type": message_type,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        })
        ctx.message_count += 1
        ctx.last_activity = datetime.now().isoformat()
        self.save_context(ctx)
    
    def get_conversation_history(self, session_id: str, limit: int = 999999) -> List[Dict]:
        """获取对话历史"""
        ctx = self.get_or_create_context(session_id)
        return ctx.messages[-limit:]
    
    def clear_context(self, session_id: str):
        """清除对话上下文"""
        if session_id in self.contexts:
            del self.contexts[session_id]
        
        if self.db_path:
            conn = self._get_db()
            conn.execute("DELETE FROM chat_contexts WHERE session_id=?", (session_id,))
            conn.commit()
            conn.close()
    
    # ========== 意图识别与领域分类 ==========
    
    def detect_intent(self, text: str) -> str:
        """检测用户意图"""
        text_lower = text.lower()
        
        # 报价相关
        if any(kw in text_lower for kw in ["价格", "多少钱", "费用", "收费", "报价", " cost", "price"]):
            return "pricing"
        
        # 产品/服务咨询
        if any(kw in text_lower for kw in ["服务", "产品", "会员", "套餐", "方案"]):
            return "product"
        
        # 文档需求
        if any(kw in text_lower for kw in ["文档", "合同", "协议", "模板", "文件"]):
            return "document"
        
        # 订单相关
        if any(kw in text_lower for kw in ["订单", "购买", "支付", "下单", "退款"]):
            return "order"
        
        # 法律咨询
        if any(kw in text_lower for kw in ["咨询", "问题", "求助", "怎么办", "如何"]):
            return "legal_consult"
        
        # 心理评估触发
        if any(kw in text_lower for kw in ["心情", "压力", "焦虑", "担心", "害怕"]):
            return "psych_check"
        
        return "general"
    
    def detect_legal_domain(self, text: str) -> Optional[str]:
        """检测法律领域"""
        text_lower = text.lower()
        
        for domain, keywords in self.LEGAL_DOMAIN_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                return domain
        
        return None
    
    # ========== 心理画像引擎集成 ==========
    
    def should_trigger_psych_assessment(self, ctx: ChatContext) -> bool:
        """判断是否应该触发心理画像评估（每 5 分钟最多 1 次）"""
        now = datetime.now()
        
        # 检查上次触发时间
        if ctx.last_psych_trigger:
            last_trigger = datetime.fromisoformat(ctx.last_psych_trigger)
            if (now - last_trigger).total_seconds() < self.PSYCH_TRIGGER_INTERVAL:
                return False
        
        # 检查对话长度（至少 3 条消息后触发）
        if ctx.message_count < 3:
            return False
        
        return True
    
    def trigger_psych_assessment(self, user_id: int, conversation_history: List[Dict]) -> Dict:
        """触发心理画像评估"""
        # 构建分析提示
        prompt = self._build_psych_analysis_prompt(conversation_history)
        
        try:
            response = self._call_ai_api(prompt, system_prompt="""
你是一位专业的法律心理咨询师。请根据用户的对话内容，分析其心理特征。
使用大五人格模型（开放性、尽责性、外向性、宜人性、神经质）进行评估。
同时评估风险承受能力。
所有评分范围 0-10 分。
以 JSON 格式返回结果。
""")
            
            result = json.loads(response) if isinstance(response, str) else response
            
            # 更新用户心理画像
            if self.db_path and user_id:
                self._update_psych_profile(user_id, result)
            
            return {
                "triggered": True,
                "assessment": result,
                "message": self._generate_psych_feedback(result)
            }
            
        except Exception as e:
            return {
                "triggered": False,
                "error": str(e)
            }
    
    def _build_psych_analysis_prompt(self, history: List[Dict]) -> str:
        """构建心理分析提示词"""
        conversation = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in history[-999999:]  # 所有消息
        ])
        
        return f"""
请分析以下对话中用户的心理特征：

{conversation}

请以 JSON 格式返回：
{{
    "openness": 5.0,  // 开放性 (0-10)
    "conscientiousness": 5.0,  // 尽责性 (0-10)
    "extraversion": 5.0,  // 外向性 (0-10)
    "agreeableness": 5.0,  // 宜人性 (0-10)
    "neuroticism": 5.0,  // 神经质 (0-10)
    "risk_tolerance": 5.0,  // 风险承受 (0-10)
    "confidence": 0.8,  // 评估置信度 (0-1)
    "notes": "简要分析说明"
}}
"""
    
    def _update_psych_profile(self, user_id: int, assessment: Dict):
        """更新用户心理画像"""
        conn = self._get_db()
        conn.execute("""
            INSERT OR REPLACE INTO psych_profiles 
            (user_id, openness, conscientiousness, extraversion, 
             agreeableness, neuroticism, risk_tolerance, 
             assessment_confidence, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            user_id,
            assessment.get('openness', 5.0),
            assessment.get('conscientiousness', 5.0),
            assessment.get('extraversion', 5.0),
            assessment.get('agreeableness', 5.0),
            assessment.get('neuroticism', 5.0),
            assessment.get('risk_tolerance', 5.0),
            assessment.get('confidence', 0.5)
        ))
        conn.commit()
        conn.close()
    
    def _generate_psych_feedback(self, assessment: Dict) -> str:
        """生成心理反馈消息"""
        notes = assessment.get('notes', '')
        return f"根据您的对话，我注意到{notes}。我们会为您提供更个性化的服务建议。"
    
    # ========== 动态报价引擎集成 ==========
    
    def get_dynamic_pricing(self, user_id: int, product_type: str, 
                           context: Dict = None) -> Dict:
        """获取动态报价"""
        # 获取用户信息
        user_info = self._get_user_info(user_id) if user_id else {}
        
        # 获取心理画像
        psych_profile = self._get_psych_profile(user_id) if user_id else {}
        
        # 基础价格
        base_prices = {
            "legal_consult": 50,
            "document_review": 100,
            "contract_draft": 300,
            "legal_representation": 1000,
            "membership_monthly": 29.9,
            "membership_quarterly": 79.9,
            "membership_yearly": 299
        }
        
        base_price = base_prices.get(product_type, 100)
        
        # 动态调整因子
        discount_factor = 1.0
        
        # 会员折扣
        if user_info.get('membership') in ['monthly', 'quarterly', 'yearly']:
            discount_factor *= 0.8
        
        # 心理画像调整（高风险承受者可能接受更高价格）
        risk_tolerance = psych_profile.get('risk_tolerance', 5.0)
        if risk_tolerance > 7:
            discount_factor *= 1.05  # 轻微上浮
        elif risk_tolerance < 3:
            discount_factor *= 0.95  # 轻微优惠
        
        # 新客户优惠
        if user_info.get('total_consultations', 0) == 0:
            discount_factor *= 0.9
        
        final_price = round(base_price * discount_factor, 2)
        
        return {
            "product_type": product_type,
            "base_price": base_price,
            "final_price": final_price,
            "discount_rate": round(discount_factor, 2),
            "factors": {
                "membership": user_info.get('membership', 'free'),
                "risk_tolerance": risk_tolerance,
                "is_new_customer": user_info.get('total_consultations', 0) == 0
            },
            "valid_until": (datetime.now() + timedelta(hours=24)).isoformat()
        }
    
    def _get_user_info(self, user_id: int) -> Dict:
        """获取用户信息"""
        if not self.db_path:
            return {}
        
        conn = self._get_db()
        row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return {}
    
    def _get_psych_profile(self, user_id: int) -> Dict:
        """获取用户心理画像"""
        if not self.db_path:
            return {}
        
        conn = self._get_db()
        row = conn.execute(
            "SELECT * FROM psych_profiles WHERE user_id=?", (user_id,)
        ).fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return {}
    
    # ========== AI 模型调用 ==========
    
    def _call_ai_api(self, user_message: str, system_prompt: str = None,
                     context_messages: List[Dict] = None) -> str:
        """调用 AI API 生成回复"""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        if context_messages:
            messages.extend(context_messages)
        
        messages.append({"role": "user", "content": user_message})
        
        payload = {
            "model": "qwen3.5-plus",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 999999
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.AI_API_KEY}"
        }
        
        try:
            response = requests.post(
                self.AI_API_URL,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            return result.get('choices', [{}])[0].get('message', {}).get('content', '')
        except Exception as e:
            return f"[AI 服务暂时不可用：{str(e)}]"
    
    def generate_legal_response(self, question: str, domain: str = None,
                                context: List[Dict] = None) -> str:
        """生成法律专业回复"""
        # 从知识库中检索相关条目
        knowledge_context = ""
        try:
            from services.legal_files import LegalKnowledgeBase
            kb = LegalKnowledgeBase(self.db_path)
            results = kb.search(question, domain)
            if results:
                knowledge_context = "\n\n以下是相关的法律知识参考：\n"
                for i, r in enumerate(results[:3], 1):
                    knowledge_context += f"\n【参考{i}】{r['title']}\n{r['content'][:500]}\n"
        except Exception as e:
            knowledge_context = ""
        
        system_prompt = f"""
你是一位专业的中国法律顾问，具有深厚的法律知识和丰富的实践经验。
{'当前咨询领域：' + domain if domain else ''}
{knowledge_context}

请：
1. 准确理解用户问题
2. 引用相关法律条文（如《民法典》、《劳动法》等）
3. 提供清晰、实用的法律建议
4. 提醒用户必要时寻求线下专业律师帮助
5. 保持专业、友善的语气
6. 6. 如有相关法律知识参考，请将其融入回答中，不要直接说"参考1"等编号
"""
        
        return self._call_ai_api(question, system_prompt, context)
    
    # ========== 消息路由与生成 ==========
    
    def route_message(self, user_input: str, session_id: str, 
                     user_id: Optional[int] = None,
                     history: Optional[List[Dict]] = None) -> Dict:
        """
        核心路由方法：处理用户输入并返回适当类型的消息
        支持 history 参数：前端传入的历史记录，用于在服务端无状态时恢复上下文
        """
        start_time = time.time()
        
        # 获取上下文
        ctx = self.get_or_create_context(session_id, user_id)
        
        # 如果前端传入了 history，用它恢复/覆盖当前上下文中的消息记录
        if history and isinstance(history, list) and len(history) > 0:
            # 检查是否需要替换（避免每次请求都覆盖）
            if len(ctx.messages) == 0 or len(ctx.messages) < len(history):
                ctx.messages = [
                    {
                        "role": m["role"],
                        "type": "text",
                        "content": m["content"],
                        "metadata": {},
                        "timestamp": datetime.now().isoformat()
                    }
                    for m in history
                ]
                ctx.message_count = len(ctx.messages)
                self.save_context(ctx)
        
        # 保存用户消息
        self.add_message(session_id, "user", user_input, "text")
        
        # 检测意图和领域
        intent = self.detect_intent(user_input)
        domain = self.detect_legal_domain(user_input) or ctx.legal_domain
        ctx.current_intent = intent
        ctx.legal_domain = domain
        self.save_context(ctx)
        
        response_data = {
            "session_id": session_id,
            "intent": intent,
            "domain": domain,
            "messages": [],
            "psych_assessment": None,
            "pricing": None,
            "response_time_ms": 0
        }
        
        # 根据意图路由
        if intent == "pricing":
            response_data["messages"] = self._handle_pricing_request(user_input, user_id, domain)
        elif intent == "product":
            response_data["messages"] = self._handle_product_request(user_input, user_id)
        elif intent == "document":
            response_data["messages"] = self._handle_document_request(user_input, user_id)
        elif intent == "order":
            response_data["messages"] = self._handle_order_request(user_input, user_id)
        elif intent == "legal_consult":
            response_data["messages"] = self._handle_legal_consult(user_input, ctx, domain)
        else:
            response_data["messages"] = self._handle_general_chat(user_input, ctx)
        
        # ========== 新增：保存 AI 回复到上下文 ==========
        if response_data["messages"]:
            for msg in response_data["messages"]:
                # 只保存 text 类型的 AI 回复（卡片类型用 summary 或 content 保存）
                content_text = msg.get("content", "")
                msg_type = msg.get("type", "text")
                metadata = msg.get("metadata", {})
                
                if msg_type == "text" or msg_type == "card_pricing":
                    self.add_message(
                        session_id, "assistant", content_text, msg_type,
                        metadata={"source": "ai_reply", **metadata}
                    )
                else:
                    # 非文本消息（卡片等）保存 summary 或 content
                    summary = metadata.get("summary", content_text)
                    self.add_message(
                        session_id, "assistant", summary or content_text, msg_type,
                        metadata={"source": "ai_reply", "card_type": msg_type, **metadata}
                    )
        # ===============================================
        
        # 检查是否需要触发心理评估
        if self.should_trigger_psych_assessment(ctx) and user_id:
            psych_result = self.trigger_psych_assessment(
                user_id, 
                self.get_conversation_history(session_id)
            )
            if psych_result.get('triggered'):
                response_data["psych_assessment"] = psych_result
                ctx.last_psych_trigger = datetime.now().isoformat()
                self.save_context(ctx)
                # 添加心理反馈消息
                response_data["messages"].append(
                    Message(
                        type=MessageType.TEXT.value,
                        content=psych_result.get('message', ''),
                        metadata={"psych_feedback": True}
                    ).to_dict()
                )
        
        response_data["response_time_ms"] = int((time.time() - start_time) * 1000)
        
        return response_data
    
    def _handle_pricing_request(self, input_text: str, user_id: int, 
                                domain: str = None) -> List[Dict]:
        """处理报价请求"""
        product_type = "legal_consult"
        if "会员" in input_text:
            product_type = "membership_monthly"
        elif "合同" in input_text:
            product_type = "contract_draft"
        elif "文书" in input_text:
            product_type = "document_review"
        
        pricing = self.get_dynamic_pricing(user_id, product_type)
        
        messages = [
            Message(
                type=MessageType.CARD_PRICING.value,
                content=f"根据您的需求和用户等级，我们为您提供以下报价",
                metadata={
                    "pricing": pricing,
                    "product_type": product_type,
                    "domain": domain
                }
            ).to_dict()
        ]
        
        # 添加行动按钮
        messages.append(
            Message(
                type=MessageType.BUTTON.value,
                content="立即咨询",
                metadata={
                    "action": "start_consultation",
                    "product_type": product_type,
                    "price": pricing['final_price']
                }
            ).to_dict()
        )
        
        return messages
    
    def _handle_product_request(self, input_text: str, user_id: int) -> List[Dict]:
        """处理产品/服务咨询"""
        products = [
            {
                "id": "consult_basic",
                "name": "基础法律咨询",
                "description": "30 分钟在线法律咨询，解答您的法律疑问",
                "price": 50,
                "tokens": 500
            },
            {
                "id": "consult_premium",
                "name": "深度法律咨询",
                "description": "60 分钟一对一咨询 + 书面法律意见",
                "price": 150,
                "tokens": 1500
            },
            {
                "id": "document_review",
                "name": "合同审查",
                "description": "专业律师审查合同，提供修改建议",
                "price": 100,
                "tokens": 1000
            },
            {
                "id": "membership_monthly",
                "name": "月度会员",
                "description": "无限次咨询 + 专属优惠",
                "price": 29.9,
                "tokens": 10000
            }
        ]
        
        return [
            Message(
                type=MessageType.CARD_PRODUCT.value,
                content="我们提供以下法律服务",
                metadata={"products": products}
            ).to_dict()
        ]
    
    def _handle_document_request(self, input_text: str, user_id: int) -> List[Dict]:
        """处理文档需求"""
        doc_type = "合同" if "合同" in input_text else "法律文书"
        
        return [
            Message(
                type=MessageType.CARD_DOCUMENT.value,
                content=f"为您生成{doc_type}模板",
                metadata={
                    "doc_type": doc_type,
                    "template_available": True,
                    "customizable": True
                }
            ).to_dict(),
            Message(
                type=MessageType.BUTTON.value,
                content="生成文档",
                metadata={
                    "action": "generate_document",
                    "doc_type": doc_type
                }
            ).to_dict()
        ]
    
    def _handle_order_request(self, input_text: str, user_id: int) -> List[Dict]:
        """处理订单相关请求"""
        return [
            Message(
                type=MessageType.CARD_ORDER.value,
                content="订单处理中",
                metadata={
                    "status": "pending",
                    "message": "请确认您的订单信息"
                }
            ).to_dict()
        ]
    
    def _handle_legal_consult(self, question: str, ctx: ChatContext,
                             domain: str = None) -> List[Dict]:
        """处理法律咨询"""
        history = self.get_conversation_history(ctx.session_id, limit=999999)
        context_messages = [
            {"role": msg['role'], "content": msg['content']}
            for msg in history[:-1]  # 排除当前问题
        ]
        
        answer = self.generate_legal_response(question, domain, context_messages)
        
        return [
            Message(
                type=MessageType.TEXT.value,
                content=answer,
                metadata={
                    "domain": domain,
                    "is_legal_advice": True
                }
            ).to_dict()
        ]
    
    def _handle_general_chat(self, input_text: str, ctx: ChatContext) -> List[Dict]:
        """处理一般聊天"""
        response = self.generate_legal_response(
            input_text, 
            ctx.legal_domain,
            [{"role": msg['role'], "content": msg['content']} 
             for msg in ctx.messages[-999999:]]  # 所有消息
        )
        
        return [
            Message(
                type=MessageType.TEXT.value,
                content=response,
                metadata={}
            ).to_dict()
        ]


# ========== 便捷函数 ==========

def create_chat_router(db_path: str = None) -> ChatRouter:
    """创建 ChatRouter 实例"""
    return ChatRouter(db_path)


if __name__ == "__main__":
    # 测试代码
    router = ChatRouter(db_path="data/test_chat.db")
    
    # 测试对话路由
    result = router.route_message(
        user_input="我想咨询离婚财产分割的问题",
        session_id="test_session_001",
        user_id=1
    )
    
    print(json.dumps(result, ensure_ascii=False, indent=2))
