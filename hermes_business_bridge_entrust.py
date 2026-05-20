"""
委托付费系统Bridge - 从 entrust_api.py 提取业务逻辑
功能：委托创建、支付、查询、取消、完成
"""

import json
import sqlite3
import random
import string
from datetime import datetime

# ========== 数据库配置 ==========
DB_PATH = "/home/admin/xinhai_legal_api/data/xinhai_legal.db"


def get_db():
    """获取数据库连接"""
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def generate_order_no():
    """生成委托订单号"""
    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    rand = ''.join(random.choices(string.digits, k=4))
    return f'ENTRUST{ts}{rand}'


# ========== Action: create_entrust ==========

def create_entrust(body: dict) -> dict:
    """创建委托订单"""
    user_id = body.get('user_id')
    lawyer_id = body.get('lawyer_id')
    service_type = body.get('service_type', 'legal_consult')
    service_desc = body.get('service_desc', '')
    amount = body.get('amount', 0)

    if not user_id or not lawyer_id or amount <= 0:
        return {'code': 400, 'msg': '缺少必填参数(user_id/lawyer_id/amount)'}

    db = get_db()
    try:
        # 验证用户
        user = db.execute('SELECT id FROM users WHERE id = ?', (user_id,)).fetchone()
        if not user:
            return {'code': 404, 'msg': '用户不存在'}

        # 验证律师
        lawyer = db.execute(
            'SELECT id, name, status FROM lawyer_profiles WHERE id = ?',
            (lawyer_id,)
        ).fetchone()
        if not lawyer:
            return {'code': 404, 'msg': '律师不存在'}
        if lawyer['status'] not in ('active', 'approved'):
            return {'code': 400, 'msg': '律师未上线'}

        # 平台服务费 20%
        platform_fee = int(amount * 0.2)
        lawyer_income = amount - platform_fee

        order_no = generate_order_no()

        db.execute('''
            INSERT INTO entrust_orders 
            (order_no, user_id, lawyer_id, service_type, service_desc,
             amount, platform_fee, lawyer_income, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        ''', (order_no, user_id, lawyer_id, service_type, service_desc,
              amount, platform_fee, lawyer_income))
        db.commit()

        order = db.execute(
            'SELECT * FROM entrust_orders WHERE order_no = ?', (order_no,)
        ).fetchone()

        return {
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
        }
    except Exception as e:
        db.rollback()
        return {'code': 500, 'msg': f'创建失败: {str(e)}'}
    finally:
        db.close()


# ========== Action: get_order ==========

def get_order(body: dict) -> dict:
    """查询委托订单详情"""
    order_id = body.get('order_id')
    user_id = body.get('user_id')

    if not order_id:
        return {'code': 400, 'msg': '缺少order_id'}

    db = get_db()
    try:
        order = db.execute(
            'SELECT * FROM entrust_orders WHERE id = ? AND user_id = ?',
            (order_id, user_id)
        ).fetchone() if user_id else db.execute(
            'SELECT * FROM entrust_orders WHERE id = ?', (order_id,)
        ).fetchone()

        if not order:
            return {'code': 404, 'msg': '订单不存在'}

        # 关联律师信息
        lawyer = db.execute(
            'SELECT id, name, avatar, firm_name FROM lawyer_profiles WHERE id = ?',
            (order['lawyer_id'],)
        ).fetchone()

        return {
            'code': 0,
            'msg': 'ok',
            'data': {
                'id': order['id'],
                'order_no': order['order_no'],
                'user_id': order['user_id'],
                'lawyer_id': order['lawyer_id'],
                'lawyer_name': lawyer['name'] if lawyer else '',
                'lawyer_avatar': lawyer['avatar'] if lawyer else '',
                'lawyer_firm': lawyer['firm_name'] if lawyer else '',
                'service_type': order['service_type'],
                'service_desc': order['service_desc'],
                'amount': order['amount'],
                'platform_fee': order['platform_fee'],
                'lawyer_income': order['lawyer_income'],
                'status': order['status'],
                'created_at': order['created_at'],
                'paid_at': order.get('paid_at', ''),
                'completed_at': order.get('completed_at', '')
            }
        }
    finally:
        db.close()


# ========== Action: list_entrust ==========

def list_entrust(body: dict) -> dict:
    """获取用户的委托订单列表"""
    user_id = body.get('user_id')
    status = body.get('status', '')  # 可选筛选
    page = int(body.get('page', 1))
    limit = int(body.get('limit', 20))
    offset = (page - 1) * limit

    if not user_id:
        return {'code': 400, 'msg': '缺少user_id'}

    db = get_db()
    try:
        if status:
            total = db.execute(
                'SELECT COUNT(*) as c FROM entrust_orders WHERE user_id = ? AND status = ?',
                (user_id, status)
            ).fetchone()['c']
            rows = db.execute(
                '''SELECT e.*, lp.name as lawyer_name, lp.avatar as lawyer_avatar
                   FROM entrust_orders e
                   LEFT JOIN lawyer_profiles lp ON e.lawyer_id = lp.id
                   WHERE e.user_id = ? AND e.status = ?
                   ORDER BY e.created_at DESC LIMIT ? OFFSET ?''',
                (user_id, status, limit, offset)
            ).fetchall()
        else:
            total = db.execute(
                'SELECT COUNT(*) as c FROM entrust_orders WHERE user_id = ?',
                (user_id,)
            ).fetchone()['c']
            rows = db.execute(
                '''SELECT e.*, lp.name as lawyer_name, lp.avatar as lawyer_avatar
                   FROM entrust_orders e
                   LEFT JOIN lawyer_profiles lp ON e.lawyer_id = lp.id
                   WHERE e.user_id = ?
                   ORDER BY e.created_at DESC LIMIT ? OFFSET ?''',
                (user_id, limit, offset)
            ).fetchall()

        return {
            'code': 0,
            'msg': 'ok',
            'data': {
                'total': total,
                'page': page,
                'limit': limit,
                'items': [dict(r) for r in rows]
            }
        }
    finally:
        db.close()


# ========== Action: cancel_entrust ==========

def cancel_entrust(body: dict) -> dict:
    """取消委托订单"""
    order_id = body.get('order_id')
    user_id = body.get('user_id')

    if not order_id:
        return {'code': 400, 'msg': '缺少order_id'}

    db = get_db()
    try:
        order = db.execute(
            'SELECT * FROM entrust_orders WHERE id = ? AND user_id = ?',
            (order_id, user_id)
        ).fetchone()

        if not order:
            return {'code': 404, 'msg': '订单不存在'}
        if order['status'] != 'pending':
            return {'code': 400, 'msg': '只能取消待支付的订单'}

        db.execute(
            "UPDATE entrust_orders SET status = 'cancelled', updated_at = datetime('now') WHERE id = ?",
            (order_id,)
        )
        db.commit()

        return {'code': 0, 'msg': '取消成功'}
    except Exception as e:
        db.rollback()
        return {'code': 500, 'msg': f'取消失败: {str(e)}'}
    finally:
        db.close()


# ========== Action: complete_entrust ==========

def complete_entrust(body: dict) -> dict:
    """完成委托订单（标记已完成）"""
    order_id = body.get('order_id')
    user_id = body.get('user_id')

    if not order_id:
        return {'code': 400, 'msg': '缺少order_id'}

    db = get_db()
    try:
        order = db.execute(
            'SELECT * FROM entrust_orders WHERE id = ? AND user_id = ?',
            (order_id, user_id)
        ).fetchone()

        if not order:
            return {'code': 404, 'msg': '订单不存在'}
        if order['status'] != 'paid':
            return {'code': 400, 'msg': '只能完成已支付的订单'}

        db.execute(
            """UPDATE entrust_orders 
               SET status = 'completed', completed_at = datetime('now'), updated_at = datetime('now')
               WHERE id = ?""",
            (order_id,)
        )
        db.commit()

        return {'code': 0, 'msg': '已完成'}
    except Exception as e:
        db.rollback()
        return {'code': 500, 'msg': f'操作失败: {str(e)}'}
    finally:
        db.close()


# ========== Main ==========

ACTIONS = {
    'create_entrust': create_entrust,
    'get_order': get_order,
    'list_entrust': list_entrust,
    'cancel_entrust': cancel_entrust,
    'complete_entrust': complete_entrust,
}


def main():
    import sys
    if len(sys.argv) < 3:
        print(json.dumps({'code': 400, 'msg': '参数不足: action + json_body'}))
        return

    action = sys.argv[1]
    body_str = sys.argv[2]

    try:
        body = json.loads(body_str)
    except json.JSONDecodeError:
        print(json.dumps({'code': 400, 'msg': 'JSON参数解析失败'}))
        return

    handler = ACTIONS.get(action)
    if not handler:
        print(json.dumps({'code': 400, 'msg': f'未知action: {action}'}))
        return

    result = handler(body)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
