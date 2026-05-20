"""
心海法律 AI - 企业常法 API
企业信息模块（4个）+ 套餐模块（3个），共7个API
"""
from flask import Blueprint, request, jsonify, g
import re
import sqlite3
import time
from datetime import datetime, date, timedelta
import os
import json
import hashlib
import requests
import random
import string

enterprise_bp = Blueprint('enterprise', __name__, url_prefix='/api/enterprise')

# 数据库路径
DB_PATH = '/home/admin/xinhai_legal_api/data/xinhai_legal.db'

# 套餐定价
PLAN_PRICES = {
    'basic': 2980,
    'standard': 6800,
    'professional': 15800
}

# 套餐人数上限
PLAN_MEMBER_LIMITS = {
    'free': 1,
    'basic': 3,
    'standard': 5,
    'professional': 10
}

# 各套餐人工复核限额 (basic=0, standard=10, professional=-1=不限次)
PLAN_MANUAL_REVIEW_LIMITS = {
    'free': 0,
    'basic': 0,
    'standard': 10,
    'professional': -1
}

# 各套餐律师上门次数
PLAN_LAWYER_VISIT_LIMITS = {
    'free': 0,
    'basic': 0,
    'standard': 1,
    'professional': 2
}

# 套餐功能定义
PLAN_FEATURES = {
    'basic': {
        'name': '基础版',
        'price': 2980,
        'unit': '年',
        'target': '个体工商户、微型企业',
        'features': [
            'AI合同审查（不限次）',
            'AI法律咨询（三模型）',
            '合同模板库下载（10+模板）',
            '基础合规体检',
            '无人工服务'
        ],
        'agent_commission': 1490,
        'commission_rate': '50%'
    },
    'standard': {
        'name': '标准版',
        'price': 6800,
        'unit': '年',
        'target': '小型企业（10-50人）',
        'badge': '推荐',
        'features': [
            '基础版全部功能',
            '人工律师审核合同（10次/年）',
            '不限次电话咨询（<4小时响应）',
            '1次律师上门/年',
            '年度合规体检报告（含人工分析）',
            '共享律师池'
        ],
        'agent_commission': 3060,
        'commission_rate': '45%'
    },
    'professional': {
        'name': '专业版',
        'price': 15800,
        'unit': '年',
        'target': '中型企业（50-200人）',
        'features': [
            '标准版全部功能',
            '专属律师（指定1人）',
            '人工复核不限次',
            '2次律师上门/年',
            '诉讼优惠（推荐律师8折）',
            '紧急响应（<1小时）'
        ],
        'agent_commission': 6320,
        'commission_rate': '40%'
    }
}

# 幂等键存储（生产环境应用Redis）
_idempotency_store = {}
_idempotency_expire = 86400  # 24小时


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def get_current_user_id():
    """从请求头中解析当前用户ID"""
    # 开发模式：X-User-Id 头
    dev_user_id = request.headers.get('X-User-Id')
    if dev_user_id:
        try:
            return int(dev_user_id)
        except (ValueError, TypeError):
            pass

    # JWT模式
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None

    token = auth_header[7:]
    try:
        import jwt
        from services.auth import JWT_CONFIG
        payload = jwt.decode(token, JWT_CONFIG['secret'], algorithms=[JWT_CONFIG['algorithm']])
        return payload.get('user_id')
    except Exception:
        # UUID token模式（phase8认证）
        try:
            from phase8_user_auth_api import verify_token
            user = verify_token(token)
            if user:
                return user.get('id')
        except Exception:
            pass
        return None


def require_auth(f):
    """登录校验装饰器"""
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({
                'code': 401,
                'message': '未登录或 Token 已过期',
                'data': None
            }), 401
        g.current_user_id = user_id
        return f(*args, **kwargs)

    return decorated


def validate_credit_code(code):
    """校验统一社会信用代码格式（18位数字或大写字母）"""
    if not code or len(code) != 18:
        return False
    return bool(re.match(r'^[0-9A-Z]{18}$', code))


def validate_scale(scale):
    """校验企业规模"""
    valid_scales = ['<10人', '10-50人', '50-200人', '200人以上']
    return scale in valid_scales


def get_plan_limits(plan):
    """根据套餐获取各项服务限额"""
    review_limit = -1 if plan in ('basic', 'standard', 'professional') else 0
    manual_limit = PLAN_MANUAL_REVIEW_LIMITS.get(plan, 0)
    phone_limit = -1 if plan in ('standard', 'professional') else 0
    visit_limit = PLAN_LAWYER_VISIT_LIMITS.get(plan, 0)
    member_limit = PLAN_MEMBER_LIMITS.get(plan, 1)
    return review_limit, manual_limit, phone_limit, visit_limit, member_limit


# =====================================================================
# 一、企业信息模块（4个API）
# =====================================================================

# ---------- 1.1 创建企业信息 ----------

@enterprise_bp.route('/create', methods=['POST'])
@require_auth
def create_enterprise():
    """
    创建企业信息（首次填写）
    POST /api/enterprise/create
    自动赠送7天基础版体验
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'message': '请求体不能为空', 'data': None}), 400

        user_id = g.current_user_id

        # 必填字段校验
        required_fields = ['name', 'credit_code', 'industry', 'scale', 'contact_name', 'contact_phone']
        missing = [f for f in required_fields if not data.get(f)]
        if missing:
            return jsonify({
                'code': 400,
                'message': f'缺少必填字段: {", ".join(missing)}',
                'data': None
            }), 400

        name = data.get('name', '').strip()
        credit_code = data.get('credit_code', '').strip()
        industry = data.get('industry', '').strip()
        scale = data.get('scale', '').strip()
        contact_name = data.get('contact_name', '').strip()
        contact_phone = data.get('contact_phone', '').strip()

        # 校验信用代码
        if not validate_credit_code(credit_code):
            return jsonify({'code': 400, 'message': '统一社会信用代码格式错误（应为18位数字+大写字母）', 'data': None}), 400

        # 校验企业规模
        if not validate_scale(scale):
            return jsonify({'code': 400, 'message': '企业规模值无效，可选值: <10人, 10-50人, 50-200人, 200人以上', 'data': None}), 400

        # 可选字段
        province = data.get('province', '').strip()
        city = data.get('city', '').strip()
        address = data.get('address', '').strip()
        agent_id = data.get('agent_id')
        partner_id = data.get('partner_id')
        if agent_id is not None:
            try:
                agent_id = int(agent_id)
            except (ValueError, TypeError):
                agent_id = None
        if partner_id is not None:
            try:
                partner_id = int(partner_id)
            except (ValueError, TypeError):
                partner_id = None

        conn = get_db()

        # 检查信用代码是否已存在
        existing = conn.execute(
            "SELECT id FROM enterprise_companies WHERE credit_code=?", (credit_code,)
        ).fetchone()
        if existing:
            conn.close()
            return jsonify({'code': 400, 'message': '统一社会信用代码已注册', 'data': None}), 400

        # 自动赠送7天基础版体验
        today = date.today()
        plan_end = today + timedelta(days=7)
        review_limit, manual_limit, phone_limit, visit_limit, member_limit = get_plan_limits('basic')

        cursor = conn.execute("""
            INSERT INTO enterprise_companies 
                (name, credit_code, industry, scale, contact_name, contact_phone,
                 province, city, address, agent_id, partner_id,
                 plan, plan_start, plan_end,
                 contract_review_used, contract_review_limit,
                 phone_consult_used, lawyer_visit_used,
                 status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    'basic', ?, ?,
                    0, ?,
                    0, 0,
                    'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (
            name, credit_code, industry, scale, contact_name, contact_phone,
            province, city, address, agent_id, partner_id,
            today.isoformat(), plan_end.isoformat(),
            review_limit
        ))

        enterprise_id = cursor.lastrowid

        # 自动将当前用户绑定为管理员
        conn.execute("""
            INSERT INTO enterprise_user_bindings (enterprise_id, user_id, role_in_company, is_active)
            VALUES (?, ?, 'admin', 1)
        """, (enterprise_id, user_id))

        conn.commit()
        conn.close()

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'enterprise_id': enterprise_id,
                'name': name,
                'plan': 'basic',
                'plan_start': today.isoformat(),
                'plan_end': plan_end.isoformat(),
                'trial_days': 7,
                'status': 'active'
            }
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': f'创建企业失败: {str(e)}', 'data': None}), 500


# ---------- 1.2 获取企业信息 ----------

@enterprise_bp.route('/info', methods=['GET'])
@require_auth
def get_enterprise_info():
    """
    获取企业信息+套餐状态+使用统计+成员数
    GET /api/enterprise/info?enterprise_id=1
    """
    try:
        enterprise_id = request.args.get('enterprise_id', type=int)
        if not enterprise_id:
            return jsonify({'code': 400, 'message': '缺少 enterprise_id 参数', 'data': None}), 400

        user_id = g.current_user_id
        conn = get_db()

        # 校验用户是否绑定到此企业
        binding = conn.execute("""
            SELECT role_in_company FROM enterprise_user_bindings 
            WHERE enterprise_id=? AND user_id=? AND is_active=1
        """, (enterprise_id, user_id)).fetchone()
        if not binding:
            conn.close()
            return jsonify({'code': 403, 'message': '您不是该企业成员', 'data': None}), 403

        # 查询企业信息
        row = conn.execute("SELECT * FROM enterprise_companies WHERE id=?", (enterprise_id,)).fetchone()
        if not row:
            conn.close()
            return jsonify({'code': 404, 'message': '企业不存在', 'data': None}), 404

        company = dict(row)

        # 计算剩余天数
        days_remaining = 0
        if company.get('plan_end'):
            try:
                end = datetime.strptime(company['plan_end'], '%Y-%m-%d').date()
                days_remaining = (end - date.today()).days
                if days_remaining < 0:
                    days_remaining = 0
            except (ValueError, TypeError):
                pass

        # 成员数量
        member_count_row = conn.execute("""
            SELECT COUNT(*) as cnt FROM enterprise_user_bindings 
            WHERE enterprise_id=? AND is_active=1
        """, (enterprise_id,)).fetchone()
        member_count = member_count_row['cnt'] if member_count_row else 0

        _, _, _, _, member_limit = get_plan_limits(company.get('plan', 'free'))

        conn.close()

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'id': company['id'],
                'name': company['name'],
                'credit_code': company.get('credit_code'),
                'industry': company.get('industry'),
                'scale': company.get('scale'),
                'contact_name': company.get('contact_name'),
                'contact_phone': company.get('contact_phone'),
                'province': company.get('province'),
                'city': company.get('city'),
                'address': company.get('address'),
                'agent_id': company.get('agent_id'),
                'partner_id': company.get('partner_id'),
                'plan': company.get('plan', 'free'),
                'plan_start': company.get('plan_start'),
                'plan_end': company.get('plan_end'),
                'days_remaining': days_remaining,
                'status': company.get('status', 'active'),
                'contract_review_used': company.get('contract_review_used', 0),
                'contract_review_limit': company.get('contract_review_limit', 0),
                'phone_consult_used': company.get('phone_consult_used', 0),
                'lawyer_visit_used': company.get('lawyer_visit_used', 0),
                'member_count': member_count,
                'member_limit': member_limit,
                'created_at': company.get('created_at')
            }
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取企业信息失败: {str(e)}', 'data': None}), 500


# ---------- 1.3 更新企业信息 ----------

@enterprise_bp.route('/update', methods=['PUT'])
@require_auth
def update_enterprise():
    """
    更新企业信息
    PUT /api/enterprise/update
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'message': '请求体不能为空', 'data': None}), 400

        enterprise_id = data.get('enterprise_id')
        try:
            enterprise_id = int(enterprise_id) if enterprise_id else None
        except (ValueError, TypeError):
            enterprise_id = None
        if not enterprise_id:
            return jsonify({'code': 400, 'message': '缺少 enterprise_id', 'data': None}), 400

        user_id = g.current_user_id
        conn = get_db()

        # 校验操作人是否是管理员
        binding = conn.execute("""
            SELECT role_in_company FROM enterprise_user_bindings 
            WHERE enterprise_id=? AND user_id=? AND is_active=1
        """, (enterprise_id, user_id)).fetchone()
        if not binding:
            conn.close()
            return jsonify({'code': 403, 'message': '您不是该企业成员', 'data': None}), 403
        if binding['role_in_company'] != 'admin':
            conn.close()
            return jsonify({'code': 403, 'message': '仅管理员可更新企业信息', 'data': None}), 403

        # 检查企业是否存在
        row = conn.execute("SELECT id FROM enterprise_companies WHERE id=?", (enterprise_id,)).fetchone()
        if not row:
            conn.close()
            return jsonify({'code': 404, 'message': '企业不存在', 'data': None}), 404

        # 收集可更新字段
        updatable_fields = ['name', 'credit_code', 'industry', 'scale',
                            'contact_name', 'contact_phone', 'province', 'city', 'address']
        updates = []
        params = []

        for field in updatable_fields:
            if field in data and data[field] is not None:
                value = str(data[field]).strip()

                # 校验信用代码
                if field == 'credit_code':
                    if not validate_credit_code(value):
                        conn.close()
                        return jsonify({'code': 400, 'message': '统一社会信用代码格式错误', 'data': None}), 400
                    # 检查唯一性
                    existing = conn.execute(
                        "SELECT id FROM enterprise_companies WHERE credit_code=? AND id!=?",
                        (value, enterprise_id)
                    ).fetchone()
                    if existing:
                        conn.close()
                        return jsonify({'code': 400, 'message': '统一社会信用代码已被其他企业使用', 'data': None}), 400

                # 校验规模
                if field == 'scale' and not validate_scale(value):
                    conn.close()
                    return jsonify({'code': 400, 'message': '企业规模值无效', 'data': None}), 400

                updates.append(f"{field}=?")
                params.append(value)

        if not updates:
            conn.close()
            return jsonify({'code': 400, 'message': '无可更新字段', 'data': None}), 400

        # 执行更新
        updates.append("updated_at=CURRENT_TIMESTAMP")
        sql = f"UPDATE enterprise_companies SET {', '.join(updates)} WHERE id=?"
        params.append(enterprise_id)

        conn.execute(sql, params)
        conn.commit()
        conn.close()

        updated_fields = [f.split('=')[0] for f in updates if '=' in f and f != "updated_at=CURRENT_TIMESTAMP"]

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'enterprise_id': enterprise_id,
                'updated_fields': updated_fields,
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': f'更新企业信息失败: {str(e)}', 'data': None}), 500


# ---------- 1.4 绑定用户到企业 ----------

@enterprise_bp.route('/bind/user', methods=['POST'])
@require_auth
def bind_user_to_enterprise():
    """
    绑定用户到企业（管理员操作）
    POST /api/enterprise/bind/user
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'message': '请求体不能为空', 'data': None}), 400

        enterprise_id = data.get('enterprise_id')
        try:
            enterprise_id = int(enterprise_id) if enterprise_id else None
        except (ValueError, TypeError):
            enterprise_id = None
        target_user_id = data.get('user_id')
        try:
            target_user_id = int(target_user_id) if target_user_id else None
        except (ValueError, TypeError):
            target_user_id = None

        if not enterprise_id or not target_user_id:
            return jsonify({'code': 400, 'message': '缺少 enterprise_id 或 user_id', 'data': None}), 400

        operator_user_id = g.current_user_id
        role_in_company = data.get('role_in_company', 'member')

        # 校验角色值
        valid_roles = ['admin', 'legal', 'hr', 'manager', 'member']
        if role_in_company not in valid_roles:
            return jsonify({'code': 400, 'message': f'角色值无效，可选: {", ".join(valid_roles)}', 'data': None}), 400

        conn = get_db()

        # 检查企业是否存在
        company = conn.execute(
            "SELECT id, plan, status FROM enterprise_companies WHERE id=?",
            (enterprise_id,)
        ).fetchone()
        if not company:
            conn.close()
            return jsonify({'code': 404, 'message': '企业不存在', 'data': None}), 404

        if company['status'] != 'active':
            conn.close()
            return jsonify({'code': 400, 'message': '企业状态异常，无法绑定成员', 'data': None}), 400

        # 校验操作人是否是管理员
        binding = conn.execute("""
            SELECT role_in_company FROM enterprise_user_bindings 
            WHERE enterprise_id=? AND user_id=? AND is_active=1
        """, (enterprise_id, operator_user_id)).fetchone()
        if not binding or binding['role_in_company'] != 'admin':
            conn.close()
            return jsonify({'code': 400, 'message': '操作人不是企业管理员', 'data': None}), 400

        # 检查被绑定用户是否存在
        target_user = conn.execute("SELECT id FROM users WHERE id=?", (target_user_id,)).fetchone()
        if not target_user:
            conn.close()
            return jsonify({'code': 404, 'message': '被绑定的用户不存在', 'data': None}), 404

        # 检查是否已绑定
        existing_binding = conn.execute("""
            SELECT id FROM enterprise_user_bindings
            WHERE enterprise_id=? AND user_id=?
        """, (enterprise_id, target_user_id)).fetchone()
        if existing_binding:
            conn.close()
            return jsonify({'code': 400, 'message': '该用户已绑定此企业', 'data': None}), 400

        # 校验人数上限
        _, _, _, _, member_limit = get_plan_limits(company['plan'])
        current_count = conn.execute("""
            SELECT COUNT(*) as cnt FROM enterprise_user_bindings
            WHERE enterprise_id=? AND is_active=1
        """, (enterprise_id,)).fetchone()['cnt']

        if current_count >= member_limit:
            conn.close()
            return jsonify({
                'code': 400,
                'message': f'已达版本人数上限（{member_limit}人），请升级套餐',
                'data': None
            }), 400

        # 执行绑定
        cursor = conn.execute("""
            INSERT INTO enterprise_user_bindings (enterprise_id, user_id, role_in_company, is_active)
            VALUES (?, ?, ?, 1)
        """, (enterprise_id, target_user_id, role_in_company))

        binding_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'binding_id': binding_id,
                'enterprise_id': enterprise_id,
                'user_id': target_user_id,
                'role_in_company': role_in_company,
                'is_active': 1
            }
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': f'绑定用户失败: {str(e)}', 'data': None}), 500


# =====================================================================
# 二、套餐模块（3个API）
# =====================================================================

# ---------- 2.1 获取套餐列表 ----------

@enterprise_bp.route('/plans', methods=['GET'])
@require_auth
def get_plans():
    """
    获取套餐列表（3档定价+功能对比+代理分润）
    GET /api/enterprise/plans
    """
    try:
        plans = []
        for plan_id, info in PLAN_FEATURES.items():
            plans.append({
                'id': plan_id,
                'name': info['name'],
                'price': info['price'],
                'unit': info['unit'],
                'target': info['target'],
                'badge': info.get('badge'),
                'features': info['features'],
                'agent_commission': info['agent_commission'],
                'commission_rate': info['commission_rate']
            })

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {'plans': plans}
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取套餐列表失败: {str(e)}', 'data': None}), 500


# ---------- 2.2 购买/续费套餐 ----------

def generate_order_no():
    """生成订单号: ENT + 日期(8位) + 序号(4位)"""
    today_str = datetime.now().strftime('%Y%m%d')
    # 使用当前时间戳的后6位 + 随机2位作为序列号
    seq = str(int(time.time()))[-6:]
    rand = ''.join(random.choices(string.digits, k=2))
    return f"ENT{today_str}{seq}{rand}"


@enterprise_bp.route('/order', methods=['POST'])
@require_auth
def create_order():
    """
    购买/续费套餐
    POST /api/enterprise/order
    生成订单→调微信支付
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'message': '请求体不能为空', 'data': None}), 400

        enterprise_id = data.get('enterprise_id')
        try:
            enterprise_id = int(enterprise_id) if enterprise_id else None
        except (ValueError, TypeError):
            enterprise_id = None
        plan = data.get('plan', '').strip().lower()
        payment_method = data.get('payment_method', '').strip().lower()
        user_id = data.get('user_id')
        try:
            user_id = int(user_id) if user_id else g.current_user_id
        except (ValueError, TypeError):
            user_id = g.current_user_id
        idempotency_key = data.get('idempotency_key', '').strip()

        # 参数校验
        if not enterprise_id:
            return jsonify({'code': 400, 'message': '缺少 enterprise_id', 'data': None}), 400
        if plan not in PLAN_PRICES:
            return jsonify({'code': 400, 'message': '无效套餐，可选: basic/standard/professional', 'data': None}), 400
        if payment_method != 'wechat':
            return jsonify({'code': 400, 'message': '支付方式不支持，当前仅支持 wechat', 'data': None}), 400

        # 幂等键检查
        if idempotency_key:
            if idempotency_key in _idempotency_store:
                existing = _idempotency_store[idempotency_key]
                age = time.time() - existing.get('created_at', 0)
                if age < _idempotency_expire:
                    return jsonify({
                        'code': 200,
                        'message': 'success',
                        'data': {
                            'order_id': existing['order_no'],
                            'enterprise_id': enterprise_id,
                            'plan': plan,
                            'amount': existing['amount'],
                            'note': '该订单已存在（幂等键命中）',
                            'payment_params': existing.get('payment_params')
                        }
                    })
                else:
                    del _idempotency_store[idempotency_key]

        conn = get_db()

        # 检查企业
        company = conn.execute(
            "SELECT id, plan, plan_end, status FROM enterprise_companies WHERE id=?",
            (enterprise_id,)
        ).fetchone()
        if not company:
            conn.close()
            return jsonify({'code': 404, 'message': '企业不存在', 'data': None}), 404

        if company['status'] != 'active':
            conn.close()
            return jsonify({'code': 400, 'message': '企业已冻结，不可购买', 'data': None}), 400

        amount = PLAN_PRICES[plan]

        # 生成订单号
        order_no = generate_order_no()

        # 查询用户微信 openid（用于微信支付）
        user_row = conn.execute("SELECT wechat_openid, phone, username FROM users WHERE id=?", (user_id,)).fetchone()
        openid = user_row['wechat_openid'] if user_row else None

        # 插入订单
        product_name = PLAN_FEATURES[plan]['name']

        conn.execute("""
            INSERT INTO orders (order_no, user_id, order_type, product_id, product_name,
                                original_price, final_price, status, created_at, updated_at)
            VALUES (?, ?, 'enterprise_plan', ?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (order_no, user_id, plan, product_name, amount, amount))

        conn.commit()

        # 构造微信支付参数（模拟，实际生产需调微信支付API）
        payment_params = {
            'appId': 'wx73612d8efb98658d',
            'timeStamp': str(int(time.time())),
            'nonceStr': ''.join(random.choices(string.ascii_letters + string.digits, k=16)),
            'package': f'prepay_id=ent{order_no[-10:]}',
            'signType': 'MD5',
            'paySign': hashlib.md5(f'entpay_{order_no}_sign'.encode()).hexdigest()
        }

        # 保存幂等性
        if idempotency_key:
            _idempotency_store[idempotency_key] = {
                'order_no': order_no,
                'amount': amount,
                'payment_params': payment_params,
                'created_at': time.time()
            }

        conn.close()

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'order_id': order_no,
                'enterprise_id': enterprise_id,
                'plan': plan,
                'amount': amount,
                'payment_params': payment_params
            }
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': f'创建订单失败: {str(e)}', 'data': None}), 500


# ---------- 2.3 套餐状态与使用统计 ----------

@enterprise_bp.route('/status', methods=['GET'])
@require_auth
def get_enterprise_status():
    """
    获取套餐状态+使用统计
    GET /api/enterprise/status?enterprise_id=1
    """
    try:
        enterprise_id = request.args.get('enterprise_id', type=int)
        if not enterprise_id:
            return jsonify({'code': 400, 'message': '缺少 enterprise_id 参数', 'data': None}), 400

        user_id = g.current_user_id
        conn = get_db()

        # 校验用户是否绑定到此企业
        binding = conn.execute("""
            SELECT role_in_company FROM enterprise_user_bindings 
            WHERE enterprise_id=? AND user_id=? AND is_active=1
        """, (enterprise_id, user_id)).fetchone()
        if not binding:
            conn.close()
            return jsonify({'code': 403, 'message': '您不是该企业成员', 'data': None}), 403

        # 查询企业信息
        row = conn.execute("SELECT * FROM enterprise_companies WHERE id=?", (enterprise_id,)).fetchone()
        if not row:
            conn.close()
            return jsonify({'code': 404, 'message': '企业不存在', 'data': None}), 404

        company = dict(row)
        plan = company.get('plan', 'free')

        # 计算剩余天数
        days_remaining = 0
        if company.get('plan_end'):
            try:
                end = datetime.strptime(company['plan_end'], '%Y-%m-%d').date()
                days_remaining = (end - date.today()).days
                if days_remaining < 0:
                    days_remaining = 0
            except (ValueError, TypeError):
                pass

        # 各服务限额
        review_limit = company.get('contract_review_limit', 0)
        review_used = company.get('contract_review_used', 0)
        manual_limit = PLAN_MANUAL_REVIEW_LIMITS.get(plan, 0)
        phone_limit = -1 if plan in ('standard', 'professional') else 0
        visit_limit = PLAN_LAWYER_VISIT_LIMITS.get(plan, 0)
        _, _, _, _, member_limit = get_plan_limits(plan)

        # 获取电话咨询次数（从 service_logs）
        phone_used = conn.execute("""
            SELECT COUNT(*) as cnt FROM enterprise_service_logs
            WHERE enterprise_id=? AND service_type='phone_consult'
        """, (enterprise_id,)).fetchone()['cnt']

        # 律师上门次数
        visit_used = company.get('lawyer_visit_used', 0)

        # 成员数
        member_count = conn.execute("""
            SELECT COUNT(*) as cnt FROM enterprise_user_bindings
            WHERE enterprise_id=? AND is_active=1
        """, (enterprise_id,)).fetchone()['cnt']

        # 人工复核次数（从enterprise_contract_reviews表中统计）
        manual_used = 0
        try:
            manual_row = conn.execute("""
                SELECT COUNT(*) as cnt FROM enterprise_contract_reviews
                WHERE enterprise_id=? AND review_type='ai+manual'
            """, (enterprise_id,)).fetchone()
            if manual_row:
                manual_used = manual_row['cnt']
        except Exception:
            pass

        conn.close()

        # 构建使用统计
        usage = {
            'contract_review': {
                'used': review_used,
                'limit': review_limit,
                'remaining_label': '不限次' if review_limit == -1 else str(review_limit - review_used)
            },
            'manual_review': {
                'used': manual_used,
                'limit': manual_limit,
                'remaining': manual_limit - manual_used if manual_limit > 0 else (-1 if manual_limit == -1 else 0)
            },
            'phone_consult': {
                'used': phone_used,
                'limit': phone_limit,
                'remaining_label': '不限次' if phone_limit == -1 else str(phone_limit - phone_used)
            },
            'lawyer_visit': {
                'used': visit_used,
                'limit': visit_limit,
                'remaining': visit_limit - visit_used
            }
        }

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'enterprise_id': enterprise_id,
                'plan': plan,
                'plan_start': company.get('plan_start'),
                'plan_end': company.get('plan_end'),
                'days_remaining': days_remaining,
                'status': company.get('status', 'active'),
                'usage': usage,
                'members': {
                    'current': member_count,
                    'limit': member_limit
                }
            }
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取套餐状态失败: {str(e)}', 'data': None}), 500


# =====================================================================
# v1 兼容蓝图（小程序调用路径 /api/v1/enterprise/*）
# =====================================================================

enterprise_v1_bp = Blueprint('enterprise_v1', __name__, url_prefix='/api/v1/enterprise')


@enterprise_v1_bp.route('/create', methods=['POST'])
def create_enterprise_v1():
    return create_enterprise()


@enterprise_v1_bp.route('/info', methods=['GET'])
def get_enterprise_info_v1():
    return get_enterprise_info()


@enterprise_v1_bp.route('/update', methods=['PUT'])
def update_enterprise_v1():
    return update_enterprise()


@enterprise_v1_bp.route('/bind/user', methods=['POST'])
def bind_user_v1():
    return bind_user_to_enterprise()


@enterprise_v1_bp.route('/plans', methods=['GET'])
def get_plans_v1():
    return get_plans()


@enterprise_v1_bp.route('/order', methods=['POST'])
def create_order_v1():
    return create_order()


@enterprise_v1_bp.route('/status', methods=['GET'])
def get_status_v1():
    return get_enterprise_status()


# =====================================================================
# 二、合同审查模块（5个API）
# =====================================================================

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'jpg', 'jpeg', 'png'}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_file_id():
    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    rand = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f'f_{ts}_{rand}'


# ---------- 3.1 上传合同文件 ----------

@enterprise_bp.route('/contract/upload', methods=['POST'])
@require_auth
def upload_contract():
    """
    上传合同文件
    POST /api/enterprise/contract/upload
    """
    try:
        enterprise_id = request.form.get('enterprise_id', type=int)
        user_id = request.form.get('user_id', type=int)
        if not enterprise_id:
            return jsonify({'code': 400, 'message': '缺少 enterprise_id', 'data': None}), 400

        if 'file' not in request.files:
            return jsonify({'code': 400, 'message': '请上传文件', 'data': None}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'code': 400, 'message': '文件名为空', 'data': None}), 400

        if not allowed_file(file.filename):
            return jsonify({'code': 400, 'message': '不支持的格式，支持: pdf/docx/doc/jpg/png', 'data': None}), 400

        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        if file_size > MAX_FILE_SIZE:
            return jsonify({'code': 400, 'message': '文件超过20MB限制', 'data': None}), 400

        file_id = generate_file_id()
        ext = file.filename.rsplit('.', 1)[1].lower()
        save_dir = f'/home/admin/xinhai_legal_api/enterprise_contracts/{enterprise_id}'
        os.makedirs(save_dir, exist_ok=True)
        save_path = f'{save_dir}/{file_id}.{ext}'
        file.save(save_path)

        file_type_map = {'pdf': 'pdf', 'docx': 'docx', 'doc': 'docx', 'jpg': 'jpg', 'jpeg': 'jpg', 'png': 'jpg'}
        file_type = file_type_map.get(ext, 'other')

        conn = get_db()
        conn.execute("""
            INSERT INTO enterprise_contract_reviews
                (enterprise_id, file_name, file_type, file_size, file_path, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'processing', CURRENT_TIMESTAMP)
        """, (enterprise_id, file.filename, file_type, file_size, save_path))
        cursor = conn.execute("SELECT last_insert_rowid()")
        review_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'review_id': review_id,
                'file_id': file_id,
                'file_name': file.filename,
                'file_type': file_type,
                'file_size': file_size,
                'status': 'processing'
            }
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': f'上传失败: {str(e)}', 'data': None}), 500


# ---------- 3.2 发起合同审查 ----------

@enterprise_bp.route('/contract/review', methods=['POST'])
@require_auth
def start_contract_review():
    """
    发起合同审查（异步）
    POST /api/enterprise/contract/review
    """
    try:
        data = request.get_json()
        enterprise_id = data.get('enterprise_id')
        review_id = data.get('review_id')
        user_id = data.get('user_id')

        if not all([enterprise_id, review_id]):
            return jsonify({'code': 400, 'message': '缺少 enterprise_id 或 review_id', 'data': None}), 400

        conn = get_db()

        # 校验企业状态
        company = conn.execute(
            "SELECT plan, plan_end, status FROM enterprise_companies WHERE id=?",
            (enterprise_id,)
        ).fetchone()
        if not company:
            conn.close()
            return jsonify({'code': 404, 'message': '企业不存在', 'data': None}), 404
        if company['status'] != 'active':
            conn.close()
            return jsonify({'code': 400, 'message': '企业已过期或冻结', 'data': None}), 400

        # 免费模式限1次
        if company['plan'] == 'free':
            used = conn.execute(
                "SELECT COUNT(*) as cnt FROM enterprise_contract_reviews WHERE enterprise_id=? AND status='completed'",
                (enterprise_id,)
            ).fetchone()['cnt']
            if used >= 1:
                conn.close()
                return jsonify({'code': 400, 'message': '免费模式1次体验额度已用完，请购买套餐', 'data': None}), 400

        # Mock AI审查结果
        risk_high = random.randint(0, 2)
        risk_medium = random.randint(1, 4)
        risk_low = random.randint(2, 5)
        risk_json = json.dumps({
            'summary': {'high': risk_high, 'medium': risk_medium, 'low': risk_low, 'total': risk_high + risk_medium + risk_low},
            'risks': [
                {'level': 'high', 'title': '试用期超过法定上限', 'location': '第3条',
                 'content': '试用期约定为6个月，但劳动合同期限为1年，根据《劳动合同法》第19条，试用期不得超过2个月。',
                 'suggestion': '建议将试用期修改为不超过2个月。',
                 'law_basis': '《劳动合同法》第19条'},
                {'level': 'medium', 'title': '加班工资计算基数不明确', 'location': '第7条',
                 'content': '加班工资条款未明确计算基数，存在争议风险。',
                 'suggestion': '建议明确加班工资计算基数为基本工资还是全额工资。'},
                {'level': 'low', 'title': '合同签署日期未填写', 'location': '末尾',
                 'content': '合同末尾的签署日期留空。',
                 'suggestion': '建议在双方签署时填写实际签署日期。'}
            ][:max(1, risk_high)]
        })

        conn.execute("""
            UPDATE enterprise_contract_reviews SET
                status='completed', risk_high=?, risk_medium=?, risk_low=?,
                risk_json=?, completed_at=CURRENT_TIMESTAMP
            WHERE id=?
        """, (risk_high, risk_medium, risk_low, risk_json, review_id))

        # 更新企业统计
        conn.execute("""
            UPDATE enterprise_companies SET
                contract_review_used = contract_review_used + 1,
                last_review_date = DATE('now')
            WHERE id=?
        """, (enterprise_id,))

        conn.commit()
        conn.close()

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'review_id': review_id,
                'status': 'completed',
                'risk_summary': {'high': risk_high, 'medium': risk_medium, 'low': risk_low}
            }
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': f'审查失败: {str(e)}', 'data': None}), 500


# ---------- 3.3 获取审查结果 ----------

@enterprise_bp.route('/contract/result/<int:review_id>', methods=['GET'])
@require_auth
def get_contract_result(review_id):
    """
    获取审查结果
    GET /api/enterprise/contract/result/{id}
    """
    try:
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM enterprise_contract_reviews WHERE id=?", (review_id,)
        ).fetchone()
        if not row:
            conn.close()
            return jsonify({'code': 404, 'message': '审查记录不存在', 'data': None}), 404

        if row['status'] == 'processing':
            conn.close()
            return jsonify({
                'code': 200, 'message': 'success',
                'data': {'review_id': review_id, 'status': 'processing', 'message': 'AI正在逐条分析合同条款...'}
            })

        risks = json.loads(row['risk_json']) if row['risk_json'] else {'risks': []}

        conn.close()
        return jsonify({
            'code': 200, 'message': 'success',
            'data': {
                'review_id': review_id,
                'file_name': row['file_name'],
                'file_type': row['file_type'],
                'status': 'completed',
                'review_type': row['review_type'],
                'risk_summary': risks.get('summary', {}),
                'risks': risks.get('risks', []),
                'completed_at': row['completed_at']
            }
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取结果失败: {str(e)}', 'data': None}), 500


# ---------- 3.4 审查历史列表 ----------

@enterprise_bp.route('/contract/history', methods=['GET'])
@require_auth
def get_contract_history():
    """
    审查历史列表
    GET /api/enterprise/contract/history
    """
    try:
        enterprise_id = request.args.get('enterprise_id', type=int)
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        status_filter = request.args.get('status')

        if not enterprise_id:
            return jsonify({'code': 400, 'message': '缺少 enterprise_id', 'data': None}), 400

        conn = get_db()
        where = "WHERE enterprise_id=?"
        params = [enterprise_id]
        if status_filter:
            where += " AND status=?"
            params.append(status_filter)

        total = conn.execute(f"SELECT COUNT(*) as cnt FROM enterprise_contract_reviews {where}", params).fetchone()['cnt']
        offset = (page - 1) * page_size
        rows = conn.execute(
            f"SELECT id, file_name, file_type, status, risk_high, risk_medium, risk_low, review_type, created_at, completed_at "
            f"FROM enterprise_contract_reviews {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset]
        ).fetchall()

        conn.close()
        return jsonify({
            'code': 200, 'message': 'success',
            'data': {
                'total': total, 'page': page, 'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size,
                'list': [dict(r) for r in rows]
            }
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取历史失败: {str(e)}', 'data': None}), 500


# ---------- 3.5 下载审查报告 ----------

@enterprise_bp.route('/contract/download/<int:review_id>', methods=['GET'])
@require_auth
def download_contract_report(review_id):
    """
    下载审查报告（返回PDF文件流）
    GET /api/enterprise/contract/download/{id}
    """
    try:
        from flask import send_file
        conn = get_db()
        row = conn.execute(
            "SELECT file_name, file_path FROM enterprise_contract_reviews WHERE id=?", (review_id,)
        ).fetchone()
        conn.close()
        if not row:
            return jsonify({'code': 404, 'message': '审查记录不存在', 'data': None}), 404
        if not row['file_path'] or not os.path.exists(row['file_path']):
            return jsonify({'code': 404, 'message': '文件不存在', 'data': None}), 404

        return send_file(
            row['file_path'],
            as_attachment=True,
            download_name=f'审查报告_{row["file_name"]}'
        )

    except Exception as e:
        return jsonify({'code': 500, 'message': f'下载失败: {str(e)}', 'data': None}), 500


# =====================================================================
# 三、服务模块（3个API）
# =====================================================================

# ---------- 4.1 申请人工复核 ----------

@enterprise_bp.route('/service/apply-review', methods=['POST'])
@require_auth
def apply_manual_review():
    """
    申请人工复核合同
    POST /api/enterprise/service/apply-review
    """
    try:
        data = request.get_json()
        enterprise_id = data.get('enterprise_id')
        review_id = data.get('review_id')
        user_id = data.get('user_id', g.current_user_id)
        note = data.get('note', '')

        if not all([enterprise_id, review_id]):
            return jsonify({'code': 400, 'message': '缺少 enterprise_id 或 review_id', 'data': None}), 400

        conn = get_db()
        company = conn.execute(
            "SELECT plan, status FROM enterprise_companies WHERE id=?", (enterprise_id,)
        ).fetchone()
        if not company:
            conn.close()
            return jsonify({'code': 404, 'message': '企业不存在', 'data': None}), 404
        if company['status'] != 'active':
            conn.close()
            return jsonify({'code': 400, 'message': '企业已过期或冻结', 'data': None}), 400

        plan = company['plan']
        manual_limit = PLAN_MANUAL_REVIEW_LIMITS.get(plan, 0)
        if manual_limit == 0:
            conn.close()
            return jsonify({'code': 400, 'message': '基础版不可申请人工复核，请升级套餐', 'data': None}), 400

        if manual_limit > 0:
            used = conn.execute(
                "SELECT COUNT(*) as cnt FROM enterprise_service_logs WHERE enterprise_id=? AND service_type='contract_review'",
                (enterprise_id,)
            ).fetchone()['cnt']
            if used >= manual_limit:
                conn.close()
                return jsonify({'code': 400, 'message': '人工复核次数已用完（本年限10次），超出可¥200/次购买', 'data': None}), 400

        # 更新审查记录
        conn.execute(
            "UPDATE enterprise_contract_reviews SET review_type='ai+manual' WHERE id=?",
            (review_id,)
        )
        # 写入服务日志
        conn.execute("""
            INSERT INTO enterprise_service_logs (enterprise_id, service_type, summary, created_at)
            VALUES (?, 'contract_review', ?, CURRENT_TIMESTAMP)
        """, (enterprise_id, f'申请人工复核审查记录#{review_id}'))
        cursor = conn.execute("SELECT last_insert_rowid()")
        service_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()

        return jsonify({
            'code': 200, 'message': 'success',
            'data': {
                'service_id': service_id, 'review_id': review_id,
                'service_type': 'contract_review', 'status': 'pending',
                'estimated_hours': 24,
                'message': '已提交人工复核申请，预计24小时内完成。结果将通过服务通知告知您。'
            }
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': f'申请失败: {str(e)}', 'data': None}), 500


# ---------- 4.2 申请律师上门 ----------

@enterprise_bp.route('/service/request-visit', methods=['POST'])
@require_auth
def request_lawyer_visit():
    """
    申请律师上门
    POST /api/enterprise/service/request-visit
    """
    try:
        data = request.get_json()
        enterprise_id = data.get('enterprise_id')
        user_id = data.get('user_id', g.current_user_id)
        address = data.get('address')
        preferred_date = data.get('preferred_date')
        topic = data.get('topic', '')

        if not all([enterprise_id, address]):
            return jsonify({'code': 400, 'message': '缺少 enterprise_id 或 address', 'data': None}), 400

        conn = get_db()
        company = conn.execute(
            "SELECT plan, status, lawyer_visit_used FROM enterprise_companies WHERE id=?",
            (enterprise_id,)
        ).fetchone()
        if not company:
            conn.close()
            return jsonify({'code': 404, 'message': '企业不存在', 'data': None}), 404
        if company['status'] != 'active':
            conn.close()
            return jsonify({'code': 400, 'message': '企业已过期或冻结', 'data': None}), 400

        plan = company['plan']
        visit_limit = PLAN_LAWYER_VISIT_LIMITS.get(plan, 0)
        if visit_limit == 0:
            conn.close()
            return jsonify({'code': 400, 'message': '不可申请律师上门', 'data': None}), 400

        if company['lawyer_visit_used'] >= visit_limit and visit_limit > 0:
            conn.close()
            return jsonify({'code': 400, 'message': '上门次数已用完', 'data': None}), 400

        conn.execute("""
            INSERT INTO enterprise_service_logs (enterprise_id, service_type, summary, created_at)
            VALUES (?, 'lawyer_visit', ?, CURRENT_TIMESTAMP)
        """, (enterprise_id, f'律师上门: {address}, 主题: {topic}'))
        cursor = conn.execute("SELECT last_insert_rowid()")
        service_id = cursor.fetchone()[0]

        conn.execute(
            "UPDATE enterprise_companies SET lawyer_visit_used = lawyer_visit_used + 1 WHERE id=?",
            (enterprise_id,)
        )
        conn.commit()
        conn.close()

        return jsonify({
            'code': 200, 'message': 'success',
            'data': {
                'service_id': service_id, 'service_type': 'lawyer_visit',
                'status': 'pending',
                'message': '已提交上门服务申请，律师将在3个工作日内联系您确认时间。'
            }
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': f'申请失败: {str(e)}', 'data': None}), 500


# ---------- 4.3 服务记录列表 ----------

@enterprise_bp.route('/service/logs', methods=['GET'])
@require_auth
def get_service_logs():
    """
    服务记录列表
    GET /api/enterprise/service/logs
    """
    try:
        enterprise_id = request.args.get('enterprise_id', type=int)
        service_type = request.args.get('service_type')
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)

        if not enterprise_id:
            return jsonify({'code': 400, 'message': '缺少 enterprise_id', 'data': None}), 400

        conn = get_db()
        where = "WHERE enterprise_id=?"
        params = [enterprise_id]
        if service_type:
            where += " AND service_type=?"
            params.append(service_type)

        total = conn.execute(f"SELECT COUNT(*) as cnt FROM enterprise_service_logs {where}", params).fetchone()['cnt']
        offset = (page - 1) * page_size
        rows = conn.execute(
            f"SELECT * FROM enterprise_service_logs {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset]
        ).fetchall()

        conn.close()
        return jsonify({
            'code': 200, 'message': 'success',
            'data': {
                'total': total, 'page': page, 'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size,
                'list': [dict(r) for r in rows]
            }
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取服务记录失败: {str(e)}', 'data': None}), 500


# =====================================================================
# 四、合同模板库模块（3个API）
# =====================================================================

# ---------- 5.1 获取模板列表 ----------

@enterprise_bp.route('/templates', methods=['GET'])
@require_auth
def get_templates():
    """
    获取合同模板列表
    GET /api/enterprise/templates
    """
    try:
        enterprise_id = request.args.get('enterprise_id', type=int)
        category = request.args.get('category')
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)

        conn = get_db()

        # 判断套餐以确定can_download
        plan = 'free'
        if enterprise_id:
            company = conn.execute(
                "SELECT plan FROM enterprise_companies WHERE id=?", (enterprise_id,)
            ).fetchone()
            if company:
                plan = company['plan']
        can_download = plan != 'free'

        where = "WHERE is_active=1"
        params = []
        if category:
            where += " AND category=?"
            params.append(category)

        total = conn.execute(f"SELECT COUNT(*) as cnt FROM enterprise_templates {where}", params).fetchone()['cnt']
        offset = (page - 1) * page_size
        rows = conn.execute(
            f"SELECT id, name, category, description, download_required_plan, is_active, created_at "
            f"FROM enterprise_templates {where} ORDER BY id ASC LIMIT ? OFFSET ?",
            params + [page_size, offset]
        ).fetchall()

        result_list = []
        for r in rows:
            item = dict(r)
            item['can_download'] = can_download
            item['can_preview'] = True
            result_list.append(item)

        conn.close()
        return jsonify({
            'code': 200, 'message': 'success',
            'data': {
                'total': total, 'page': page, 'page_size': page_size,
                'list': result_list
            }
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取模板列表失败: {str(e)}', 'data': None}), 500


# ---------- 5.2 获取模板详情 ----------

@enterprise_bp.route('/templates/<int:template_id>', methods=['GET'])
@require_auth
def get_template_detail(template_id):
    """
    获取模板详情
    GET /api/enterprise/templates/{id}
    """
    try:
        conn = get_db()
        row = conn.execute(
            "SELECT id, name, category, description, content, download_required_plan FROM enterprise_templates WHERE id=? AND is_active=1",
            (template_id,)
        ).fetchone()
        conn.close()

        if not row:
            return jsonify({'code': 404, 'message': '模板不存在', 'data': None}), 404

        data = dict(row)
        data['content_preview'] = row['content'][:200] + '...' if len(row['content']) > 200 else row['content']
        data['can_download'] = False  # 由前端根据套餐判断
        data['fields'] = [
            {'name': '甲方名称', 'type': 'text', 'required': True},
            {'name': '乙方名称', 'type': 'text', 'required': True}
        ]

        return jsonify({'code': 200, 'message': 'success', 'data': data})

    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取模板详情失败: {str(e)}', 'data': None}), 500


# ---------- 5.3 下载模板 ----------

@enterprise_bp.route('/templates/<int:template_id>/download', methods=['GET'])
@require_auth
def download_template(template_id):
    """
    下载模板文件
    GET /api/enterprise/templates/{id}/download
    """
    try:
        from flask import send_file
        enterprise_id = request.args.get('enterprise_id', type=int)

        conn = get_db()
        row = conn.execute(
            "SELECT name, file_path, download_required_plan FROM enterprise_templates WHERE id=? AND is_active=1",
            (template_id,)
        ).fetchone()

        # 校验套餐
        if enterprise_id:
            company = conn.execute("SELECT plan FROM enterprise_companies WHERE id=?", (enterprise_id,)).fetchone()
            if not company or company['plan'] == 'free':
                conn.close()
                return jsonify({'code': 403, 'message': '免费模式不可下载模板，请购买套餐', 'data': None}), 403

        conn.close()
        if not row:
            return jsonify({'code': 404, 'message': '模板不存在', 'data': None}), 404

        file_path = row['file_path']
        if file_path and os.path.exists(file_path):
            return send_file(file_path, as_attachment=True, download_name=f'{row["name"]}.docx')

        # 无文件时返回文本内容
        return jsonify({'code': 200, 'message': 'success', 'data': {'name': row['name'], 'content': '模板内容'}})

    except Exception as e:
        return jsonify({'code': 500, 'message': f'下载失败: {str(e)}', 'data': None}), 500


# =====================================================================
# 五、合规体检模块（3个API）
# =====================================================================

# ---------- 6.1 发起合规体检 ----------

@enterprise_bp.route('/compliance/check', methods=['POST'])
@require_auth
def start_compliance_check():
    """
    发起合规体检
    POST /api/enterprise/compliance/check
    """
    try:
        data = request.get_json()
        enterprise_id = data.get('enterprise_id')
        check_type = data.get('check_type')
        user_id = data.get('user_id', g.current_user_id)

        valid_types = ['labor', 'contract', 'overall']
        if check_type not in valid_types:
            return jsonify({'code': 400, 'message': '无效的体检类型，可选: labor/contract/overall', 'data': None}), 400

        conn = get_db()
        company = conn.execute(
            "SELECT plan, status FROM enterprise_companies WHERE id=?", (enterprise_id,)
        ).fetchone()
        if not company:
            conn.close()
            return jsonify({'code': 404, 'message': '企业不存在', 'data': None}), 404
        if company['status'] != 'active':
            conn.close()
            return jsonify({'code': 400, 'message': '企业已过期或冻结', 'data': None}), 400

        # overall类型限标准版以上
        if check_type == 'overall' and company['plan'] in ('free', 'basic'):
            conn.close()
            return jsonify({'code': 400, 'message': '企业综合体检需要标准版及以上套餐', 'data': None}), 400

        # Mock体检结果
        check_type_labels = {'labor': '劳动用工合规体检', 'contract': '合同合规体检', 'overall': '企业综合体检'}
        score = random.randint(60, 85)
        result_json = json.dumps({
            'dimensions': [
                {'name': '劳动合同签订', 'score': score, 'status': 'warning' if score < 75 else 'safe',
                 'detail': '已签订劳动合同，但部分条款需优化'},
                {'name': '社保公积金', 'score': score - 10, 'status': 'warning',
                 'detail': '部分员工未按实际工资基数缴纳社保'}
            ],
            'risk_count': {'high': 0 if score > 70 else 1, 'medium': 1 if score < 80 else 0, 'low': 2}
        })

        conn.execute("""
            INSERT INTO enterprise_compliance_checks
                (enterprise_id, check_type, score, result_json, suggestions, created_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (enterprise_id, check_type, score, result_json,
              f'1. 建议完善{check_type_labels.get(check_type, "")}的相关制度\n2. 建议定期进行合规复查'))
        cursor = conn.execute("SELECT last_insert_rowid()")
        check_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()

        return jsonify({
            'code': 200, 'message': 'success',
            'data': {
                'check_id': check_id, 'check_type': check_type,
                'status': 'completed', 'score': score,
                'estimated_seconds': 10
            }
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': f'发起体检失败: {str(e)}', 'data': None}), 500


# ---------- 6.2 获取体检结果 ----------

@enterprise_bp.route('/compliance/result/<int:check_id>', methods=['GET'])
@require_auth
def get_compliance_result(check_id):
    """
    获取体检结果
    GET /api/enterprise/compliance/result/{id}
    """
    try:
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM enterprise_compliance_checks WHERE id=?", (check_id,)
        ).fetchone()
        conn.close()

        if not row:
            return jsonify({'code': 404, 'message': '体检记录不存在', 'data': None}), 404

        data = dict(row)
        if row['result_json']:
            data['result'] = json.loads(row['result_json'])
        del data['result_json']

        return jsonify({'code': 200, 'message': 'success', 'data': data})

    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取结果失败: {str(e)}', 'data': None}), 500


# ---------- 6.3 合规体检历史 ----------

@enterprise_bp.route('/compliance/history', methods=['GET'])
@require_auth
def get_compliance_history():
    """
    合规体检历史
    GET /api/enterprise/compliance/history
    """
    try:
        enterprise_id = request.args.get('enterprise_id', type=int)
        check_type = request.args.get('check_type')
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)

        if not enterprise_id:
            return jsonify({'code': 400, 'message': '缺少 enterprise_id', 'data': None}), 400

        conn = get_db()
        where = "WHERE enterprise_id=?"
        params = [enterprise_id]
        if check_type:
            where += " AND check_type=?"
            params.append(check_type)

        total = conn.execute(f"SELECT COUNT(*) as cnt FROM enterprise_compliance_checks {where}", params).fetchone()['cnt']
        offset = (page - 1) * page_size
        rows = conn.execute(
            f"SELECT id, check_type, score, lawyer_review, created_at "
            f"FROM enterprise_compliance_checks {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset]
        ).fetchall()

        conn.close()
        return jsonify({
            'code': 200, 'message': 'success',
            'data': {
                'total': total, 'page': page, 'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size,
                'list': [dict(r) for r in rows]
            }
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取历史失败: {str(e)}', 'data': None}), 500


# =====================================================================
# v1 兼容路由（二~五：合同审查/服务/模板/合规体检）
# =====================================================================

@enterprise_v1_bp.route('/contract/upload', methods=['POST'])
def upload_contract_v1():
    return upload_contract()


@enterprise_v1_bp.route('/contract/review', methods=['POST'])
def start_contract_review_v1():
    return start_contract_review()


@enterprise_v1_bp.route('/contract/result/<int:review_id>', methods=['GET'])
def get_contract_result_v1(review_id):
    return get_contract_result(review_id)


@enterprise_v1_bp.route('/contract/history', methods=['GET'])
def get_contract_history_v1():
    return get_contract_history()


@enterprise_v1_bp.route('/contract/download/<int:review_id>', methods=['GET'])
def download_contract_report_v1(review_id):
    return download_contract_report(review_id)


@enterprise_v1_bp.route('/service/apply-review', methods=['POST'])
def apply_manual_review_v1():
    return apply_manual_review()


@enterprise_v1_bp.route('/service/request-visit', methods=['POST'])
def request_lawyer_visit_v1():
    return request_lawyer_visit()


@enterprise_v1_bp.route('/service/logs', methods=['GET'])
def get_service_logs_v1():
    return get_service_logs()


@enterprise_v1_bp.route('/templates', methods=['GET'])
def get_templates_v1():
    return get_templates()


@enterprise_v1_bp.route('/templates/<int:template_id>', methods=['GET'])
def get_template_detail_v1(template_id):
    return get_template_detail(template_id)


@enterprise_v1_bp.route('/templates/<int:template_id>/download', methods=['GET'])
def download_template_v1(template_id):
    return download_template(template_id)


@enterprise_v1_bp.route('/compliance/check', methods=['POST'])
def start_compliance_check_v1():
    return start_compliance_check()


@enterprise_v1_bp.route('/compliance/result/<int:check_id>', methods=['GET'])
def get_compliance_result_v1(check_id):
    return get_compliance_result(check_id)


@enterprise_v1_bp.route('/compliance/history', methods=['GET'])
def get_compliance_history_v1():
    return get_compliance_history()


# ====================================================================
# 阶段二：代理推企业常法 — 4个接口
# ====================================================================

"""🔧 辅助函数：从请求头获取代理（合伙人）ID"""
def get_agent_partner_id():
    """优先从 X-User-Id 头取（dev模式），其次从 JWT/UUID token 解析"""
    user_id = request.headers.get('X-User-Id')
    if user_id:
        try:
            return int(user_id)
        except:
            pass
    # 从UUID token解析（简化版，复用verify_token逻辑）
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        token = auth[7:]
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM auth_tokens WHERE token = ?", (token,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return row[0]
    return None


# ---------- ① 线索录入 ----------
@enterprise_bp.route('/agent/lead', methods=['POST'])
def agent_submit_lead():
    """代理提交企业线索→写入enterprise_companies（待激活状态）"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求体为空', 'code': 400}), 400

        name = (data.get('name') or '').strip()
        contact_name = (data.get('contact_name') or '').strip()
        contact_phone = (data.get('contact_phone') or '').strip()
        scale = (data.get('scale') or '').strip()
        intent_plan = (data.get('intent_plan') or 'free').strip()

        if not name or not contact_name or not contact_phone:
            return jsonify({'error': '企业名称、联系人、联系电话为必填', 'code': 400}), 400

        agent_id = get_agent_partner_id()
        if not agent_id:
            return jsonify({'error': '未认证的代理', 'code': 401}), 401

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 检查是否已存在（同名企业+同一代理去重）
        cursor.execute(
            "SELECT id FROM enterprise_companies WHERE name = ? AND agent_id = ? AND status = 'lead'",
            (name, agent_id)
        )
        existing = cursor.fetchone()
        if existing:
            conn.close()
            return jsonify({'error': '该企业线索已提交', 'code': 409, 'company_id': existing[0]}), 409

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # 默认状态为 lead（线索），没有开通任何套餐
        cursor.execute("""
            INSERT INTO enterprise_companies 
            (name, contact_name, contact_phone, scale, industry, agent_id, 
             plan, plan_start, plan_end, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'free', NULL, NULL, 'lead', ?, ?)
        """, (name, contact_name, contact_phone, scale, data.get('industry', ''), 
              agent_id, now, now))

        company_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return jsonify({
            'code': 200,
            'message': '线索提交成功',
            'company_id': company_id,
            'company_name': name,
            'intent_plan': intent_plan
        }), 200

    except Exception as e:
        return jsonify({'error': f'提交失败: {str(e)}', 'code': 500}), 500


# ---------- ② 我的客户列表 ----------
@enterprise_bp.route('/agent/clients', methods=['GET'])
def agent_get_clients():
    """代理的企业客户列表（包含线索和已转化企业）"""
    try:
        agent_id = get_agent_partner_id()
        if not agent_id:
            return jsonify({'error': '未认证的代理', 'code': 401}), 401

        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        status = request.args.get('status', '').strip()
        search = request.args.get('search', '').strip()
        offset = (page - 1) * limit

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        where = "WHERE agent_id = ?"
        params = [agent_id]

        if status:
            where += " AND status = ?"
            params.append(status)
        if search:
            where += " AND (name LIKE ? OR contact_name LIKE ? OR contact_phone LIKE ?)"
            s = f'%{search}%'
            params.extend([s, s, s])

        # 查询总数
        cursor.execute(f"SELECT COUNT(*) as total FROM enterprise_companies {where}", params)
        total = cursor.fetchone()['total']

        # 查询列表
        cursor.execute(f"""
            SELECT id, name, contact_name, contact_phone, scale, industry,
                   plan, status, plan_start, plan_end, created_at,
                   contract_review_used, contract_review_limit,
                   phone_consult_used, lawyer_visit_used
            FROM enterprise_companies {where}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, params + [limit, offset])
        rows = cursor.fetchall()
        conn.close()

        clients = []
        for r in rows:
            clients.append({
                'id': r['id'],
                'name': r['name'],
                'contact_name': r['contact_name'],
                'contact_phone': r['contact_phone'],
                'scale': r['scale'],
                'industry': r['industry'],
                'plan': r['plan'],
                'status': r['status'],
                'plan_start': r['plan_start'],
                'plan_end': r['plan_end'],
                'created_at': r['created_at'],
                'used': {
                    'contract_review': r['contract_review_used'],
                    'contract_review_limit': r['contract_review_limit'],
                    'phone_consult': r['phone_consult_used'],
                    'lawyer_visit': r['lawyer_visit_used'],
                }
            })

        return jsonify({
            'code': 200,
            'data': {
                'clients': clients,
                'total': total,
                'page': page,
                'limit': limit,
                'pages': (total + limit - 1) // limit
            }
        }), 200

    except Exception as e:
        return jsonify({'error': f'查询失败: {str(e)}', 'code': 500}), 500


# ---------- ③ 推广话术匹配 ----------
@enterprise_bp.route('/agent/scripts', methods=['GET'])
def agent_get_scripts():
    """获取企业常法推广话术模板（支持按场景关键词匹配）"""
    try:
        scene = request.args.get('scene', '').strip()
        
        scripts = [
            {
                'id': 1,
                'scene': 'general',
                'trigger_words': '公司,企业,合同,法务',
                'title': '企业常法通用推荐',
                'content': '推荐您了解一下心海法律AI的「企业法律顾问」服务，AI合同审查、合规体检、模板库一站式解决，7天免费体验！',
                'card_title': '心海法律AI · 企业法律顾问',
                'card_desc': 'AI合同审查 | 合规体检 | 法律咨询 | 模板库'
            },
            {
                'id': 2,
                'scene': 'contract',
                'trigger_words': '合同,协议,条款,违约',
                'title': '合同审查推荐',
                'content': '企业合同法律风险不容忽视！心海法律AI支持上传合同智能审查，AI自动识别风险条款，生成审查报告，帮企业规避合同陷阱。',
                'card_title': 'AI合同智能审查',
                'card_desc': '上传合同 → AI审查 → 风险报告 → 一键下载'
            },
            {
                'id': 3,
                'scene': 'employee',
                'trigger_words': '员工,劳动,社保,工资',
                'title': '劳动合规推荐',
                'content': '企业用工合规是大事！心海法律AI提供劳动合规体检，覆盖社保公积金、劳动合同、加班费、离职赔偿等常见场景，快速识别风险点。',
                'card_title': '劳动合规体检',
                'card_desc': '用工风险全扫描，合规建议即时出'
            },
            {
                'id': 4,
                'scene': 'compliance',
                'trigger_words': '合规,检查,风险,资质',
                'title': '企业合规体检推荐',
                'content': '定期做企业合规体检，防患于未然。支持劳动用工、知识产权、数据合规三大类体检，AI自动出具结果和改进建议。',
                'card_title': '企业合规体检',
                'card_desc': '三大类体检 → AI评估 → 改进建议'
            },
            {
                'id': 5,
                'scene': 'startup',
                'trigger_words': '创业,注册,开办,新公司',
                'title': '创业企业推荐',
                'content': '新公司刚起步，法务开支有限？心海法律AI企业常法套餐最低¥2,980/年，AI合同审查不限次，为创业公司降本增效。',
                'card_title': '创业企业法务方案',
                'card_desc': '低成本高保障，¥2,980/年起'
            },
        ]

        # 如果有场景匹配，优先展示匹配场景
        if scene:
            matched = [s for s in scripts if s['scene'] == scene]
            if matched:
                return jsonify({'code': 200, 'data': matched, 'matched_scene': scene}), 200

        return jsonify({'code': 200, 'data': scripts, 'total': len(scripts)}), 200

    except Exception as e:
        return jsonify({'error': f'获取失败: {str(e)}', 'code': 500}), 500


# ---------- ④ 企业常法介绍卡片 ----------
@enterprise_bp.route('/agent/card', methods=['GET'])
def agent_get_card():
    """获取企业常法产品介绍卡片（分享给客户）"""
    try:
        plan = request.args.get('plan', '').strip()
        plans_info = {
            'free': {
                'name': '免费体验版',
                'price': '免费7天',
                'features': ['AI合同审查（1次）', '合同模板库（预览）', '合规体检（1次）', '法律AI咨询'],
                'highlight': '0元试用，体验企业智能法务'
            },
            'basic': {
                'name': '基础版',
                'price': '¥2,980/年',
                'features': ['AI合同审查（不限次）', '10+合同模板下载', '合规体检（3次/年）', '法律AI咨询', '3人可绑定'],
                'highlight': '小微企业法务刚需，AI全覆盖'
            },
            'standard': {
                'name': '标准版',
                'price': '¥6,800/年',
                'features': ['AI合同审查（不限次）', '人工合同复核（10次/年）', '20+合同模板下载', '合规体检（6次/年）', '律师电话咨询（3次/年）', '5人可绑定'],
                'highlight': 'AI+人工双保障，合同无忧'
            },
            'professional': {
                'name': '专业版',
                'price': '¥15,800/年',
                'features': ['AI合同审查（不限次）', '人工合同复核（不限次）', '全部合同模板', '合规体检（不限次）', '律师电话咨询（不限次）', '律师上门（2次/年）', '10人可绑定', '专属服务群'],
                'highlight': '全方位法务保障，适合发展中企业'
            },
        }

        if plan and plan in plans_info:
            return jsonify({'code': 200, 'data': plans_info[plan]}), 200

        # 返回全部套餐简介
        return jsonify({
            'code': 200,
            'data': plans_info,
            'total': len(plans_info)
        }), 200

    except Exception as e:
        return jsonify({'error': f'获取失败: {str(e)}', 'code': 500}), 500


# ---------- v1兼容路由 ----------
@enterprise_v1_bp.route('/agent/lead', methods=['POST'])
def agent_submit_lead_v1():
    return agent_submit_lead()

@enterprise_v1_bp.route('/agent/clients', methods=['GET'])
def agent_get_clients_v1():
    return agent_get_clients()

@enterprise_v1_bp.route('/agent/scripts', methods=['GET'])
def agent_get_scripts_v1():
    return agent_get_scripts()

@enterprise_v1_bp.route('/agent/card', methods=['GET'])
def agent_get_card_v1():
    return agent_get_card()
