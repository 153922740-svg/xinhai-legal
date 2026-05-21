"""
心海法律 AI - Phase 2 微信支付 API
集成微信支付，支持小程序支付和 H5 支付
"""

from flask import Blueprint, request, jsonify, g, current_app
from datetime import datetime
from services.billing import BillingService
from models.db import get_db
import os
import json
import hashlib
import time
import requests

phase2_payment_bp = Blueprint('phase2_payment', __name__, url_prefix='/api/v2/payment')

# 微信支付配置（从环境变量读取）
from dotenv import load_dotenv
load_dotenv('/home/admin/xinhai_legal_api/.env')

WECHAT_CONFIG = {
    'appid': os.getenv('WECHAT_APPID', 'wx73612d8efb98658d'),  # 小程序 AppID
    'mchid': os.getenv('WECHAT_MCHID', '1745164408'),  # 商户号
    'api_key': os.getenv('WECHAT_APIKEY', 'Xinclaw2026xinhaifalvzixunxincla'),  # API v3 密钥
    'cert_path': os.getenv('WECHAT_CERT_PATH', '/www/wwwroot/xinclaw-law/backend/cert/apiclient_cert.pem'),
    'key_path': os.getenv('WECHAT_KEY_PATH', '/www/wwwroot/xinclaw-law/backend/cert/apiclient_key.pem'),
    'notify_url': os.getenv('WECHAT_NOTIFY_URL', 'https://xinclaw.xhacca.cn/api/v1/payment/wechat/notify'),  # 支付回调地址
}


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


# ============== 创建微信支付订单 ==============

@phase2_payment_bp.route('/wechat/create', methods=['POST'])
def create_wechat_payment():
    """
    创建微信支付订单
    POST /api/v2/payment/wechat/create
    
    Body:
    {
        "order_id": 123,
        "user_id": 1,
        "amount": 30.00,
        "description": "月度会员购买",
        "openid": "oXXXXXX"  # 用户微信 openid
    }
    
    Response:
    {
        "code": 200,
        "data": {
            "payment_params": {
                "appId": "wx1234567890abcdef",
                "timeStamp": "1684300000",
                "nonceStr": "random_string",
                "package": "prepay_id=wx20230517000000",
                "signType": "RSA",
                "paySign": "signature"
            },
            "order_id": 123,
            "order_no": "M202605170001"
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
        
        order_id = int(data.get('order_id', 0))
        user_id = int(data.get('user_id', 0))
        amount = float(data.get('amount', 0.0))
        description = data.get('description', '会员购买')
        openid = data.get('openid')
        
        if not order_id or not user_id or not amount:
            return jsonify({
                'code': 400,
                'message': '缺少必要参数',
                'data': None
            }), 400
        
        # 验证订单
        conn = get_db('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
        order = conn.execute(
            "SELECT * FROM membership_orders WHERE id=? AND user_id=? AND status='pending'",
            (order_id, user_id)
        ).fetchone()
        
        if not order:
            conn.close()
            return jsonify({
                'code': 404,
                'message': '订单不存在或状态异常',
                'data': None
            }), 404
        
        order = dict(order)
        
        # 检查金额是否匹配
        if abs(order['price'] - amount) > 0.01:
            conn.close()
            return jsonify({
                'code': 400,
                'message': '订单金额不匹配',
                'data': None
            }), 400
        
        conn.close()
        
        # ========== 模拟微信支付（开发环境）==========
        # 生产环境需要调用微信支付 API
        
        # 生成预支付 ID（模拟）
        prepay_id = f"wx{datetime.now().strftime('%Y%m%d%H%M%S')}{order_id:06d}"
        nonce_str = hashlib.md5(f"{time.time()}".encode()).hexdigest()
        timestamp = str(int(time.time()))
        
        # 生成签名（简化版，生产环境需要 RSA 签名）
        sign_str = f"appId={WECHAT_CONFIG['appid']}&timeStamp={timestamp}&nonceStr={nonce_str}&package=prepay_id={prepay_id}&signType=RSA"
        pay_sign = hashlib.sha256(f"{sign_str}{WECHAT_CONFIG['api_key']}".encode()).hexdigest()
        
        # 更新订单状态为待支付
        conn = get_db('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
        conn.execute("""
            UPDATE membership_orders 
            SET status='pending_payment', payment_method='wechat', updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        """, (order_id,))
        conn.commit()
        conn.close()
        
        payment_params = {
            'appId': WECHAT_CONFIG['appid'],
            'timeStamp': timestamp,
            'nonceStr': nonce_str,
            'package': f'prepay_id={prepay_id}',
            'signType': 'RSA',
            'paySign': pay_sign
        }
        
        return jsonify({
            'code': 200,
            'message': '支付订单创建成功',
            'data': {
                'payment_params': payment_params,
                'order_id': order_id,
                'order_no': order.get('order_no', ''),
                'amount': amount,
                'description': description,
                'expire_at': order.get('expire_at')
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'创建支付订单失败：{str(e)}',
            'data': None
        }), 500


# ============== 微信支付回调 ==============

@phase2_payment_bp.route('/wechat/notify', methods=['POST'])
def wechat_payment_notify():
    """
    微信支付结果回调
    POST /api/v2/payment/wechat/notify
    
    微信支付成功后会调用此接口通知支付结果
    """
    try:
        # 获取回调数据
        notify_data = request.get_json() or request.data
        
        # 验证签名（生产环境必须验证）
        # ...
        
        # 解析回调数据
        order_no = notify_data.get('out_trade_no')  # 商户订单号
        transaction_id = notify_data.get('transaction_id')  # 微信支付订单号
        trade_state = notify_data.get('trade_state')  # 支付状态 SUCCESS/REFUND/NOTPAY
        total_amount = notify_data.get('total_amount', 0) / 100  # 金额（分转元）
        
        if trade_state != 'SUCCESS':
            return jsonify({'code': 'FAIL', 'message': '支付未成功'})
        
        # 查找订单
        conn = get_db('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
        order = conn.execute(
            "SELECT * FROM membership_orders WHERE order_no=?", (order_no,)
        ).fetchone()
        
        if not order:
            conn.close()
            return jsonify({'code': 'FAIL', 'message': '订单不存在'})
        
        order = dict(order)
        
        if order['status'] == 'paid':
            conn.close()
            return jsonify({'code': 'SUCCESS', 'message': '已处理'})
        
        # 激活会员
        billing = get_billing_service()
        success = billing.activate_membership(order['id'])
        
        if success:
            # 更新订单
            conn.execute("""
                UPDATE membership_orders 
                SET status='paid', paid_at=CURRENT_TIMESTAMP, transaction_id=?
                WHERE id=?
            """, (transaction_id, order['id']))
            conn.commit()
            
            conn.close()
            return jsonify({'code': 'SUCCESS', 'message': '支付成功'})
        else:
            conn.close()
            return jsonify({'code': 'FAIL', 'message': '激活会员失败'})
            
    except Exception as e:
        current_app.logger.error(f"微信支付回调错误：{e}")
        return jsonify({'code': 'FAIL', 'message': '回调处理失败'}), 500


# ============== 查询支付状态 ==============

@phase2_payment_bp.route('/wechat/status/<int:order_id>', methods=['GET'])
def get_payment_status(order_id):
    """
    查询支付状态
    GET /api/v2/payment/wechat/status/123
    
    Response:
    {
        "code": 200,
        "data": {
            "order_id": 123,
            "order_no": "M202605170001",
            "status": "paid",
            "paid_at": "2026-05-17T10:05:00",
            "amount": 30.00,
            "transaction_id": "4200001234567890"
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
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'order_id': order['id'],
                'order_no': order.get('order_no', ''),
                'status': order['status'],
                'paid_at': order.get('paid_at'),
                'amount': order['price'],
                'transaction_id': order.get('transaction_id'),
                'plan': order['plan']
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'查询支付状态失败：{str(e)}',
            'data': None
        }), 500


# ============== 退款申请 ==============

@phase2_payment_bp.route('/wechat/refund', methods=['POST'])
def apply_refund():
    """
    申请退款
    POST /api/v2/payment/wechat/refund
    
    Body:
    {
        "order_id": 123,
        "reason": "用户申请退款",
        "amount": 30.00  // 退款金额，可选（部分退款）
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
        
        order_id = int(data.get('order_id', 0))
        reason = data.get('reason', '用户申请退款')
        refund_amount = data.get('amount')
        
        if not order_id:
            return jsonify({
                'code': 400,
                'message': '缺少订单 ID',
                'data': None
            }), 400
        
        conn = get_db('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
        order = conn.execute(
            "SELECT * FROM membership_orders WHERE id=? AND status='paid'",
            (order_id,)
        ).fetchone()
        
        if not order:
            conn.close()
            return jsonify({
                'code': 404,
                'message': '订单不存在或未支付',
                'data': None
            }), 404
        
        order = dict(order)
        
        # 检查是否已退款
        if order.get('refund_status') == 'refunded':
            conn.close()
            return jsonify({
                'code': 400,
                'message': '订单已退款',
                'data': None
            }), 400
        
        # 创建退款记录
        refund_amount = refund_amount or order['price']
        refund_no = f"R{datetime.now().strftime('%Y%m%d%H%M%S')}{order_id:04d}"
        
        cursor = conn.execute("""
            INSERT INTO refund_requests (order_id, refund_amount, reason, status, refund_no)
            VALUES (?, ?, ?, 'pending', ?)
        """, (order_id, refund_amount, reason, refund_no))
        conn.commit()
        refund_id = cursor.lastrowid
        
        conn.close()
        
        # TODO: 调用微信支付退款 API
        
        return jsonify({
            'code': 200,
            'message': '退款申请已提交',
            'data': {
                'refund_id': refund_id,
                'refund_no': refund_no,
                'order_id': order_id,
                'refund_amount': refund_amount,
                'status': 'pending'
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'申请退款失败：{str(e)}',
            'data': None
        }), 500


# ============== 健康检查 ==============

@phase2_payment_bp.route('/health', methods=['GET'])
def payment_health():
    """
    支付系统健康检查
    GET /api/v2/payment/health
    """
    try:
        import sqlite3
        conn = sqlite3.connect('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
        conn.execute("SELECT 1")
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'payment_router': 'available',
            'wechat_pay': 'mock_mode',
            'database': 'connected'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'payment_router': 'unavailable',
            'error': str(e)
        }), 500
