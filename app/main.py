"""
心海法律AI - FastAPI Web Application
主应用入口，整合所有模块
"""

import sys
import os
import json
import uuid
from datetime import datetime, date, timedelta
from contextlib import asynccontextmanager

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request, HTTPException, Depends, Header, Query
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import yaml

# Load config
config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.yaml')
with open(config_path, 'r', encoding='utf-8') as f:
    CONFIG = yaml.safe_load(f)

# Initialize database
from models.db import init_db, get_db, UserModel, UserMemoryModel

db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), CONFIG['database']['path'])
init_db(db_path)

# Initialize services
from services.legal_qa import LegalQAService
from services.billing import BillingService
from services.agency import AgencyService
from services.promotion import PromotionService
from services.legal_files import LegalFileService, RightsReminderService, LegalKnowledgeBase
from services.chat_router import ChatRouter

qa_service = LegalQAService(CONFIG)
billing_service = BillingService(CONFIG)
agency_service = AgencyService(CONFIG)
promotion_service = PromotionService(CONFIG)
legal_file_service = LegalFileService()
reminder_service = RightsReminderService(CONFIG)
knowledge_base = LegalKnowledgeBase(db_path=db_path)

# 初始化 ChatRouter
chat_router = ChatRouter(db_path=db_path)

# Seed knowledge base
try:
    knowledge_base.seed_knowledge()
except:
    pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"⚖️  心海法律AI服务平台 v{CONFIG['app']['version']}")
    print(f"   API Docs at http://{CONFIG['app']['host']}:{CONFIG['app']['port']}/docs")
    print(f"   Health check at http://{CONFIG['app']['host']}:{CONFIG['app']['port']}/api/health")
    yield


app = FastAPI(
    title=CONFIG['app']['name'],
    version=CONFIG['app']['version'],
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== Helper: 获取用户ID ==========

def get_user_id(request: Request, x_user_id: str = Header(None)) -> int | None:
    """从请求中提取用户ID"""
    return x_user_id


# ========== Auth API ==========

@app.get("/api/register")
@app.post("/api/register")
async def api_register(request: Request):
    """用户注册"""
    if request.method == "GET":
        return {
            'name': '用户注册',
            'method': 'POST',
            'params': {
                'username': '用户名', 'password': '密码',
                'real_name': '真实姓名(可选)', 'phone': '手机号(可选)', 'email': '邮箱(可选)'
            }
        }

    data = await request.json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        raise HTTPException(status_code=400, detail='用户名和密码不能为空')

    user = UserModel.create(
        db_path=db_path, username=username, password_hash=password,
        email=data.get('email'), phone=data.get('phone'),
        full_name=data.get('real_name')
    )

    if not user:
        raise HTTPException(status_code=400, detail='用户名已存在')

    UserModel.add_tokens(user['id'], CONFIG['pricing']['default_free_tokens'], 'gift', '注册赠送')

    return JSONResponse({
        'message': '注册成功',
        'user': {'id': user['id'], 'username': user['username']},
        'bonus_tokens': CONFIG['pricing']['default_free_tokens']
    }, status_code=201)


@app.get("/api/login")
@app.post("/api/login")
async def api_login(request: Request):
    """用户登录"""
    if request.method == "GET":
        return {
            'name': '用户登录',
            'method': 'POST',
            'params': {'username': '用户名', 'password': '密码'}
        }

    data = await request.json()
    username = data.get('username')
    password = data.get('password')

    user = UserModel.get_by_username(username)
    if not user:
        raise HTTPException(status_code=401, detail='用户名或密码错误')

    # 简单的密码校验（生产环境应使用 passlib/bcrypt）
    if user.get('password_hash') and user['password_hash'] != password:
        raise HTTPException(status_code=401, detail='用户名或密码错误')

    return {
        'message': '登录成功',
        'user': {
            'id': user['id'], 'username': user['username'],
            'role': user['role'], 'membership': user['membership'],
            'tokens_balance': user['tokens_balance']
        }
    }


@app.get("/api/user/info")
async def api_user_info(user_id: str = Header(None)):
    """获取用户信息"""
    if not user_id:
        raise HTTPException(status_code=401, detail='未登录')

    user = UserModel.get_by_id(int(user_id))
    if not user:
        raise HTTPException(status_code=404, detail='用户不存在')

    membership_info = billing_service.check_membership_status(user['id'])

    return {
        'id': user['id'], 'username': user['username'],
        'real_name': user.get('real_name'), 'phone': user.get('phone'),
        'role': user['role'], 'membership': membership_info,
        'tokens_balance': user['tokens_balance'],
        'agent_level': user.get('agent_level'), 'agent_code': user.get('agent_code'),
        'created_at': user['created_at']
    }


# ===== Legal Q&A API =====

@app.get("/api/legal/ask")
async def api_legal_ask_info():
    """法律咨询 - 信息说明"""
    return {
        'name': '法律咨询', 'method': 'POST',
        'params': {
            'question': '法律问题描述', 'user_id': '用户ID(可选)',
            'session_id': '会话ID(可选)', 'domain': '法律领域(可选，自动识别)'
        },
        'domains': CONFIG['legal_domains']
    }


@app.post("/api/legal/ask")
async def api_legal_ask(request: Request):
    """法律咨询"""
    data = await request.json()
    question = data.get('question')
    if not question:
        raise HTTPException(status_code=400, detail='请提供法律问题')

    user_id = data.get('user_id')
    session_id = data.get('session_id') or str(uuid.uuid4())[:12]

    if user_id:
        user_id = int(user_id)
        estimated_tokens = qa_service.calculate_tokens(question) + 500
        if not billing_service.can_use(user_id, estimated_tokens):
            user = UserModel.get_by_id(user_id)
            if user:
                raise HTTPException(status_code=402, detail={
                    'error': 'Token余额不足',
                    'tokens_balance': user['tokens_balance'],
                    'estimated_needed': estimated_tokens,
                    'suggestion': '请充值或升级会员'
                })
            raise HTTPException(status_code=404, detail='用户不存在')

    result = qa_service.ask(question, user_id, session_id)

    if user_id and user_id != 'None':
        billing_service.consume(user_id, result['tokens_used'], f"法律咨询: {question[:50]}...")

    # 注入用户记忆
    user_memories = []
    if user_id:
        memories = UserMemoryModel.get_memories(db_path, int(user_id), limit=10)
        user_memories = [{'type': m['memory_type'], 'content': m['content'], 'updated_at': m['updated_at']} for m in memories]

    return {
        'answer': result['final_answer'], 'domain': result['domain'],
        'confidence': result['confidence'], 'consensus': result['consensus'],
        'models_used': result['models_used'], 'tokens_used': result['tokens_used'],
        'session_id': session_id,
        'user_memories': user_memories
    }


@app.get("/api/legal/history")
async def api_legal_history(
    limit: int = Query(999999), offset: int = Query(0),
    user_id: str = Header(None)
):
    """获取咨询历史"""
    if not user_id:
        raise HTTPException(status_code=400, detail='请提供用户ID')

    from models.db import LegalQAModel
    history = LegalQAModel.get_history(int(user_id), limit, offset)

    return {
        'total': len(history), 'limit': limit, 'offset': offset,
        'items': [{
            'id': h['id'], 'question': h['question'], 'domain': h['domain'],
            'confidence': h['confidence'], 'tokens_used': h['tokens_used'],
            'created_at': h['created_at']
        } for h in history]
    }


# ===== Billing API =====

@app.get("/api/billing/plans")
async def api_billing_plans():
    """获取会员方案"""
    plans = []
    for plan_id, plan_info in billing_service.membership_plans.items():
        plans.append({
            'id': plan_id, 'name': plan_info['name'], 'price': plan_info['price'],
            'duration_days': plan_info['duration_days'], 'tokens': plan_info['tokens'],
            'price_per_day': round(plan_info['price'] / plan_info['duration_days'], 2)
        })

    return {
        'plans': plans,
        'token_price_basic': CONFIG['pricing']['token_prices']['basic'],
        'token_price_premium': CONFIG['pricing']['token_prices']['premium']
    }


@app.post("/api/billing/order")
async def api_billing_order(request: Request, user_id: str = Header(None)):
    """创建会员订单"""
    if not user_id:
        raise HTTPException(status_code=401, detail='未登录')

    data = await request.json()
    plan = data.get('plan')
    order = billing_service.create_membership_order(int(user_id), plan)

    if not order:
        raise HTTPException(status_code=400, detail='无效的会员方案')

    return {
        'order_id': order['id'], 'plan': order['plan'], 'price': order['price'],
        'duration_days': order['duration_days'], 'tokens_granted': order['tokens_granted'],
        'status': order['status'], 'message': '订单创建成功，请完成支付'
    }


@app.post("/api/billing/pay/{order_id}")
async def api_billing_pay(order_id: int):
    """模拟支付并激活会员"""
    success = billing_service.activate_membership(order_id)
    if not success:
        raise HTTPException(status_code=400, detail='支付失败或订单不存在')

    conn = get_db()
    order = conn.execute("SELECT * FROM membership_orders WHERE id=?", (order_id,)).fetchone()
    conn.close()

    if order:
        order = dict(order)
        if order['user_id']:
            user = UserModel.get_by_id(order['user_id'])
            if user and user.get('parent_agent_id'):
                agency_service.record_commission(
                    order_id, 'membership', order['price'], user['parent_agent_id']
                )

    return {
        'message': '支付成功，会员已激活',
        'order': dict(order) if order else {'id': order_id}
    }


@app.post("/api/billing/tokens/buy")
async def api_buy_tokens(request: Request, user_id: str = Header(None)):
    """购买Token"""
    if not user_id:
        raise HTTPException(status_code=401, detail='未登录')

    data = await request.json()
    amount = float(data.get('amount', 0))

    if amount <= 0:
        raise HTTPException(status_code=400, detail='充值金额必须大于0')

    result = billing_service.purchase_tokens(int(user_id), amount)
    if not result:
        raise HTTPException(status_code=400, detail='购买失败')

    return {
        'message': f'购买成功，获得 {result["tokens"]} Token',
        'tokens': result['tokens'], 'amount': result['amount'],
        'balance_after': result['balance_after']
    }


@app.get("/api/billing/stats")
async def api_billing_stats(user_id: str = Header(None)):
    """获取用量统计"""
    if not user_id:
        raise HTTPException(status_code=401, detail='未登录')

    stats = billing_service.get_usage_stats(int(user_id))
    return stats


# ===== Agency API =====

@app.get("/api/agent/regions")
async def api_agent_regions(province: str = Query(None)):
    """获取区域信息"""
    provinces = agency_service.get_provinces()
    if province:
        cities = agency_service.get_cities(province)
        return {'province': province, 'cities': cities}
    return {'provinces': provinces}


@app.get("/api/agent/apply")
async def api_agent_apply_info():
    """代理申请 - 信息说明"""
    return {
        'name': '代理申请', 'method': 'POST',
        'levels': [{'code': k, 'name': v['name'], 'buyin': v['buyin']}
                   for k, v in CONFIG['agency']['levels'].items()],
        'params': {
            'user_id': '用户ID', 'level': '代理级别(county/city/provincial)',
            'province': '省份', 'city': '城市(可选)', 'district': '区县(可选)',
            'company_name': '公司名称(可选)', 'contact_phone': '联系电话'
        }
    }


@app.post("/api/agent/apply")
async def api_agent_apply(request: Request, user_id: str = Header(None)):
    """申请成为代理"""
    if not user_id:
        raise HTTPException(status_code=401, detail='请提供用户ID')

    data = await request.json()
    result = agency_service.apply_agent(
        user_id=int(user_id), level=data.get('level'),
        province=data.get('province'), city=data.get('city'),
        district=data.get('district'), company_name=data.get('company_name'),
        contact_phone=data.get('contact_phone')
    )
    return result


@app.post("/api/agent/approve/{profile_id}")
async def api_agent_approve(profile_id: int):
    """审核通过代理 (管理员)"""
    success = agency_service.approve_agent(profile_id)
    return {'success': success}


@app.get("/api/agent/stats")
async def api_agent_stats(user_id: str = Header(None)):
    """获取代理统计数据"""
    if not user_id:
        raise HTTPException(status_code=401, detail='未登录')

    conn = get_db()
    profile = conn.execute(
        "SELECT id FROM agent_profiles WHERE user_id=?", (int(user_id),)
    ).fetchone()
    conn.close()

    if not profile:
        raise HTTPException(status_code=404, detail='您还不是代理')

    stats = agency_service.get_agent_stats(profile['id'])
    return stats


@app.post("/api/agent/withdraw")
async def api_agent_withdraw(request: Request, user_id: str = Header(None)):
    """提现佣金"""
    if not user_id:
        raise HTTPException(status_code=401, detail='未登录')

    conn = get_db()
    profile = conn.execute(
        "SELECT id FROM agent_profiles WHERE user_id=?", (int(user_id),)
    ).fetchone()
    conn.close()

    if not profile:
        raise HTTPException(status_code=404, detail='您还不是代理')

    data = await request.json()
    amount = float(data.get('amount', 0))
    result = agency_service.withdraw_commission(profile['id'], amount)
    return result


# ===== Promotion API =====

@app.get("/api/promotion/templates")
async def api_promotion_templates(
    category: str = Query(None), tag: str = Query(None)
):
    """获取推广模板"""
    templates = promotion_service.get_templates(category, tag)
    return templates


@app.post("/api/promotion/generate")
async def api_promotion_generate(request: Request):
    """生成推广内容"""
    data = await request.json()
    result = promotion_service.generate_promotion(
        data.get('category', '朋友圈推广'),
        data.get('agent_name'), data.get('agent_code'), data.get('custom_msg')
    )
    return result


@app.post("/api/promotion/script")
async def api_promotion_script(request: Request):
    """生成短视频脚本"""
    data = await request.json()
    result = promotion_service.generate_video_script(data.get('title'))
    return result


@app.post("/api/promotion/analyze")
async def api_promotion_analyze(request: Request):
    """分析客户消息"""
    data = await request.json()
    message = data.get('message', '')
    if not message:
        raise HTTPException(status_code=400, detail='请提供客户消息')
    result = promotion_service.analyze_customer_message(message)
    return result


# ===== Legal Files API =====

@app.get("/api/cases")
async def api_cases_list(
    status: str = Query(None), user_id: str = Header(None)
):
    """获取案件列表"""
    if not user_id:
        raise HTTPException(status_code=401, detail='未登录')
    cases = legal_file_service.get_user_cases(int(user_id), status)
    return {'total': len(cases), 'items': cases}


@app.post("/api/cases")
async def api_cases_create(request: Request, user_id: str = Header(None)):
    """创建案件"""
    if not user_id:
        raise HTTPException(status_code=401, detail='未登录')
    data = await request.json()
    result = legal_file_service.create_case(
        user_id=int(user_id), title=data.get('title'),
        description=data.get('description'), case_type=data.get('case_type'),
        domain=data.get('domain'), opponent_name=data.get('opponent_name'),
        claim_amount=data.get('claim_amount', type=float),
        key_date=data.get('key_date'), key_date_desc=data.get('key_date_desc')
    )
    return result


@app.get("/api/cases/{case_id}")
async def api_case_detail(case_id: int):
    """案件详情"""
    case = legal_file_service.get_case_detail(case_id)
    if not case:
        raise HTTPException(status_code=404, detail='案件不存在')
    return case


@app.put("/api/cases/{case_id}")
async def api_case_update(case_id: int, request: Request):
    """更新案件"""
    data = await request.json()
    success = legal_file_service.update_case(case_id, **data)
    return {'success': success}


# ===== ChatRouter API =====

@app.post("/api/v1/chat/send")
async def api_chat_send(request: Request):
    """
    ChatRouter 核心 API：发送消息并获取智能回复
    支持多种消息类型：text, card_pricing, card_product, card_document, card_order, button
    """
    data = await request.json()

    user_input = data.get('message')
    if not user_input:
        raise HTTPException(status_code=400, detail='请提供消息内容')

    session_id = data.get('session_id') or str(uuid.uuid4())[:12]
    user_id = data.get('user_id')
    if user_id:
        user_id = int(user_id)

    history = data.get('history')

    # 调用 ChatRouter 处理
    result = chat_router.route_message(
        user_input=user_input, session_id=session_id,
        user_id=user_id, history=history
    )

    # 保存聊天记录到数据库
    if user_id:
        conn = get_db()
        for msg in result['messages']:
            conn.execute("""
                INSERT INTO chat_logs (user_id, session_id, message_type, content, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, session_id, 'assistant', msg['content'], json.dumps(msg)))
        conn.commit()
        conn.close()

    return {
        'success': True, 'session_id': session_id,
        'intent': result['intent'], 'domain': result['domain'],
        'messages': result['messages'],
        'psych_assessment': result.get('psych_assessment'),
        'pricing': result.get('pricing'),
        'response_time_ms': result['response_time_ms']
    }


@app.get("/api/v1/chat/history")
async def api_chat_history(
    session_id: str = Query(...), limit: int = Query(999999)
):
    """获取对话历史"""
    history = chat_router.get_conversation_history(session_id, limit)
    return {
        'session_id': session_id,
        'total': len(history),
        'messages': history
    }


@app.post("/api/v1/chat/clear")
async def api_chat_clear(request: Request):
    """清除对话上下文"""
    data = await request.json()
    session_id = data.get('session_id')
    if not session_id:
        raise HTTPException(status_code=400, detail='请提供 session_id')

    chat_router.clear_context(session_id)
    return {'success': True, 'message': '对话上下文已清除'}


# ===== 小程序核心 API（添加于 nginx /api/v1/ 路径下）=====

# ---------- Auth API ----------

@app.post("/api/auth/send-code")
@app.post("/api/auth/send_sms")
async def api_auth_send_code(request: Request):
    """发送验证码（开发模式：888888）"""
    data = await request.json()
    phone = data.get('phone')
    if not phone:
        raise HTTPException(status_code=400, detail='手机号不能为空')
    # 开发模式：验证码固定为 888888
    return {
        'success': True,
        'message': '验证码已发送（开发模式）',
        'code_hint': '888888',
        'expire_in': 300
    }


@app.post("/api/auth/login")
async def api_auth_phone_login(request: Request):
    """手机号+验证码登录（开发模式：验证码888888）"""
    data = await request.json()
    phone = data.get('phone')
    code = data.get('code')

    if not phone or not code:
        raise HTTPException(status_code=400, detail='手机号和验证码不能为空')

    # 开发模式验证码校验
    if code != '888888':
        raise HTTPException(status_code=401, detail='验证码错误')

    # 查找或创建用户
    user = UserModel.get_by_phone(db_path, phone)
    if not user:
        # 自动注册
        import hashlib
        username = f"u_{phone[-4:]}"
        user = UserModel.create(
            db_path=db_path, username=username, phone=phone,
            full_name=data.get('real_name')
        )
        # 赠送初始Token
        UserModel.add_tokens(user['id'], CONFIG['pricing']['default_free_tokens'], 'gift', '手机注册赠送')
    else:
        UserModel.update_login(db_path, user['id'])

    membership_info = billing_service.check_membership_status(user['id'])

    return {
        'success': True,
        'message': '登录成功',
        'user': {
            'id': user['id'],
            'username': user['username'],
            'phone': user.get('phone'),
            'real_name': user.get('full_name'),
            'role': user['role'],
            'membership': membership_info,
            'tokens_balance': user['tokens_balance'],
            'created_at': user['created_at']
        }
    }


# ---------- User API ----------

@app.get("/api/user/profile")
async def api_user_profile(x_user_id: str = Header(None)):
    """获取用户资料"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail='未登录')
    user = UserModel.get_by_id(db_path, int(x_user_id))
    if not user:
        raise HTTPException(status_code=404, detail='用户不存在')
    membership_info = billing_service.check_membership_status(user['id'])
    return {
        'id': user['id'],
        'username': user['username'],
        'real_name': user.get('full_name'),
        'phone': user.get('phone'),
        'email': user.get('email'),
        'avatar': user.get('avatar'),
        'role': user['role'],
        'membership': membership_info,
        'tokens_balance': user['tokens_balance'],
        'created_at': user['created_at']
    }


# ---------- Membership / 会员 API ----------

@app.get("/api/member/status")
async def api_member_status(x_user_id: str = Header(None)):
    """获取会员状态"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail='未登录')
    status = billing_service.check_membership_status(int(x_user_id))
    # 附加套餐信息
    plans = []
    for plan_id, plan_info in billing_service.membership_plans.items():
        plans.append({
            'id': plan_id,
            'name': plan_info['name'],
            'price': plan_info['price'],
            'duration_days': plan_info['duration_days'],
            'tokens': plan_info['tokens'],
            'price_per_day': round(plan_info['price'] / plan_info['duration_days'], 2)
        })
    return {
        'membership': status,
        'plans': plans
    }


# ---------- Chat / 会话 API ----------

@app.get("/api/chat/sessions")
async def api_chat_sessions(
    limit: int = Query(50),
    offset: int = Query(0),
    x_user_id: str = Header(None)
):
    """获取历史会话列表"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail='未登录')
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT session_id, COUNT(*) as msg_count,
               MIN(created_at) as created_at, MAX(created_at) as last_activity,
               MAX(CASE WHEN message_type='user' THEN content ELSE '' END) as last_message
        FROM chat_logs
        WHERE user_id = ?
        GROUP BY session_id
        ORDER BY last_activity DESC
        LIMIT ? OFFSET ?
    """, (int(x_user_id), limit, offset))
    sessions = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {
        'total': len(sessions),
        'limit': limit,
        'offset': offset,
        'sessions': sessions
    }


@app.get("/api/chat/history/{session_id}")
async def api_chat_session_detail(session_id: str, limit: int = Query(999999)):
    """获取指定会话的详情"""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, message_type, content, model_used, tokens_used,
               response_time_ms, confidence_score, created_at
        FROM chat_logs
        WHERE session_id = ?
        ORDER BY created_at ASC
        LIMIT ?
    """, (session_id, limit))
    messages = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {
        'session_id': session_id,
        'total': len(messages),
        'messages': messages
    }


# ---------- Payment / 支付 API ----------

@app.post("/api/payment/wechat")
async def api_payment_wechat(request: Request, x_user_id: str = Header(None)):
    """微信支付（模拟）"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail='未登录')
    data = await request.json()
    plan_id = data.get('plan')
    if not plan_id:
        raise HTTPException(status_code=400, detail='请选择会员方案')

    plan_info = billing_service.membership_plans.get(plan_id)
    if not plan_info:
        raise HTTPException(status_code=400, detail='无效的会员方案')

    order = billing_service.create_membership_order(int(x_user_id), plan_id)
    if not order:
        raise HTTPException(status_code=400, detail='创建订单失败')

    # 模拟微信支付参数
    return {
        'success': True,
        'order_id': order['id'],
        'plan': plan_id,
        'price': order['price'],
        'payment_params': {
            'appId': 'wx_dev_appid',
            'timeStamp': str(int(datetime.now().timestamp())),
            'nonceStr': str(uuid.uuid4())[:16],
            'package': f'prepay_id={order["id"]}',
            'signType': 'MD5',
            'paySign': 'dev_mode_signature'
        },
        'message': '模拟支付参数已生成'
    }


# ---------- 用户记忆系统 ----------

@app.post("/api/user/memory")
async def api_user_memory_save(request: Request, x_user_id: str = Header(None)):
    """保存用户记忆"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail='未登录')
    data = await request.json()
    memory_type = data.get('memory_type', 'personal')
    content = data.get('content')
    session_id = data.get('session_id')

    if not content:
        raise HTTPException(status_code=400, detail='记忆内容不能为空')

    valid_types = ['personal', 'case', 'preference', 'summary']
    if memory_type not in valid_types:
        raise HTTPException(status_code=400, detail=f'无效的记忆类型，可选: {valid_types}')

    mem = UserMemoryModel.save_memory(db_path, int(x_user_id), memory_type, content, session_id)
    return {'success': True, 'memory': mem}


@app.get("/api/user/memory")
async def api_user_memory_get(
    memory_type: str = Query(None),
    limit: int = Query(50),
    x_user_id: str = Header(None)
):
    """获取用户记忆"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail='未登录')
    memories = UserMemoryModel.get_memories(db_path, int(x_user_id), memory_type, limit)
    return {'success': True, 'total': len(memories), 'memories': memories}


@app.delete("/api/user/memory")
async def api_user_memory_delete(
    memory_type: str = Query(None),
    x_user_id: str = Header(None)
):
    """清除用户记忆"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail='未登录')
    UserMemoryModel.delete_memories(db_path, int(x_user_id), memory_type)
    return {'success': True, 'message': '记忆已清除'}


# ===== Health =====

@app.get("/api/health")
async def api_health():
    """健康检查"""
    return {
        'status': 'ok',
        'app': CONFIG['app']['name'],
        'version': CONFIG['app']['version'],
        'time': datetime.now().isoformat()
    }


# ========== Main ==========

if __name__ == '__main__':
    import uvicorn
    host = CONFIG['app']['host']
    port = CONFIG['app']['port']
    debug = CONFIG['app']['debug']

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )
