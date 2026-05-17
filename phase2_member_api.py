"""
心海法律 AI - Phase 2 会员系统 API
会员购买、查询、管理功能
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime
from services.billing import BillingService
from models.db import get_db, UserModel
import os

phase2_bp = Blueprint('phase2_member', __name__, url_prefix='/api/v2')

# 初始化计费服务
def get_billing_service():
    """获取计费服务实例"""
    if not hasattr(g, 'billing_service'):
        config_path = '/home/admin/xinhai_legal_api/config.json'
        if os.path.exists(config_path):
            import json
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            # 默认配置
            config = {
                'billing': {
                    'token_prices': {'basic': 0.002, 'premium': 0.001},
                    'default_free_tokens': 1000,
                    'membership': {
                        'monthly': 30,
                        'quarterly': 80,
                        'yearly': 288,
                        'monthly_tokens': 50000,
                        'quarterly_tokens': 150000,
                        'yearly_tokens': 600000
                    }
                }
            }
        g.billing_service = BillingService(config)
    return g.billing_service


# ============== 会员方案查询 ==============

@phase2_bp.route('/membership/plans', methods=['GET'])
def get_membership_plans():
    """
    获取会员方案列表
    GET /api/v2/membership/plans
    
    Response:
    {
        "code": 200,
        "data": {
            "plans": [...],
            "new_user_bonus": {...}
        }
    }
    """
    try:
        billing = get_billing_service()
        
        plans = []
        for plan_key, plan_info in billing.membership_plans.items():
            plans.append({
                'plan_id': plan_key,
                'name': plan_info['name'],
                'price': plan_info['price'],
                'duration_days': plan_info['duration_days'],
                'tokens_included': plan_info['tokens'],
                'price_per_day': round(plan_info['price'] / plan_info['duration_days'], 2),
                'recommended': plan_key == 'yearly'  # 推荐年卡
            })
        
        # 新人福利
        new_user_bonus = {
            'free_trial_days': 3,
            'free_tokens': 1000,
            'first_month_price': 1  # 首月 1 元
        }
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'plans': plans,
                'new_user_bonus': new_user_bonus
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取会员方案失败：{str(e)}',
            'data': None
        }), 500


# ============== 用户会员状态 ==============

@phase2_bp.route('/membership/status', methods=['GET'])
def get_membership_status():
    """
    获取用户会员状态
    GET /api/v2/membership/status?user_id=1
    
    Response:
    {
        "code": 200,
        "data": {
            "membership": "monthly",
            "membership_name": "月度会员",
            "membership_start": "2026-05-01T00:00:00",
            "membership_end": "2026-06-01T00:00:00",
            "days_remaining": 15,
            "tokens_balance": 45000,
            "is_active": true
        }
    }
    """
    try:
        user_id = request.args.get('user_id', type=int)
        if not user_id:
            return jsonify({
                'code': 400,
                'message': '缺少参数 user_id',
                'data': None
            }), 400
        
        db_path = '/home/admin/xinhai_legal_api/data/xinhai_legal.db'
        user = UserModel.get_by_id(db_path, user_id)
        if not user:
            return jsonify({
                'code': 404,
                'message': '用户不存在',
                'data': None
            }), 404
        
        billing = get_billing_service()
        now = datetime.now()
        
        membership_end = None
        days_remaining = 0
        is_active = False
        
        if user.get('membership_end'):
            try:
                membership_end = datetime.fromisoformat(user['membership_end'])
                delta = membership_end - now
                days_remaining = max(0, delta.days)
                is_active = days_remaining > 0
            except:
                pass
        
        plan_name = billing.membership_plans.get(user.get('membership', 'free'), {}).get('name', '免费版')
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'membership': user.get('membership', 'free'),
                'membership_name': plan_name,
                'membership_start': user.get('membership_start'),
                'membership_end': user.get('membership_end'),
                'days_remaining': days_remaining,
                'tokens_balance': user.get('tokens_balance', 0),
                'is_active': is_active,
                'auto_renew': False  # 暂不支持自动续费
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取会员状态失败：{str(e)}',
            'data': None
        }), 500


# ============== 创建会员订单 ==============

@phase2_bp.route('/membership/order', methods=['POST'])
def create_membership_order():
    """
    创建会员购买订单
    POST /api/v2/membership/order
    
    Body:
    {
        "user_id": 1,
        "plan": "monthly",  // monthly, quarterly, yearly
        "auto_renew": false  // 是否自动续费（暂不支持）
    }
    
    Response:
    {
        "code": 200,
        "data": {
            "order_id": 123,
            "order_no": "M202605170001",
            "plan": "monthly",
            "price": 30.00,
            "duration_days": 30,
            "tokens_granted": 50000,
            "status": "pending",
            "created_at": "2026-05-17T10:00:00",
            "expire_at": "2026-05-17T10:30:00"  // 30 分钟内支付
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'code': 400,
                'message': '请求体不能为空',
                'data': None
            }), 400
        
        user_id = data.get('user_id')
        plan = data.get('plan', 'monthly')
        
        if not user_id:
            return jsonify({
                'code': 400,
                'message': '缺少参数 user_id',
                'data': None
            }), 400
        
        # 确保 user_id 是整数
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            return jsonify({
                'code': 400,
                'message': 'user_id 必须是整数',
                'data': None
            }), 400
        
        db_path = '/home/admin/xinhai_legal_api/data/xinhai_legal.db'
        user = UserModel.get_by_id(db_path, user_id)
        if not user:
            return jsonify({
                'code': 404,
                'message': '用户不存在',
                'data': None
            }), 404
        
        billing = get_billing_service()
        order = billing.create_membership_order(user_id, plan)
        
        if not order:
            return jsonify({
                'code': 400,
                'message': '无效的会员方案',
                'data': None
            }), 400
        
        # 生成订单号
        from datetime import timedelta
        order_no = f"M{datetime.now().strftime('%Y%m%d%H%M%S')}{order['id']:04d}"
        expire_at = datetime.now() + timedelta(minutes=30)
        
        # 更新订单号
        conn = get_db('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
        conn.execute("UPDATE membership_orders SET order_no=? WHERE id=?", (order_no, order['id']))
        conn.commit()
        conn.close()
        
        plan_info = billing.membership_plans[plan]
        
        return jsonify({
            'code': 200,
            'message': '订单创建成功',
            'data': {
                'order_id': order['id'],
                'order_no': order_no,
                'user_id': user_id,
                'plan': plan,
                'plan_name': plan_info['name'],
                'price': plan_info['price'],
                'duration_days': plan_info['duration_days'],
                'tokens_granted': plan_info['tokens'],
                'status': order['status'],
                'created_at': order['created_at'],
                'expire_at': expire_at.isoformat()
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'创建订单失败：{str(e)}',
            'data': None
        }), 500


# ============== 查询订单 ==============

@phase2_bp.route('/membership/order/<int:order_id>', methods=['GET'])
def get_membership_order(order_id):
    """
    查询会员订单详情
    GET /api/v2/membership/order/123
    
    Response:
    {
        "code": 200,
        "data": {
            "order_id": 123,
            "order_no": "M202605170001",
            "plan": "monthly",
            "price": 30.00,
            "status": "pending",
            "created_at": "...",
            "paid_at": null
        }
    }
    """
    try:
        conn = get_db('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
        order = conn.execute(
            "SELECT * FROM membership_orders WHERE id=?", (order_id,)
        ).fetchone()
        conn.close()
        
        if not order:
            return jsonify({
                'code': 404,
                'message': '订单不存在',
                'data': None
            }), 404
        
        order = dict(order)
        # 移除敏感字段
        order.pop('payment_method', None)
        order.pop('transaction_id', None)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': order
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'查询订单失败：{str(e)}',
            'data': None
        }), 500


# ============== 订单列表 ==============

@phase2_bp.route('/membership/orders', methods=['GET'])
def get_membership_orders():
    """
    获取用户订单列表
    GET /api/v2/membership/orders?user_id=1&status=pending&limit=10
    
    Response:
    {
        "code": 200,
        "data": {
            "orders": [...],
            "total": 5
        }
    }
    """
    try:
        user_id = request.args.get('user_id', type=int)
        status = request.args.get('status', '')
        limit = request.args.get('limit', 10, type=int)
        
        if not user_id:
            return jsonify({
                'code': 400,
                'message': '缺少参数 user_id',
                'data': None
            }), 400
        
        conn = get_db('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
        
        query = "SELECT * FROM membership_orders WHERE user_id=?"
        params = [user_id]
        
        if status:
            query += " AND status=?"
            params.append(status)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        orders = conn.execute(query, params).fetchall()
        
        # 获取总数
        count_query = "SELECT COUNT(*) FROM membership_orders WHERE user_id=?"
        count_params = [user_id]
        if status:
            count_query += " AND status=?"
            count_params.append(status)
        
        total = conn.execute(count_query, count_params).fetchone()[0]
        conn.close()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'orders': [dict(o) for o in orders],
                'total': total
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取订单列表失败：{str(e)}',
            'data': None
        }), 500


# ============== 健康检查 ==============

@phase2_bp.route('/membership/health', methods=['GET'])
def membership_health():
    """
    会员系统健康检查
    GET /api/v2/membership/health
    """
    try:
        import sqlite3
        conn = sqlite3.connect('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
        conn.execute("SELECT 1")
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'membership_router': 'available',
            'billing_service': 'available',
            'database': 'connected'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'membership_router': 'unavailable',
            'error': str(e)
        }), 500
