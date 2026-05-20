#!/usr/bin/env python3
"""
Hermes Business Bridge P1 — 律师板块 Phase1（入驻+案件模块）
被 hermes_business_api.py 通过 subprocess 调用
实现：入驻申请、资质上传、审核状态、年费支付、年费状态、个人信息、案件列表/详情/状态/时间线、材料上传/列表
"""
import sys, json, sqlite3, uuid, os
from datetime import datetime, timedelta

# ==================== 配置 ====================
DB_PATH = '/home/admin/xinhai_legal_api/data/xinhai_legal.db'

# ==================== 数据库操作 ====================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables(params=None):
    """初始化律师板块相关数据库表"""
    db = get_db()
    cursor = db.cursor()

    # 律师入驻申请表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lawyer_registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT,
            phone TEXT,
            gender TEXT DEFAULT '',
            birth_date TEXT DEFAULT '',
            id_card TEXT DEFAULT '',
            bar_number TEXT DEFAULT '',
            practice_license TEXT DEFAULT '',
            law_firm TEXT DEFAULT '',
            law_firm_address TEXT DEFAULT '',
            practice_area TEXT DEFAULT '',
            qualification TEXT DEFAULT '',
            experience_years INTEGER DEFAULT 0,
            education TEXT DEFAULT '',
            school TEXT DEFAULT '',
            avatar TEXT DEFAULT '',
            description TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            admin_remark TEXT DEFAULT '',
            reviewed_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(user_id)
        )
    ''')

    # 律师资质材料表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lawyer_certificates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            cert_type TEXT NOT NULL,
            file_url TEXT NOT NULL,
            file_name TEXT DEFAULT '',
            file_size INTEGER DEFAULT 0,
            remark TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
    ''')

    # 年费记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lawyer_fee_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            amount REAL NOT NULL DEFAULT 0,
            pay_type TEXT DEFAULT 'annual',
            pay_method TEXT DEFAULT 'wechat',
            transaction_id TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            paid_at TEXT,
            expire_at TEXT,
            created_at TEXT NOT NULL
        )
    ''')

    # 案件表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lawyer_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lawyer_id INTEGER NOT NULL,
            user_id INTEGER,
            title TEXT NOT NULL,
            type TEXT,
            description TEXT,
            status TEXT DEFAULT 'pending',
            stage TEXT,
            fee REAL,
            court TEXT,
            case_no TEXT,
            opponent TEXT,
            urgency TEXT DEFAULT 'normal',
            started_at TEXT,
            closed_at TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        )
    ''')

    # 案件时间线表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lawyer_case_timeline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL,
            event_type TEXT,
            title TEXT DEFAULT '',
            content TEXT,
            event_date TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    ''')

    # 案件材料表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lawyer_case_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL,
            user_id INTEGER,
            doc_type TEXT,
            file_url TEXT,
            file_name TEXT DEFAULT '',
            file_size INTEGER DEFAULT 0,
            remark TEXT DEFAULT '',
            upload_by INTEGER,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    ''')

    # 确保 users 表有 lawyer_profile 相关字段
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN is_lawyer INTEGER DEFAULT 0')
    except Exception:
        pass
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN lawyer_status TEXT DEFAULT NULL')
    except Exception:
        pass
    # 确保现有表有需要的额外字段
    try:
        cursor.execute('ALTER TABLE lawyer_case_documents ADD COLUMN user_id INTEGER')
    except Exception:
        pass
    try:
        cursor.execute('ALTER TABLE lawyer_case_documents ADD COLUMN file_name TEXT DEFAULT ""')
    except Exception:
        pass
    try:
        cursor.execute('ALTER TABLE lawyer_case_documents ADD COLUMN file_size INTEGER DEFAULT 0')
    except Exception:
        pass
    try:
        cursor.execute('ALTER TABLE lawyer_case_documents ADD COLUMN remark TEXT DEFAULT ""')
    except Exception:
        pass
    try:
        cursor.execute('ALTER TABLE lawyer_case_timeline ADD COLUMN title TEXT DEFAULT ""')
    except Exception:
        pass
    try:
        cursor.execute('ALTER TABLE lawyer_case_timeline ADD COLUMN event_date TEXT')
    except Exception:
        pass

    db.commit()
    db.close()
    return {'success': True, 'data': {'message': '律师板块表初始化完成'}}


# ==================== 入驻模块 ====================


def handle_realname(params):
    """POST /api/lawyer/realname - 实名认证（改造版）
    支持两种模式：
    - mode='wechat_pay'（默认）：微信支付实名授权比对
      前端调起微信支付实名弹窗 → 用户确认 → 前端传auth_code → 后端验证
    - mode='direct'：直接填写（过渡/测试模式）
    """
    user_id = params.get('user_id')
    real_name = params.get('real_name', '').strip()
    idcard = params.get('idcard', '').strip()
    idcard_front = params.get('idcard_front', '')
    idcard_back = params.get('idcard_back', '')
    auth_code = params.get('auth_code', '').strip()
    mode = params.get('mode', 'wechat_pay').strip()

    if not user_id:
        return {'success': False, 'error': '缺少 user_id'}
    if not real_name:
        return {'success': False, 'error': '缺少真实姓名'}
    if not idcard:
        return {'success': False, 'error': '缺少身份证号'}
    if len(idcard) not in (15, 18):
        return {'success': False, 'error': '身份证号格式不正确（15或18位）'}

    # 微信支付实名授权验证
    if mode == 'wechat_pay':
        if not auth_code:
            return {'success': False, 'error': '缺少微信支付授权凭证（auth_code）'}
        # TODO: 调用微信支付实名授权验证接口
        # 接口: POST https://api.mch.weixin.qq.com/v3/realname/verify
        # 参数: auth_code, real_name, idcard
        # 返回: {verified: true/false}
        # 当前阶段：微信支付比对由小程序前端调起弹窗，后端验证auth_code
        # 临时方案：auth_code不为空即视为验证通过（后续接入真实验证）
        auth_ok = bool(auth_code) and len(auth_code) > 4
        if not auth_ok:
            return {'success': False, 'error': '微信支付实名授权验证失败，请重新尝试'}

    db = get_db()
    cursor = db.cursor()

    # 校验users表
    cursor.execute('SELECT full_name, id_number, is_verified FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    if not user:
        db.close()
        return {'success': False, 'error': '用户不存在'}

    user_name = (user[0] or '').strip()
    user_idcard = (user[1] or '').strip()
    already_verified = bool(user[2])

    # 如果已实名认证，直接返回成功
    if already_verified and user_name:
        db.close()
        return {
            'success': True,
            'data': {
                'verified': True,
                'real_name': user_name,
                'idcard_masked': idcard[:3] + '***********' + idcard[-4:] if len(idcard) > 7 else '',
                'message': '已通过实名认证'
            }
        }

    # 如果users表已有实名信息，校验一致性
    if user_name and user_idcard:
        if user_name != real_name:
            db.close()
            return {'success': False, 'error': f'真实姓名与系统记录不一致（系统记录: {user_name}）'}
        if user_idcard != idcard:
            db.close()
            return {'success': False, 'error': '身份证号与系统记录不一致'}
    else:
        # 更新users表
        now = datetime.now().isoformat()
        cursor.execute(
            'UPDATE users SET full_name=?, id_number=?, is_verified=1, realname_channel=? WHERE id=?',
            (real_name, idcard, mode, user_id)
        )

    # 写入律师入驻表
    now = datetime.now().isoformat()
    cursor.execute('SELECT id FROM lawyer_registrations WHERE user_id = ?', (user_id,))
    reg = cursor.fetchone()
    if reg:
        cursor.execute('''
            UPDATE lawyer_registrations SET
                name=?, id_card=?, real_name_verified=1, real_name_idcard=?,
                updated_at=?
            WHERE user_id=?
        ''', (real_name, idcard, idcard, now, user_id))
    else:
        cursor.execute('''
            INSERT INTO lawyer_registrations
                (user_id, name, id_card, real_name_verified, real_name_idcard,
                 status, created_at, updated_at)
            VALUES (?, ?, ?, 1, ?, 'draft', ?, ?)
        ''', (user_id, real_name, idcard, idcard, now, now))

    # 写入 lawyer_profiles
    cursor.execute('SELECT id FROM lawyer_profiles WHERE user_id = ?', (user_id,))
    prof = cursor.fetchone()
    if prof:
        cursor.execute('''
            UPDATE lawyer_profiles SET name=?, real_name_verified=1,
                real_name_idcard=?, updated_at=?
            WHERE user_id=?
        ''', (real_name, idcard, now, user_id))

    # 身份证照片
    if idcard_front:
        cursor.execute('''
            INSERT INTO lawyer_certificates
                (user_id, cert_type, file_url, file_name, created_at)
            VALUES (?, 'idcard_front', ?, '身份证正面', ?)
        ''', (user_id, idcard_front, now))
    if idcard_back:
        cursor.execute('''
            INSERT INTO lawyer_certificates
                (user_id, cert_type, file_url, file_name, created_at)
            VALUES (?, 'idcard_back', ?, '身份证背面', ?)
        ''', (user_id, idcard_back, now))

    db.commit()
    db.close()

    return {
        'success': True,
        'data': {
            'verified': True,
            'real_name': real_name,
            'idcard_masked': idcard[:3] + '***********' + idcard[-4:],
            'realname_channel': mode,
            'message': '实名认证成功'
        }
    }


def handle_realname_status(params):
    """POST /api/lawyer/realname/status - 查询实名认证状态（改造版）"""
    user_id = params.get('user_id')
    if not user_id:
        return {'success': False, 'error': '缺少 user_id'}

    db = get_db()
    cursor = db.cursor()

    cursor.execute('SELECT full_name, id_number, is_verified, realname_channel FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    
    # 查律师执业核验状态
    lawyer_verified = False
    lawyer_verify_channel = None
    license_no = None
    law_firm = None
    cursor.execute('SELECT lawyer_verified, license_no, law_firm FROM lawyer_profiles WHERE user_id = ?', (user_id,))
    lp = cursor.fetchone()
    if lp:
        lawyer_verified = bool(lp[0])
        license_no = lp[1]
        law_firm = lp[2]

    db.close()

    if not row:
        return {'success': False, 'error': '用户不存在'}

    full_name, id_number, is_verified, realname_channel = row
    verified = bool(is_verified) and bool(full_name) and bool(id_number)

    return {
        'success': True,
        'data': {
            'verified': verified,
            'real_name': full_name or '',
            'idcard_masked': (idcard[:3] + '***********' + idcard[-4:]) if (idcard := id_number or '') else '',
            'has_idcard': bool(id_number),
            'realname_channel': realname_channel or 'none',
            'lawyer_verified': lawyer_verified,
            'lawyer_verify_channel': 'ministry_justice' if lawyer_verified else None,
            'license_no': license_no or '',
            'law_firm': law_firm or ''
        }
    }


def handle_register(params):
    """POST /api/lawyer/register - 提交入驻申请"""
    user_id = params.get('user_id')
    name = params.get('name', '')
    phone = params.get('phone', '')
    gender = params.get('gender', '')
    birth_date = params.get('birth_date', '')
    id_card = params.get('id_card', '')
    bar_number = params.get('bar_number', '')
    practice_license = params.get('practice_license', '')
    law_firm = params.get('law_firm', '')
    law_firm_address = params.get('law_firm_address', '')
    practice_area = params.get('practice_area', '')
    qualification = params.get('qualification', '')
    experience_years = int(params.get('experience_years', 0))
    education = params.get('education', '')
    school = params.get('school', '')
    avatar = params.get('avatar', '')
    description = params.get('description', '')
    # 合规改造：律所对公账户信息（必填）
    firm_bank_name = params.get('firm_bank_name', '')
    firm_bank_account = params.get('firm_bank_account', '')
    firm_license_url = params.get('firm_license_url', '')

    if not user_id:
        return {'success': False, 'error': '缺少 user_id'}
    if not name:
        return {'success': False, 'error': '缺少姓名'}
    if not phone:
        return {'success': False, 'error': '缺少手机号'}
    if not bar_number:
        return {'success': False, 'error': '缺少执业证号'}
    if not law_firm:
        return {'success': False, 'error': '律所名称必填'}
    if not firm_bank_name:
        return {'success': False, 'error': '律所开户银行必填'}
    if not firm_bank_account:
        return {'success': False, 'error': '律所对公账号必填'}

    # 实名认证校验：必须通过实名认证才能提交入驻
    db = get_db()
    cursor = db.cursor()

    cursor.execute('SELECT full_name, id_number, is_verified FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    if not user:
        db.close()
        return {'success': False, 'error': '用户不存在'}

    full_name, id_number, is_verified = user
    if not is_verified or not full_name or not id_number:
        db.close()
        return {'success': False, 'error': '请先完成实名认证（/api/lawyer/realname）后再提交入驻'}

    # 实名一致性校验：入驻填写的姓名和身份证号必须与实名认证一致
    if not id_card:
        db.close()
        return {'success': False, 'error': '缺少身份证号（实名认证后需填写）'}
    if full_name != name:
        db.close()
        return {'success': False, 'error': f'入驻姓名与实名认证不一致（实名: {full_name}）'}
    if id_number != id_card:
        db.close()
        return {'success': False, 'error': '入驻身份证号与实名认证不一致'}

    # 检查是否已提交
    cursor.execute('SELECT * FROM lawyer_registrations WHERE user_id = ?', (user_id,))
    existing = cursor.fetchone()

    now = datetime.now().isoformat()

    if existing:
        # 更新已有记录（含律所对公账户）
        cursor.execute('''
            UPDATE lawyer_registrations SET
                name=?, phone=?, gender=?, birth_date=?, id_card=?,
                bar_number=?, practice_license=?, law_firm=?, law_firm_address=?,
                practice_area=?, qualification=?, experience_years=?,
                education=?, school=?, avatar=?, description=?,
                firm_bank_name=?, firm_bank_account=?, firm_license_url=?,
                status='pending', updated_at=?
            WHERE user_id=?
        ''', (name, phone, gender, birth_date, id_card, bar_number,
              practice_license, law_firm, law_firm_address, practice_area,
              qualification, experience_years, education, school,
              avatar, description, firm_bank_name, firm_bank_account,
              firm_license_url, now, user_id))
    else:
        # 新建入驻申请（含律所对公账户）
        cursor.execute('''
            INSERT INTO lawyer_registrations
                (user_id, name, phone, gender, birth_date, id_card,
                 bar_number, practice_license, law_firm, law_firm_address,
                 practice_area, qualification, experience_years,
                 education, school, avatar, description,
                 firm_bank_name, firm_bank_account, firm_license_url,
                 status, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'pending',?,?)
        ''', (user_id, name, phone, gender, birth_date, id_card,
              bar_number, practice_license, law_firm, law_firm_address,
              practice_area, qualification, experience_years,
              education, school, avatar, description,
              firm_bank_name, firm_bank_account, firm_license_url, now, now))

    # 更新用户表 lawyer 状态
    cursor.execute('UPDATE users SET is_lawyer=1, lawyer_status="pending" WHERE id=?', (user_id,))

    db.commit()
    db.close()

    return {
        'success': True,
        'data': {
            'message': '入驻申请已提交，等待审核',
            'status': 'pending'
        }
    }


def handle_cert_upload(params):
    """POST /api/lawyer/cert/upload - 上传资质材料"""
    user_id = params.get('user_id')
    cert_type = params.get('cert_type', '')
    file_url = params.get('file_url', '')
    file_name = params.get('file_name', '')
    file_size = int(params.get('file_size', 0))
    remark = params.get('remark', '')

    if not user_id:
        return {'success': False, 'error': '缺少 user_id'}
    if not cert_type:
        return {'success': False, 'error': '缺少证书类型'}
    if not file_url:
        return {'success': False, 'error': '缺少文件地址'}

    db = get_db()
    cursor = db.cursor()
    now = datetime.now().isoformat()

    cursor.execute('''
        INSERT INTO lawyer_certificates
            (user_id, cert_type, file_url, file_name, file_size, remark, created_at)
        VALUES (?,?,?,?,?,?,?)
    ''', (user_id, cert_type, file_url, file_name, file_size, remark, now))

    cert_id = cursor.lastrowid
    db.commit()
    db.close()

    return {
        'success': True,
        'data': {
            'cert_id': cert_id,
            'message': '资质材料上传成功'
        }
    }


def handle_status(params):
    """GET /api/lawyer/status - 查询审核状态"""
    user_id = params.get('user_id')

    if not user_id:
        return {'success': False, 'error': '缺少 user_id'}

    db = get_db()
    cursor = db.cursor()

    cursor.execute('SELECT * FROM lawyer_registrations WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()

    if not row:
        db.close()
        return {'success': True, 'data': {'registered': False, 'status': 'none'}}

    row_dict = dict(row)
    db.close()

    return {
        'success': True,
        'data': {
            'registered': True,
            'status': row_dict.get('status', 'pending'),
            'admin_remark': row_dict.get('admin_remark', ''),
            'reviewed_at': row_dict.get('reviewed_at'),
            'created_at': row_dict.get('created_at')
        }
    }


def handle_pay_fee(params):
    """POST /api/lawyer/pay-fee - 支付年费"""
    user_id = params.get('user_id')
    amount = float(params.get('amount', 0))
    pay_method = params.get('pay_method', 'wechat')
    transaction_id = params.get('transaction_id', '')

    if not user_id:
        return {'success': False, 'error': '缺少 user_id'}
    if amount <= 0:
        return {'success': False, 'error': '金额无效'}
    if not transaction_id:
        transaction_id = f'TXN{uuid.uuid4().hex[:12].upper()}'

    db = get_db()
    cursor = db.cursor()
    now = datetime.now().isoformat()
    expire_at = (datetime.now() + timedelta(days=365)).isoformat()

    cursor.execute('''
        INSERT INTO lawyer_fee_records
            (user_id, amount, pay_type, pay_method, transaction_id,
             status, paid_at, expire_at, created_at)
        VALUES (?,?,'annual',?,?,'paid',?,?,?)
    ''', (user_id, amount, pay_method, transaction_id, now, expire_at, now))

    record_id = cursor.lastrowid
    db.commit()
    db.close()

    return {
        'success': True,
        'data': {
            'record_id': record_id,
            'transaction_id': transaction_id,
            'amount': amount,
            'paid_at': now,
            'expire_at': expire_at,
            'message': '年费支付成功'
        }
    }


def handle_fee_status(params):
    """GET /api/lawyer/fee-status - 年费状态查询"""
    user_id = params.get('user_id')

    if not user_id:
        return {'success': False, 'error': '缺少 user_id'}

    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
        SELECT * FROM lawyer_fee_records
        WHERE user_id = ? AND status = 'paid'
        ORDER BY created_at DESC LIMIT 1
    ''', (user_id,))
    row = cursor.fetchone()

    if not row:
        db.close()
        return {
            'success': True,
            'data': {
                'paid': False,
                'message': '尚未缴纳年费'
            }
        }

    row_dict = dict(row)
    db.close()

    now = datetime.now()
    expire_at = datetime.fromisoformat(row_dict['expire_at']) if row_dict.get('expire_at') else now
    is_valid = expire_at > now

    return {
        'success': True,
        'data': {
            'paid': True,
            'is_valid': is_valid,
            'amount': row_dict.get('amount', 0),
            'paid_at': row_dict.get('paid_at'),
            'expire_at': row_dict.get('expire_at'),
            'days_remaining': (expire_at - now).days if is_valid else 0
        }
    }


def handle_get_profile(params):
    """GET /api/lawyer/profile - 获取个人信息"""
    user_id = params.get('user_id')

    if not user_id:
        return {'success': False, 'error': '缺少 user_id'}

    db = get_db()
    cursor = db.cursor()

    cursor.execute('SELECT * FROM lawyer_registrations WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()

    if not row:
        db.close()
        return {'success': True, 'data': {'exists': False}}

    profile = dict(row)
    
    # 获取资质材料列表
    cursor.execute('SELECT * FROM lawyer_certificates WHERE user_id = ?', (user_id,))
    certs = [dict(c) for c in cursor.fetchall()]
    profile['certificates'] = certs

    db.close()

    return {
        'success': True,
        'data': {
            'exists': True,
            'profile': profile
        }
    }


def handle_update_profile(params):
    """PUT /api/lawyer/profile - 更新个人资料"""
    user_id = params.get('user_id')

    if not user_id:
        return {'success': False, 'error': '缺少 user_id'}

    db = get_db()
    cursor = db.cursor()

    # 检查是否存在
    cursor.execute('SELECT * FROM lawyer_registrations WHERE user_id = ?', (user_id,))
    existing = cursor.fetchone()

    now = datetime.now().isoformat()

    # 允许更新的字段
    updatable = ['name', 'phone', 'gender', 'birth_date', 'id_card',
                 'bar_number', 'practice_license', 'law_firm', 'law_firm_address',
                 'practice_area', 'qualification', 'experience_years',
                 'education', 'school', 'avatar', 'description']

    if existing:
        set_parts = []
        values = []
        for field in updatable:
            if field in params:
                set_parts.append(f'{field}=?')
                values.append(params[field])
        if not set_parts:
            db.close()
            return {'success': True, 'data': {'message': '无更新内容'}}

        set_parts.append('updated_at=?')
        values.append(now)
        values.append(user_id)

        cursor.execute(f'UPDATE lawyer_registrations SET {",".join(set_parts)} WHERE user_id=?', values)
    else:
        # 如果不存在入驻记录则创建
        fields = ['user_id', 'created_at', 'updated_at']
        placeholders = ['?', '?', '?']
        values = [user_id, now, now]
        for field in updatable:
            if field in params:
                fields.append(field)
                placeholders.append('?')
                values.append(params[field])
        cursor.execute(f'INSERT INTO lawyer_registrations ({",".join(fields)}) VALUES ({",".join(placeholders)})', values)

    db.commit()
    db.close()

    return {
        'success': True,
        'data': {
            'message': '个人资料更新成功'
        }
    }


# ==================== 案件模块 ====================

def handle_cases_list(params):
    """GET /api/lawyer/cases - 案件列表"""
    user_id = params.get('user_id')
    status = params.get('status', '')
    case_type = params.get('type', '')
    page = int(params.get('page', 1))
    # 兼容 page_size 和 limit 参数
    limit = int(params.get('page_size', params.get('limit', 20)))
    keyword = params.get('keyword', '')

    if not user_id:
        return {'success': False, 'error': '缺少 user_id'}

    db = get_db()
    cursor = db.cursor()

    conditions = ['(user_id = ? OR lawyer_id = ?)']
    values = [user_id, user_id]

    if status:
        conditions.append('status = ?')
        values.append(status)
    if case_type:
        conditions.append('type = ?')
        values.append(case_type)
    if keyword:
        conditions.append('(title LIKE ? OR case_no LIKE ? OR description LIKE ?)')
        kw = f'%{keyword}%'
        values.extend([kw, kw, kw])

    where = ' AND '.join(conditions)

    # 总数
    cursor.execute(f'SELECT COUNT(*) as total FROM lawyer_cases WHERE {where}', values)
    total = cursor.fetchone()['total']

    # 分页
    offset = (page - 1) * limit
    cursor.execute(f'SELECT * FROM lawyer_cases WHERE {where} ORDER BY updated_at DESC LIMIT ? OFFSET ?', values + [limit, offset])
    cases = [dict(row) for row in cursor.fetchall()]

    db.close()

    return {
        'success': True,
        'data': {
            'total': total,
            'page': page,
            'limit': limit,
            'items': cases
        }
    }


def handle_case_detail(params):
    """GET /api/lawyer/cases/{id} - 案件详情"""
    case_id = params.get('case_id')
    user_id = params.get('user_id')

    if not case_id:
        return {'success': False, 'error': '缺少 case_id'}

    db = get_db()
    cursor = db.cursor()

    cursor.execute('SELECT * FROM lawyer_cases WHERE id=?', (case_id,))

    row = cursor.fetchone()

    if not row:
        db.close()
        return {'success': False, 'error': '案件不存在'}

    case = dict(row)
    db.close()

    return {
        'success': True,
        'data': case
    }


def handle_case_update_status(params):
    """PUT /api/lawyer/cases/{id}/status - 更新案件状态"""
    case_id = params.get('case_id')
    user_id = params.get('user_id')
    new_status = params.get('status', '')

    if not case_id:
        return {'success': False, 'error': '缺少 case_id'}
    if not new_status:
        return {'success': False, 'error': '缺少 status'}

    valid_statuses = ['pending', 'processing', 'court_session', 'mediation',
                      'judgment', 'appeal', 'closed', 'archived']
    if new_status not in valid_statuses:
        return {'success': False, 'error': f'无效状态，可选: {",".join(valid_statuses)}'}

    db = get_db()
    cursor = db.cursor()
    now = datetime.now().isoformat()

    cursor.execute('UPDATE lawyer_cases SET status=?, updated_at=? WHERE id=?',
                   (new_status, now, case_id))

    if cursor.rowcount == 0:
        db.close()
        return {'success': False, 'error': '案件不存在'}

    # 记录时间线
    cursor.execute('''
        INSERT INTO lawyer_case_timeline
            (case_id, event_type, title, content, event_date, created_at)
        VALUES (?, 'status_change', ?, ?, ?, ?)
    ''', (case_id, f'状态变更为：{new_status}', f'案件状态更新为 {new_status}', now, now))

    db.commit()
    db.close()

    return {
        'success': True,
        'data': {
            'message': f'案件状态已更新为 {new_status}'
        }
    }


def handle_case_timeline(params):
    """GET /api/lawyer/cases/{id}/timeline - 案件时间线"""
    case_id = params.get('case_id')

    if not case_id:
        return {'success': False, 'error': '缺少 case_id'}

    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
        SELECT * FROM lawyer_case_timeline
        WHERE case_id = ?
        ORDER BY event_date DESC, created_at DESC
    ''', (case_id,))

    timeline = [dict(row) for row in cursor.fetchall()]
    db.close()

    return {
        'success': True,
        'data': {
            'total': len(timeline),
            'items': timeline
        }
    }


def handle_case_upload_document(params):
    """POST /api/lawyer/cases/{id}/documents - 上传材料"""
    case_id = params.get('case_id')
    user_id = params.get('user_id')
    doc_type = params.get('doc_type', 'other')
    file_url = params.get('file_url', '')
    file_name = params.get('file_name', '')
    file_size = int(params.get('file_size', 0))
    remark = params.get('remark', '')

    if not case_id:
        return {'success': False, 'error': '缺少 case_id'}
    if not user_id:
        return {'success': False, 'error': '缺少 user_id'}
    if not file_url:
        return {'success': False, 'error': '缺少文件地址'}

    db = get_db()
    cursor = db.cursor()
    now = datetime.now().isoformat()

    cursor.execute('''
        INSERT INTO lawyer_case_documents
            (case_id, user_id, upload_by, doc_type, file_url, file_name, file_size, remark, created_at)
        VALUES (?,?,?,?,?,?,?,?,?)
    ''', (case_id, user_id, user_id, doc_type, file_url, file_name, file_size, remark, now))

    doc_id = cursor.lastrowid

    # 记录时间线
    cursor.execute('''
        INSERT INTO lawyer_case_timeline
            (case_id, event_type, title, content, event_date, created_at)
        VALUES (?, 'document_upload', ?, ?, ?, ?)
    ''', (case_id, f'上传材料：{file_name}', remark or f'上传了材料 {file_name}', now, now))

    db.commit()
    db.close()

    return {
        'success': True,
        'data': {
            'doc_id': doc_id,
            'message': '材料上传成功'
        }
    }


def handle_case_documents(params):
    """GET /api/lawyer/cases/{id}/documents - 材料列表"""
    case_id = params.get('case_id')

    if not case_id:
        return {'success': False, 'error': '缺少 case_id'}

    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
        SELECT * FROM lawyer_case_documents
        WHERE case_id = ?
        ORDER BY created_at DESC
    ''', (case_id,))

    docs = [dict(row) for row in cursor.fetchall()]
    db.close()

    return {
        'success': True,
        'data': {
            'total': len(docs),
            'items': docs
        }
    }


# ==================== 路由调度 ====================

ACTION_MAP = {
    'create_tables': create_tables,
    'register': handle_register,
    'cert_upload': handle_cert_upload,
    'status': handle_status,
    'pay_fee': handle_pay_fee,
    'fee_status': handle_fee_status,
    'get_profile': handle_get_profile,
    'update_profile': handle_update_profile,
    'cases_list': handle_cases_list,
    'case_detail': handle_case_detail,
    'case_update_status': handle_case_update_status,
    'case_timeline': handle_case_timeline,
    'case_upload_document': handle_case_upload_document,
    'case_documents': handle_case_documents,
    'realname': handle_realname,
    'realname_status': handle_realname_status,
}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({'success': False, 'error': '缺少参数 action'}))
        sys.exit(1)

    action = sys.argv[1]
    body_str = sys.argv[2] if len(sys.argv) > 2 else '{}'

    try:
        params = json.loads(body_str) if body_str else {}
    except json.JSONDecodeError as e:
        print(json.dumps({'success': False, 'error': f'JSON解析失败: {str(e)}'}))
        sys.exit(1)

    # 统一处理GET传参：将列表值转为单值
    for k, v in params.items():
        if isinstance(v, list) and len(v) == 1:
            params[k] = v[0]

    try:
        handler = ACTION_MAP.get(action)
        if handler:
            result = handler(params)
        else:
            result = {'success': False, 'error': f'未知操作: {action}'}

        print(json.dumps(result, ensure_ascii=False), flush=True)

        if not result.get('success', True):
            sys.exit(1)
    except Exception as e:
        print(json.dumps({'success': False, 'error': str(e)}, ensure_ascii=False), flush=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
