"""
Phase 9: 积分系统 API
- 每日签到
- 积分任务
- 积分余额
- 积分记录
- 积分商城
"""

import sqlite3
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify

phase9_bp = Blueprint('phase9', __name__)

# 积分规则配置
SIGN_IN_RULES = {
    'daily': 10,  # 每日签到基础积分
    'continuous': {3: 20, 7: 230, 14: 120, 30: 300},  # 连续签到奖励（7天累计240分：10基础+230奖励）
    'makeup': {1: 20, 2: 30, 3: 50}  # 补签价格（1 天前 20 分，2 天前 30 分，3 天前 50 分）
}

TASK_RULES = {
    'daily': {
        'consult': {'points': 5, 'limit': 5, 'desc': '每日咨询'},  # 5 分/次，上限 5 分/日
        'document': {'points': 5, 'limit': 5, 'desc': '生成文书'},  # 5 分/次，上限 5 分/日
        'share': {'points': 5, 'limit': 15, 'desc': '分享'}  # 5 分/次，上限 3 次
    },
    'one_time': {
        'profile': {'points': 50, 'desc': '完善资料'},
        'first_consult': {'points': 20, 'desc': '首次咨询'},
        'first_document': {'points': 20, 'desc': '首次文书'},
        'bind_wx': {'points': 30, 'desc': '绑定微信'},
        'verify': {'points': 50, 'desc': '实名认证'}
    },
    'social': {
        'invite_register': {'points': 100, 'desc': '邀请好友注册'},
        'invite_member': {'points': 500, 'desc': '好友开通会员'},
        'invite_recharge': {'points': 50, 'rate': 0.05, 'desc': '好友充值返利 5%'}
    }
}

# 积分商城商品
SHOP_ITEMS = {
    'virtual': [
        {'id': 'v1', 'name': '1 天会员卡', 'points': 100, 'type': 'member_days', 'value': 1},
        {'id': 'v2', 'name': '3 天会员卡', 'points': 250, 'type': 'member_days', 'value': 3},
        {'id': 'v3', 'name': '1 万 Token 包', 'points': 200, 'type': 'token', 'value': 10000},
        {'id': 'v4', 'name': '5 万 Token 包', 'points': 800, 'type': 'token', 'value': 50000},
        {'id': 'v5', 'name': '文书生成券×1', 'points': 50, 'type': 'document_coupon', 'value': 1},
        {'id': 'v6', 'name': '文书生成券×5', 'points': 200, 'type': 'document_coupon', 'value': 5},
    ],
    'coupon': [
        {'id': 'c1', 'name': '会员 95 折券', 'points': 300, 'type': 'discount', 'value': 0.95, 'category': 'member'},
        {'id': 'c2', 'name': 'Token 充值 95 折券', 'points': 500, 'type': 'discount', 'value': 0.95, 'category': 'token'},
    ],
    'physical': [
        {'id': 'p1', 'name': '定制笔记本', 'points': 2000, 'type': 'physical', 'stock': 100},
        {'id': 'p2', 'name': '定制马克杯', 'points': 1500, 'type': 'physical', 'stock': 100},
        {'id': 'p3', 'name': '定制 T 恤', 'points': 3000, 'type': 'physical', 'stock': 50},
        {'id': 'p4', 'name': '法律书籍', 'points': 5000, 'type': 'physical', 'stock': 20},
    ]
}

def get_db():
    db = sqlite3.connect('/home/admin/xinhai_legal.db')
    db.row_factory = sqlite3.Row
    return db

# ============== 签到 ==============

@phase9_bp.route('/api/v1/user/sign', methods=['POST'])
def user_sign():
    """
    每日签到
    参数：user_id
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'code': 400, 'message': '缺少 user_id'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        today = datetime.now().date()
        today_str = today.isoformat()
        
        # 检查今天是否已签到
        cursor.execute('''
            SELECT * FROM sign_in_records
            WHERE user_id = ? AND date = ?
        ''', (user_id, today_str))
        
        if cursor.fetchone():
            db.close()
            return jsonify({'code': 400, 'message': '今日已签到'}), 400
        
        # 获取上次签到日期
        cursor.execute('''
            SELECT date FROM sign_in_records
            WHERE user_id = ?
            ORDER BY date DESC LIMIT 1
        ''', (user_id,))
        
        last_row = cursor.fetchone()
        continuous_days = 1
        
        if last_row:
            last_date = datetime.fromisoformat(last_row['date']).date()
            days_diff = (today - last_date).days
            
            if days_diff == 1:
                # 连续签到
                cursor.execute('SELECT continuous_days FROM users WHERE id = ?', (user_id,))
                user_row = cursor.fetchone()
                continuous_days = (user_row['continuous_days'] if user_row else 0) + 1
            elif days_diff > 1:
                # 中断，重置
                continuous_days = 1
        
        # 计算积分
        points = SIGN_IN_RULES['daily']
        
        # 连续签到奖励
        bonus = 0
        for days, bonus_points in SIGN_IN_RULES['continuous'].items():
            if continuous_days >= days:
                bonus = bonus_points
        
        total_points = points + bonus
        
        # 插入签到记录
        cursor.execute('''
            INSERT INTO sign_in_records (user_id, date, points, bonus, continuous_days, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, today_str, points, bonus, continuous_days, datetime.now().isoformat()))
        
        # 更新用户积分
        cursor.execute('''
            UPDATE users SET points = COALESCE(points, 0) + ?, continuous_days = ?
            WHERE id = ?
        ''', (total_points, continuous_days, user_id))
        
        # 记录积分流水
        cursor.execute('''
            INSERT INTO integral_records (user_id, type, points, balance_after, description, created_at)
            VALUES (?, 'sign', ?, ?, ?, ?)
        ''', (user_id, total_points, total_points, f'签到奖励 (连续{continuous_days}天)', datetime.now().isoformat()))
        
        db.commit()
        db.close()
        
        return jsonify({
            'code': 200,
            'message': '签到成功',
            'data': {
                'points': points,
                'bonus': bonus,
                'total': total_points,
                'continuous_days': continuous_days
            }
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'签到失败：{str(e)}'}), 500


@phase9_bp.route('/api/v1/user/sign/status', methods=['GET'])
def get_sign_status():
    """
    获取签到状态
    参数：user_id
    """
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'code': 400, 'message': '缺少 user_id'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        today = datetime.now().date().isoformat()
        
        # 检查今天是否已签到
        cursor.execute('SELECT * FROM sign_in_records WHERE user_id = ? AND date = ?', (user_id, today))
        today_signed = cursor.fetchone() is not None
        
        # 获取连续签到天数
        cursor.execute('SELECT continuous_days FROM users WHERE id = ?', (user_id,))
        user_row = cursor.fetchone()
        continuous_days = user_row['continuous_days'] if user_row else 0
        
        # 获取本月签到记录
        month_start = datetime.now().replace(day=1).date().isoformat()
        cursor.execute('''
            SELECT date, points, bonus FROM sign_in_records
            WHERE user_id = ? AND date >= ?
            ORDER BY date ASC
        ''', (user_id, month_start))
        
        sign_records = [dict(row) for row in cursor.fetchall()]
        
        db.close()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'today_signed': today_signed,
                'continuous_days': continuous_days,
                'month_records': sign_records
            }
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询失败：{str(e)}'}), 500


@phase9_bp.route('/api/v1/user/sign/makeup', methods=['POST'])
def sign_makeup():
    """
    补签
    参数：user_id, date (补签日期)
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        date = data.get('date')
        
        if not user_id or not date:
            return jsonify({'code': 400, 'message': '缺少参数'}), 400
        
        # 计算补签价格
        today = datetime.now().date()
        target_date = datetime.fromisoformat(date).date()
        days_diff = (today - target_date).days
        
        if days_diff not in SIGN_IN_RULES['makeup']:
            return jsonify({'code': 400, 'message': '只能补签最近 3 天'}), 400
        
        cost = SIGN_IN_RULES['makeup'][days_diff]
        
        db = get_db()
        cursor = db.cursor()
        
        # 检查积分是否足够
        cursor.execute('SELECT points FROM users WHERE id = ?', (user_id,))
        user_row = cursor.fetchone()
        current_points = user_row['points'] if user_row else 0
        
        if current_points < cost:
            db.close()
            return jsonify({'code': 400, 'message': f'积分不足，需要{cost}分'}), 400
        
        # 检查是否已签到
        cursor.execute('SELECT * FROM sign_in_records WHERE user_id = ? AND date = ?', (user_id, date))
        if cursor.fetchone():
            db.close()
            return jsonify({'code': 400, 'message': '该日期已签到'}), 400
        
        # 扣除积分
        cursor.execute('UPDATE users SET points = points - ? WHERE id = ?', (cost, user_id))
        
        # 插入签到记录
        cursor.execute('''
            INSERT INTO sign_in_records (user_id, date, points, bonus, is_makeup, created_at)
            VALUES (?, ?, 0, 0, 1, ?)
        ''', (user_id, date, datetime.now().isoformat()))
        
        # 记录积分流水
        cursor.execute('''
            INSERT INTO integral_records (user_id, type, points, balance_after, description, created_at)
            VALUES (?, 'makeup_cost', ?, ?, ?, ?)
        ''', (user_id, -cost, current_points - cost, f'补签 ({date})', datetime.now().isoformat()))
        
        db.commit()
        db.close()
        
        return jsonify({
            'code': 200,
            'message': '补签成功',
            'data': {'cost': cost}
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'补签失败：{str(e)}'}), 500


# ============== 积分余额 ==============

@phase9_bp.route('/api/v1/integral/balance', methods=['GET'])
def get_integral_balance():
    """
    获取积分余额
    参数：user_id
    """
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'code': 400, 'message': '缺少 user_id'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('SELECT points FROM users WHERE id = ?', (user_id,))
        user_row = cursor.fetchone()
        balance = user_row['points'] if user_row else 0
        
        db.close()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {'balance': balance}
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询失败：{str(e)}'}), 500


@phase9_bp.route('/api/v1/integral/records', methods=['GET'])
def get_integral_records():
    """
    获取积分记录
    参数：user_id, type, page, limit
    """
    try:
        user_id = request.args.get('user_id')
        record_type = request.args.get('type', 'all')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        
        if not user_id:
            return jsonify({'code': 400, 'message': '缺少 user_id'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        if record_type == 'all':
            cursor.execute('''
                SELECT * FROM integral_records
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (user_id, limit, (page-1)*limit))
        else:
            cursor.execute('''
                SELECT * FROM integral_records
                WHERE user_id = ? AND type = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (user_id, record_type, limit, (page-1)*limit))
        
        records = [dict(row) for row in cursor.fetchall()]
        
        db.close()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'total': len(records),
                'page': page,
                'limit': limit,
                'items': records
            }
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询失败：{str(e)}'}), 500


# ============== 任务系统 ==============

@phase9_bp.route('/api/v1/integral/tasks', methods=['GET'])
def get_tasks():
    """
    获取任务列表
    参数：user_id
    """
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'code': 400, 'message': '缺少 user_id'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        # 获取用户今日已完成的日常任务
        today = datetime.now().date().isoformat()
        cursor.execute('''
            SELECT type, COUNT(*) as count, SUM(points) as total
            FROM integral_records
            WHERE user_id = ? AND date(created_at) = ? AND type IN ('consult', 'document', 'share')
            GROUP BY type
        ''', (user_id, today))
        
        today_tasks = {row['type']: {'count': row['count'], 'points': row['total']} for row in cursor.fetchall()}
        
        # 获取已完成的一次性任务
        cursor.execute('''
            SELECT type FROM integral_records
            WHERE user_id = ? AND type IN ('profile', 'first_consult', 'first_document', 'bind_wx', 'verify')
        ''', (user_id,))
        
        completed_one_time = {row['type'] for row in cursor.fetchall()}
        
        db.close()
        
        # 构建任务列表
        tasks = {
            'daily': [],
            'one_time': [],
            'social': []
        }
        
        for key, config in TASK_RULES['daily'].items():
            task = today_tasks.get(key, {'count': 0, 'points': 0})
            tasks['daily'].append({
                'id': key,
                'name': config['desc'],
                'points': config['points'],
                'limit': config['limit'],
                'completed': task['count'],
                'progress': f"{task['count']}/{config['limit']}"
            })
        
        for key, config in TASK_RULES['one_time'].items():
            tasks['one_time'].append({
                'id': key,
                'name': config['desc'],
                'points': config['points'],
                'completed': key in completed_one_time
            })
        
        tasks['social'] = [
            {'id': 'invite_register', 'name': TASK_RULES['social']['invite_register']['desc'], 'points': 100},
            {'id': 'invite_member', 'name': TASK_RULES['social']['invite_member']['desc'], 'points': 500},
            {'id': 'invite_recharge', 'name': TASK_RULES['social']['invite_recharge']['desc'], 'points': '5% 返利'}
        ]
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {'tasks': tasks}
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询失败：{str(e)}'}), 500


@phase9_bp.route('/api/v1/integral/task/complete', methods=['POST'])
def complete_task():
    """
    完成任务（用于一次性任务）
    参数：user_id, task_id
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        task_id = data.get('task_id')
        
        if not user_id or not task_id:
            return jsonify({'code': 400, 'message': '缺少参数'}), 400
        
        if task_id not in TASK_RULES['one_time']:
            return jsonify({'code': 400, 'message': '任务不存在'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        # 检查是否已完成
        cursor.execute('''
            SELECT * FROM integral_records
            WHERE user_id = ? AND type = ?
        ''', (user_id, task_id))
        
        if cursor.fetchone():
            db.close()
            return jsonify({'code': 400, 'message': '任务已完成'}), 400
        
        task = TASK_RULES['one_time'][task_id]
        points = task['points']
        
        # 获取当前积分
        cursor.execute('SELECT points FROM users WHERE id = ?', (user_id,))
        current_points = cursor.fetchone()['points'] or 0
        
        # 更新积分
        cursor.execute('UPDATE users SET points = points + ? WHERE id = ?', (points, user_id))
        
        # 记录积分流水
        cursor.execute('''
            INSERT INTO integral_records (user_id, type, points, balance_after, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, task_id, points, current_points + points, task['desc'], datetime.now().isoformat()))
        
        db.commit()
        db.close()
        
        return jsonify({
            'code': 200,
            'message': '任务完成',
            'data': {'points': points}
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'操作失败：{str(e)}'}), 500


# ============== 积分商城 ==============

@phase9_bp.route('/api/v1/integral/shop', methods=['GET'])
def get_shop_items():
    """
    获取商城商品
    """
    try:
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': SHOP_ITEMS
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询失败：{str(e)}'}), 500


@phase9_bp.route('/api/v1/integral/exchange', methods=['POST'])
def exchange_item():
    """
    积分兑换
    参数：user_id, item_id
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        item_id = data.get('item_id')
        
        if not user_id or not item_id:
            return jsonify({'code': 400, 'message': '缺少参数'}), 400
        
        # 查找商品
        item = None
        for category in SHOP_ITEMS.values():
            for i in category:
                if i['id'] == item_id:
                    item = i
                    break
        
        if not item:
            return jsonify({'code': 404, 'message': '商品不存在'}), 404
        
        db = get_db()
        cursor = db.cursor()
        
        # 检查积分
        cursor.execute('SELECT points FROM users WHERE id = ?', (user_id,))
        user_row = cursor.fetchone()
        current_points = user_row['points'] if user_row else 0
        
        if current_points < item['points']:
            db.close()
            return jsonify({'code': 400, 'message': f'积分不足，需要{item["points"]}分'}), 400
        
        # 检查库存（实物商品）
        if item.get('type') == 'physical':
            if item.get('stock', 0) <= 0:
                db.close()
                return jsonify({'code': 400, 'message': '商品已售罄'}), 400
        
        # 扣除积分
        cursor.execute('UPDATE users SET points = points - ? WHERE id = ?', (item['points'], user_id))
        
        # 创建兑换记录
        cursor.execute('''
            INSERT INTO exchange_orders (user_id, item_id, item_name, points_cost, status, created_at)
            VALUES (?, ?, ?, ?, 'pending', ?)
        ''', (user_id, item_id, item['name'], item['points'], datetime.now().isoformat()))
        
        # 减少库存（实物商品）
        if item.get('type') == 'physical':
            pass  # TODO: 更新库存表
        
        # 记录积分流水
        cursor.execute('''
            INSERT INTO integral_records (user_id, type, points, balance_after, description, created_at)
            VALUES (?, 'exchange', ?, ?, ?, ?)
        ''', (user_id, -item['points'], current_points - item['points'], f'兑换：{item["name"]}', datetime.now().isoformat()))
        
        db.commit()
        db.close()
        
        return jsonify({
            'code': 200,
            'message': '兑换成功',
            'data': {'order_id': cursor.lastrowid}
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'兑换失败：{str(e)}'}), 500


@phase9_bp.route('/api/v1/integral/orders', methods=['GET'])
def get_exchange_orders():
    """
    获取兑换记录
    参数：user_id, page, limit
    """
    try:
        user_id = request.args.get('user_id')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        
        if not user_id:
            return jsonify({'code': 400, 'message': '缺少 user_id'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
            SELECT * FROM exchange_orders
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        ''', (user_id, limit, (page-1)*limit))
        
        orders = [dict(row) for row in cursor.fetchall()]
        
        db.close()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'total': len(orders),
                'page': page,
                'limit': limit,
                'items': orders
            }
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询失败：{str(e)}'}), 500


# ============== 数据库初始化 ==============

def init_phase9_tables():
    """
    初始化 Phase 9 数据库表
    """
    db = get_db()
    cursor = db.cursor()
    
    # 确保 users 表有 points 和 continuous_days 字段
    cursor.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS points INTEGER DEFAULT 0')
    cursor.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS continuous_days INTEGER DEFAULT 0')
    
    # 签到记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sign_in_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            date TEXT NOT NULL,
            points INTEGER DEFAULT 0,
            bonus INTEGER DEFAULT 0,
            is_makeup INTEGER DEFAULT 0,
            continuous_days INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            UNIQUE(user_id, date)
        )
    ''')
    
    # 积分流水表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS integral_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            type TEXT NOT NULL,
            points INTEGER NOT NULL,
            balance_after INTEGER,
            description TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    
    # 兑换订单表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exchange_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            item_name TEXT NOT NULL,
            points_cost INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            shipping_address TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    
    db.commit()
    db.close()
    print("Phase 9 数据库表初始化完成")


if __name__ == '__main__':
    init_phase9_tables()
    print("Phase 9 积分系统 API 模块就绪")
