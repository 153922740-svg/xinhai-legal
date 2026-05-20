#!/usr/bin/env python3
"""
Hermes Business Bridge P4 — 律师板块 Phase4（钱包模块）
被 hermes_business_api.py 通过 subprocess 调用
实现：钱包信息、提现申请、提现记录、收入明细、结算记录
"""
import sys, json, sqlite3, os
from datetime import datetime

# ==================== 配置 ====================
DB_PATH = '/home/admin/xinhai_legal_api/data/xinhai_legal.db'

# ==================== 数据库操作 ====================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables(params=None):
    """初始化钱包模块相关数据库表"""
    db = get_db()
    cursor = db.cursor()

    # 律师钱包表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lawyer_wallet (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lawyer_id INTEGER UNIQUE NOT NULL,
            balance REAL DEFAULT 0,
            frozen REAL DEFAULT 0,
            pending REAL DEFAULT 0,
            total_income REAL DEFAULT 0,
            total_withdrawn REAL DEFAULT 0,
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        )
    ''')

    # 提现记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lawyer_withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lawyer_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            bank_account TEXT,
            status TEXT DEFAULT 'pending',
            remark TEXT,
            reviewed_by INTEGER,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    ''')

    # 结算记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lawyer_settlements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER,
            lawyer_id INTEGER NOT NULL,
            total_fee REAL,
            platform_commission REAL,
            lawyer_income REAL,
            status TEXT DEFAULT 'pending',
            settled_at TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    ''')

    db.commit()
    db.close()
    return {'success': True, 'data': {'message': '钱包模块表初始化完成'}}


# ==================== 接口实现 ====================

def handle_wallet(params):
    """GET /api/lawyer/wallet - 钱包信息"""
    lawyer_id = params.get('lawyer_id') or params.get('user_id')

    if not lawyer_id:
        return {'success': False, 'error': '缺少 lawyer_id'}

    db = get_db()
    cursor = db.cursor()

    # 尝试转换整数
    try:
        lawyer_id = int(lawyer_id)
    except (ValueError, TypeError):
        pass

    cursor.execute('SELECT * FROM lawyer_wallet WHERE lawyer_id = ?', (lawyer_id,))
    row = cursor.fetchone()

    if not row:
        # 创建默认钱包
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO lawyer_wallet (lawyer_id, balance, frozen, pending, total_income, total_withdrawn, updated_at)
            VALUES (?, 0, 0, 0, 0, 0, ?)
        ''', (lawyer_id, now))
        db.commit()

        data = {
            'lawyer_id': lawyer_id,
            'balance': 0,
            'frozen': 0,
            'pending': 0,
            'total_income': 0,
            'total_withdrawn': 0
        }
    else:
        data = dict(row)

    db.close()
    return {'success': True, 'data': data}


def handle_withdraw(params):
    """POST /api/lawyer/wallet/withdraw - 提现申请
    合规改造：强制提现到律所对公账户，从律师profile读取
    """
    lawyer_id = params.get('lawyer_id') or params.get('user_id')
    amount = params.get('amount')

    if not lawyer_id:
        return {'success': False, 'error': '缺少 lawyer_id'}
    if amount is None:
        return {'success': False, 'error': '缺少提现金额'}

    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return {'success': False, 'error': '金额格式无效'}

    if amount <= 0:
        return {'success': False, 'error': '提现金额必须大于0'}

    try:
        lawyer_id = int(lawyer_id)
    except (ValueError, TypeError):
        pass

    db = get_db()
    cursor = db.cursor()

    # 合规检查：查询律师profile获取律所对公账户
    cursor.execute('SELECT * FROM lawyer_profiles WHERE id = ?', (lawyer_id,))
    profile = cursor.fetchone()
    if not profile:
        db.close()
        return {'success': False, 'error': '律师信息不存在，请先完成入驻'}
    profile = dict(profile)
    firm_bank_name = profile.get('firm_bank_name', '') or ''
    firm_bank_account = profile.get('firm_bank_account', '') or ''
    law_firm = profile.get('law_firm', '') or ''
    if not firm_bank_name or not firm_bank_account:
        db.close()
        return {'success': False, 'error': '律所对公账户信息不完整，请先联系平台完善账户信息'}

    # 查询钱包余额
    cursor.execute('SELECT * FROM lawyer_wallet WHERE lawyer_id = ?', (lawyer_id,))
    wallet = cursor.fetchone()

    if not wallet:
        # 创建默认钱包
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO lawyer_wallet (lawyer_id, balance, frozen, pending, total_income, total_withdrawn, updated_at)
            VALUES (?, 0, 0, 0, 0, 0, ?)
        ''', (lawyer_id, now))
        db.commit()
        db.close()
        return {'success': False, 'error': '钱包余额不足，无法提现'}

    wallet = dict(wallet)
    available = wallet['balance'] - wallet['frozen']

    if amount > available:
        return {'success': False, 'error': f'可提现余额不足（可用: {available}，需提现: {amount}）'}

    # 扣减余额，增加冻结
    new_balance = wallet['balance'] - amount
    new_frozen = wallet['frozen'] + amount
    now = datetime.now().isoformat()

    cursor.execute('''
        UPDATE lawyer_wallet SET balance=?, frozen=?, updated_at=? WHERE id=?
    ''', (new_balance, new_frozen, now, wallet['id']))

    # 写入提现记录表（强制写入律所对公账户）
    cursor.execute('''
        INSERT INTO lawyer_withdrawals (lawyer_id, amount, bank_account, status, firm_bank_name, firm_bank_account, account_name, created_at)
        VALUES (?, ?, ?, 'pending', ?, ?, ?, ?)
    ''', (lawyer_id, amount, firm_bank_account, firm_bank_name, firm_bank_account, law_firm, now))

    withdrawal_id = cursor.lastrowid
    db.commit()
    db.close()

    return {
        'success': True,
        'data': {
            'withdrawal_id': withdrawal_id,
            'amount': amount,
            'firm_bank_name': firm_bank_name,
            'firm_bank_account': firm_bank_account,
            'account_name': law_firm,
            'status': 'pending',
            'message': f'提现申请已提交，将打款至{law_firm}对公账户（{firm_bank_account}），等待审核'
        }
    }


def handle_withdrawals(params):
    """GET /api/lawyer/wallet/withdrawals - 提现记录列表"""
    lawyer_id = params.get('lawyer_id') or params.get('user_id')

    if not lawyer_id:
        return {'success': False, 'error': '缺少 lawyer_id'}

    try:
        lawyer_id = int(lawyer_id)
    except (ValueError, TypeError):
        pass

    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
        SELECT * FROM lawyer_withdrawals WHERE lawyer_id = ?
        ORDER BY created_at DESC
    ''', (lawyer_id,))

    records = [dict(row) for row in cursor.fetchall()]
    db.close()

    return {'success': True, 'data': {'records': records, 'total': len(records)}}


def handle_income(params):
    """GET /api/lawyer/wallet/income - 收入明细"""
    lawyer_id = params.get('lawyer_id') or params.get('user_id')
    start_date = params.get('start_date')
    end_date = params.get('end_date')

    if not lawyer_id:
        return {'success': False, 'error': '缺少 lawyer_id'}

    try:
        lawyer_id = int(lawyer_id)
    except (ValueError, TypeError):
        pass

    db = get_db()
    cursor = db.cursor()

    query = 'SELECT * FROM lawyer_settlements WHERE lawyer_id = ?'
    query_params = [lawyer_id]

    if start_date:
        query += ' AND created_at >= ?'
        query_params.append(start_date)
    if end_date:
        query += ' AND created_at <= ?'
        query_params.append(end_date)

    query += ' ORDER BY created_at DESC'

    cursor.execute(query, query_params)
    records = [dict(row) for row in cursor.fetchall()]
    db.close()

    return {'success': True, 'data': {'records': records, 'total': len(records)}}


def handle_settlements(params):
    """GET /api/lawyer/wallet/settlements - 结算记录"""
    lawyer_id = params.get('lawyer_id') or params.get('user_id')

    if not lawyer_id:
        return {'success': False, 'error': '缺少 lawyer_id'}

    try:
        lawyer_id = int(lawyer_id)
    except (ValueError, TypeError):
        pass

    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
        SELECT * FROM lawyer_settlements WHERE lawyer_id = ?
        ORDER BY created_at DESC
    ''', (lawyer_id,))

    records = [dict(row) for row in cursor.fetchall()]
    db.close()

    return {'success': True, 'data': {'records': records, 'total': len(records)}}


# ==================== 路由分发 ====================

ACTIONS = {
    'create_tables': create_tables,
    'wallet': handle_wallet,
    'withdraw': handle_withdraw,
    'withdrawals': handle_withdrawals,
    'income': handle_income,
    'settlements': handle_settlements,
}


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(json.dumps({'success': False, 'error': '缺少参数'}))
        sys.exit(1)

    action = sys.argv[1]
    body_str = sys.argv[2] if len(sys.argv) > 2 else '{}'
    body = json.loads(body_str)

    handler = ACTIONS.get(action)
    if not handler:
        print(json.dumps({'success': False, 'error': f'未知操作: {action}'}))
        sys.exit(1)

    # 确保表存在
    if action != 'create_tables':
        create_tables()

    result = handler(body)
    print(json.dumps(result, ensure_ascii=False))
