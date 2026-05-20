"""
心海法律 AI · 委托付费模块 API
包含：委托订单创建/支付/查询/取消/完成
基于 Flask Blueprint 实现
"""

import json
import time
import hashlib
import random
import string
from datetime import datetime
from flask import Blueprint, request, jsonify
from functools import wraps

entrust_bp = Blueprint('entrust', __name__, url_prefix='/api/entrust')

DB_PATH = '/home/admin/xinhai_legal_api/data/xinhai_legal.db'

# ─── 工具函数 ────────────────────────────────────────────

def get_db():
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def generate_order_no():
    """生成委托订单号: ENTRUST + 时间戳 + 4位随机数"""
    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    rand = ''.join(random.choices(string.digits, k=4))
    return f'ENTRUST{ts}{rand}'

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        token_str = auth.replace('Bearer ', '') if auth else ''
        
        # 开发模式：支持传入X-User-Id头
        dev_user_id = request.headers.get('X-User-Id')
        if dev_user_id:
            conn = get_db()
            user = conn.execute(
                'SELECT id, phone, full_name, is_lawyer FROM users WHERE id = ?',
                (dev_user_id,)
            ).fetchone()
            conn.close()
            if user:
                return f(dict(user), *args, **kwargs)
        
        if not token_str:
            return jsonify({'code': 401, 'msg': '未登录'}), 401
        
        # 生产模式：验证JWT token（auth.py的verify_token）
        try:
            from services.auth import get_auth_service
            auth_service = get_auth_service()
            payload = auth_service.verify_token(token_str)
            if payload:
                conn = get_db()
                user = conn.execute(
                    'SELECT id, phone, full_name, is_lawyer FROM users WHERE id = ?',
                    (payload.get('user_id'),)
                ).fetchone()
                conn.close()
                if user:
                    return f(dict(user), *args, **kwargs)
        except:
            pass
        
        return jsonify({'code': 401, 'msg': '登录已过期'}), 401
    return decorated

# ─── 接口1：创建委托订单 ────────────────────────────────

@entrust_bp.route('/create', methods=['POST'])
@login_required
def create_entrust(user):
    data = request.get_json(silent=True) or {}
    lawyer_id = data.get('lawyer_id')
    service_type = data.get('service_type', 'legal_consult')
    service_desc = data.get('service_desc', '')
    amount = data.get('amount', 0)  # 分

    if not lawyer_id or amount <= 0:
        return jsonify({'code': 400, 'msg': '缺少必填参数(lawyer_id/amount)'})

    # 验证律师是否存在、已入驻
    conn = get_db()
    lawyer = conn.execute(
        'SELECT id, name, status FROM lawyer_profiles WHERE id = ?',
        (lawyer_id,)
    ).fetchone()
    if not lawyer:
        conn.close()
        return jsonify({'code': 404, 'msg': '律师不存在'})
    if lawyer['status'] not in ('active', 'approved'):
        conn.close()
        return jsonify({'code': 400, 'msg': '律师未上线'})

    # 平台服务费 20%，律师收入 80%
    platform_fee = int(amount * 0.2)
    lawyer_income = amount - platform_fee

    order_no = generate_order_no()

    conn.execute('''
        INSERT INTO entrust_orders 
        (order_no, user_id, lawyer_id, service_type, service_desc, 
         amount, platform_fee, lawyer_income, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
    ''', (order_no, user['id'], lawyer_id, service_type, service_desc,
          amount, platform_fee, lawyer_income))
    conn.commit()

    order_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    order = conn.execute('SELECT * FROM entrust_orders WHERE id = ?', (order_id,)).fetchone()
    conn.close()

    return jsonify({
        'code': 0,
        'msg': 'ok',
        'data': {
            'id': order['id'],
            'order_no': order['order_no'],
            'amount': order['amount'],
            'platform_fee': order['platform_fee'],
            'lawyer_income': order['lawyer_income'],
            'status': order['status'],
            'created_at': order['created_at']
        }
    })


# ─── 接口2：委托支付（调起微信支付JSAPI）───────────────

@entrust_bp.route('/pay', methods=['POST'])
@login_required
def pay_entrust(user):
    data = request.get_json(silent=True) or {}
    order_id = data.get('order_id')

    if not order_id:
        return jsonify({'code': 400, 'msg': '缺少order_id'})

    conn = get_db()
    order = conn.execute(
        'SELECT * FROM entrust_orders WHERE id = ? AND user_id = ?',
        (order_id, user['id'])
    ).fetchone()

    if not order:
        conn.close()
        return jsonify({'code': 404, 'msg': '订单不存在'})
    if order['status'] != 'pending':
        conn.close()
        return jsonify({'code': 400, 'msg': '订单状态异常，无法支付'})

    # 获取用户 openid
    openid = conn.execute(
        'SELECT wechat_openid FROM users WHERE id = ?',
        (user['id'],)
    ).fetchone()
    conn.close()

    if not openid or not openid['wechat_openid']:
        return jsonify({'code': 400, 'msg': '未获取到openid，请先绑定微信'})

    # 构建微信支付参数（商户号1724824261）
    from wechatpayv3 import WeChatPaySDKException
    try:
        # 使用已有的微信支付配置
        from payment_wechat import wx_pay
        result = wx_pay.pay(
            description='心海法律AI - 委托律师服务费',
            out_trade_no=order['order_no'],
            amount=order['amount'],
            openid=openid['openid'],
            notify_url='https://xinclaw.xhacca.cn/api/entrust/pay/notify'
        )
        # 更新 prepay_id
        prepay_id = result.get('prepay_id', '')
        if prepay_id:
            conn2 = get_db()
            conn2.execute(
                'UPDATE entrust_orders SET prepay_id = ? WHERE id = ?',
                (prepay_id, order_id)
            )
            conn2.commit()
            conn2.close()

        # 返回小程序调起支付所需参数
        return jsonify({
            'code': 0,
            'msg': 'ok',
            'data': {
                'timeStamp': str(int(time.time())),
                'nonceStr': ''.join(random.choices(string.ascii_letters + string.digits, k=32)),
                'package': f'prepay_id={prepay_id}',
                'signType': 'RSA',
                'paySign': result.get('pay_sign', ''),
                'prepay_id': prepay_id
            }
        })
    except Exception as e:
        return jsonify({'code': 500, 'msg': f'支付失败: {str(e)}'})


# ─── 接口3：微信支付回调 ────────────────────────────────

@entrust_bp.route('/pay/notify', methods=['POST'])
def pay_notify():
    """微信支付异步通知"""
    data = request.get_data(as_text=True)
    # 验证签名、解析通知
    # ...
    return 'SUCCESS'


# ─── 接口4：查询委托订单 ────────────────────────────────

@entrust_bp.route('/order/<int:order_id>', methods=['GET'])
@login_required
def get_order(user, order_id):
    conn = get_db()
    order = conn.execute(
        'SELECT o.*, l.name as lawyer_name, l.avatar as lawyer_avatar '
        'FROM entrust_orders o '
        'LEFT JOIN lawyer_profiles l ON o.lawyer_id = l.id '
        'WHERE o.id = ? AND (o.user_id = ? OR o.lawyer_id = ?)',
        (order_id, user['id'], user['id'])
    ).fetchone()
    conn.close()

    if not order:
        return jsonify({'code': 404, 'msg': '订单不存在'})

    return jsonify({
        'code': 0,
        'msg': 'ok',
        'data': dict(order)
    })


# ─── 接口5：委托列表 ────────────────────────────────────

@entrust_bp.route('/list', methods=['GET'])
@login_required
def list_orders(user):
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 20, type=int)
    offset = (page - 1) * size
    role = request.args.get('role', 'user')  # user/lawyer

    conn = get_db()
    if role == 'lawyer':
        total = conn.execute(
            'SELECT COUNT(*) FROM entrust_orders WHERE lawyer_id = ?',
            (user['id'],)
        ).fetchone()[0]
        orders = conn.execute(
            'SELECT o.*, u.nickname as user_name '
            'FROM entrust_orders o '
            'LEFT JOIN users u ON o.user_id = u.id '
            'WHERE o.lawyer_id = ? '
            'ORDER BY o.created_at DESC LIMIT ? OFFSET ?',
            (user['id'], size, offset)
        ).fetchall()
    else:
        total = conn.execute(
            'SELECT COUNT(*) FROM entrust_orders WHERE user_id = ?',
            (user['id'],)
        ).fetchone()[0]
        orders = conn.execute(
            'SELECT o.*, l.name as lawyer_name, l.avatar as lawyer_avatar '
            'FROM entrust_orders o '
            'LEFT JOIN lawyer_profiles l ON o.lawyer_id = l.id '
            'WHERE o.user_id = ? '
            'ORDER BY o.created_at DESC LIMIT ? OFFSET ?',
            (user['id'], size, offset)
        ).fetchall()
    conn.close()

    return jsonify({
        'code': 0,
        'msg': 'ok',
        'data': {
            'total': total,
            'page': page,
            'size': size,
            'items': [dict(o) for o in orders]
        }
    })


# ─── 接口6：取消委托 ────────────────────────────────────

@entrust_bp.route('/cancel', methods=['POST'])
@login_required
def cancel_order(user):
    data = request.get_json(silent=True) or {}
    order_id = data.get('order_id')

    if not order_id:
        return jsonify({'code': 400, 'msg': '缺少order_id'})

    conn = get_db()
    order = conn.execute(
        'SELECT * FROM entrust_orders WHERE id = ? AND user_id = ?',
        (order_id, user['id'])
    ).fetchone()

    if not order:
        conn.close()
        return jsonify({'code': 404, 'msg': '订单不存在'})
    if order['status'] not in ('pending', 'paid'):
        conn.close()
        return jsonify({'code': 400, 'msg': '当前状态不可取消'})

    conn.execute(
        "UPDATE entrust_orders SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (order_id,)
    )
    conn.commit()
    conn.close()

    return jsonify({'code': 0, 'msg': '已取消'})


# ─── 接口7：律师完成服务 ────────────────────────────────

@entrust_bp.route('/complete', methods=['POST'])
@login_required
def complete_order(user):
    data = request.get_json(silent=True) or {}
    order_id = data.get('order_id')

    if not order_id:
        return jsonify({'code': 400, 'msg': '缺少order_id'})

    conn = get_db()
    # 验证是律师本人操作
    order = conn.execute(
        'SELECT * FROM entrust_orders WHERE id = ? AND lawyer_id = ?',
        (order_id, user['id'])
    ).fetchone()

    if not order:
        conn.close()
        return jsonify({'code': 404, 'msg': '订单不存在'})
    if order['status'] != 'paid':
        conn.close()
        return jsonify({'code': 400, 'msg': '订单未支付或已结束'})

    conn.execute(
        "UPDATE entrust_orders SET status = 'completed', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (order_id,)
    )
    conn.execute(
        "UPDATE entrust_services SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE order_id = ?",
        (order_id,)
    )
    conn.commit()
    conn.close()

    return jsonify({'code': 0, 'msg': '服务已完成'})
