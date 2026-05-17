"""
心海法律 AI - Phase 2 Token 计费 API
Token 查询、消费、购买功能
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime
from services.billing import BillingService
from models.db import get_db, UserModel
import os
import json

phase2_token_bp = Blueprint('phase2_token', __name__, url_prefix='/api/v2/token')


def get_billing_service():
    """获取计费服务实例"""
    if not hasattr(g, 'billing_service'):
        config_path = '/home/admin/xinhai_legal_api/config.json'
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
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


# ============== Token 余额查询 ==============

@phase2_token_bp.route('/balance', methods=['GET'])
def get_token_balance():
    """
    查询用户 Token 余额
    GET /api/v2/token/balance?user_id=1
    
    Response:
    {
        "code": 200,
        "data": {
            "user_id": 1,
            "tokens_balance": 45000,
            "membership": "monthly",
            "token_price": 0.001,
            "estimated_value": 45.00
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
        
        user = UserModel.get_by_id(user_id)
        if not user:
            return jsonify({
                'code': 404,
                'message': '用户不存在',
                'data': None
            }), 404
        
        billing = get_billing_service()
        token_price = billing.get_token_price(user_id)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'user_id': user_id,
                'tokens_balance': user.get('tokens_balance', 0),
                'membership': user.get('membership', 'free'),
                'token_price': token_price,
                'estimated_value': round(user.get('tokens_balance', 0) * token_price / 1000, 2)
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'查询余额失败：{str(e)}',
            'data': None
        }), 500


# ============== Token 消费记录 ==============

@phase2_token_bp.route('/transactions', methods=['GET'])
def get_token_transactions():
    """
    查询用户 Token 交易记录
    GET /api/v2/token/transactions?user_id=1&limit=20&offset=0
    
    Response:
    {
        "code": 200,
        "data": {
            "transactions": [
                {
                    "id": 1,
                    "amount": -1000,
                    "balance_after": 45000,
                    "transaction_type": "consultation",
                    "description": "AI 法律咨询",
                    "created_at": "2026-05-17T10:00:00"
                }
            ],
            "total": 50
        }
    }
    """
    try:
        user_id = request.args.get('user_id', type=int)
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        tx_type = request.args.get('type', '')
        
        if not user_id:
            return jsonify({
                'code': 400,
                'message': '缺少参数 user_id',
                'data': None
            }), 400
        
        conn = get_db('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
        
        query = "SELECT * FROM token_transactions WHERE user_id=?"
        params = [user_id]
        
        if tx_type:
            query += " AND transaction_type=?"
            params.append(tx_type)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        transactions = conn.execute(query, params).fetchall()
        
        # 获取总数
        count_query = "SELECT COUNT(*) FROM token_transactions WHERE user_id=?"
        count_params = [user_id]
        if tx_type:
            count_query += " AND transaction_type=?"
            count_params.append(tx_type)
        
        total = conn.execute(count_query, count_params).fetchone()[0]
        conn.close()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'transactions': [dict(t) for t in transactions],
                'total': total,
                'limit': limit,
                'offset': offset
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'查询交易记录失败：{str(e)}',
            'data': None
        }), 500


# ============== 购买 Token ==============

@phase2_token_bp.route('/purchase', methods=['POST'])
def purchase_tokens():
    """
    购买 Token
    POST /api/v2/token/purchase
    
    Body:
    {
        "user_id": 1,
        "amount_rmb": 100.00  // 充值金额（元）
    }
    
    Response:
    {
        "code": 200,
        "data": {
            "order_id": 456,
            "order_no": "T202605170001",
            "amount_rmb": 100.00,
            "tokens_to_grant": 50000,
            "status": "pending"
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
        
        user_id = data.get('user_id', type=int)
        amount_rmb = data.get('amount_rmb', type=float)
        
        if not user_id or not amount_rmb or amount_rmb <= 0:
            return jsonify({
                'code': 400,
                'message': '参数错误',
                'data': None
            }), 400
        
        user = UserModel.get_by_id(user_id)
        if not user:
            return jsonify({
                'code': 404,
                'message': '用户不存在',
                'data': None
            }), 404
        
        billing = get_billing_service()
        result = billing.purchase_tokens(user_id, amount_rmb)
        
        if not result:
            return jsonify({
                'code': 400,
                'message': '创建订单失败',
                'data': None
            }), 400
        
        return jsonify({
            'code': 200,
            'message': '订单创建成功',
            'data': result
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'购买 Token 失败：{str(e)}',
            'data': None
        }), 500


# ============== Token 价格查询 ==============

@phase2_token_bp.route('/pricing', methods=['GET'])
def get_token_pricing():
    """
    查询 Token 价格
    GET /api/v2/token/pricing
    
    Response:
    {
        "code": 200,
        "data": {
            "basic_price": 0.002,
            "premium_price": 0.001,
            "currency": "CNY",
            "unit": "per 1000 tokens",
            "packages": [
                {"amount_rmb": 10, "tokens": 5000, "bonus": 0},
                {"amount_rmb": 50, "tokens": 25000, "bonus": 2500},
                {"amount_rmb": 100, "tokens": 50000, "bonus": 10000}
            ]
        }
    }
    """
    try:
        billing = get_billing_service()
        
        packages = [
            {'amount_rmb': 10, 'tokens': 5000, 'bonus': 0, 'recommended': False},
            {'amount_rmb': 50, 'tokens': 25000, 'bonus': 2500, 'recommended': True},
            {'amount_rmb': 100, 'tokens': 50000, 'bonus': 10000, 'recommended': False},
            {'amount_rmb': 500, 'tokens': 250000, 'bonus': 75000, 'recommended': False}
        ]
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'basic_price': billing.token_prices['basic'],
                'premium_price': billing.token_prices['premium'],
                'currency': 'CNY',
                'unit': 'per 1000 tokens',
                'packages': packages
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'查询价格失败：{str(e)}',
            'data': None
        }), 500


# ============== Token 消耗统计 ==============

@phase2_token_bp.route('/usage/stats', methods=['GET'])
def get_token_usage_stats():
    """
    查询用户 Token 消耗统计
    GET /api/v2/token/usage/stats?user_id=1&days=7
    
    Response:
    {
        "code": 200,
        "data": {
            "user_id": 1,
            "period_days": 7,
            "total_consumed": 15000,
            "daily_average": 2142,
            "breakdown": {
                "consultation": 10000,
                "document_generation": 3000,
                "contract_review": 2000
            }
        }
    }
    """
    try:
        user_id = request.args.get('user_id', type=int)
        days = request.args.get('days', 7, type=int)
        
        if not user_id:
            return jsonify({
                'code': 400,
                'message': '缺少参数 user_id',
                'data': None
            }), 400
        
        from datetime import timedelta
        since = datetime.now() - timedelta(days=days)
        
        conn = get_db('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
        
        # 总消耗
        result = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) as total
            FROM token_transactions
            WHERE user_id=? AND amount < 0 AND created_at >= ?
        """, (user_id, since.isoformat())).fetchone()
        total_consumed = abs(result['total'])
        
        # 按类型统计
        breakdown_result = conn.execute("""
            SELECT transaction_type, SUM(ABS(amount)) as amount
            FROM token_transactions
            WHERE user_id=? AND amount < 0 AND created_at >= ?
            GROUP BY transaction_type
        """, (user_id, since.isoformat())).fetchall()
        
        breakdown = {r['transaction_type']: r['amount'] for r in breakdown_result}
        conn.close()
        
        daily_average = total_consumed / days if days > 0 else 0
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'user_id': user_id,
                'period_days': days,
                'total_consumed': total_consumed,
                'daily_average': int(daily_average),
                'breakdown': breakdown
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'查询使用统计失败：{str(e)}',
            'data': None
        }), 500


# ============== 健康检查 ==============

@phase2_token_bp.route('/health', methods=['GET'])
def token_health():
    """
    Token 计费系统健康检查
    GET /api/v2/token/health
    """
    try:
        import sqlite3
        conn = sqlite3.connect('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
        conn.execute("SELECT 1")
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'token_router': 'available',
            'billing_service': 'available',
            'database': 'connected'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'token_router': 'unavailable',
            'error': str(e)
        }), 500
