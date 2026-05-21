"""
Phase 8: 用户认证 API
手机号验证码登录/注册
"""

from flask import Blueprint, request, jsonify
import sqlite3
import uuid
from datetime import datetime, timedelta
import os

phase8_bp = Blueprint('phase8', __name__)

# 数据库路径
DB_PATH = os.getenv('DB_PATH', '/home/admin/xinhai_legal_api/data/xinhai_legal.db')

# 验证码存储（内存，5 分钟有效）
VERIFICATION_CODES = {}

# 配置
NEW_USER_TOKEN_BONUS = 100  # 新用户赠送 Token
NEW_USER_TRIAL_DAYS = 3     # 会员体验天数

def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db

def generate_code():
    """生成 6 位验证码"""
    import random
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])

# ============== 发送验证码 ==============

@phase8_bp.route('/api/v1/auth/send_sms', methods=['POST'])
def send_sms():
    """发送验证码"""
    try:
        data = request.get_json()
        phone = data.get('phone')
        
        if not phone:
            return jsonify({'code': 400, 'message': '缺少手机号'}), 400
        
        # 检查手机号格式
        if not phone.startswith('+86') and len(phone) != 11:
            return jsonify({'code': 400, 'message': '手机号格式不正确'}), 400
        
        # 生成验证码
        code = generate_code()
        
        # 存储验证码（5 分钟有效）
        VERIFICATION_CODES[phone] = {
            'code': code,
            'expires_at': datetime.now() + timedelta(minutes=5)
        }
        
        # 打印验证码（开发模式）
        print(f"[短信验证码] {phone}: {code}")
        
        return jsonify({
            'code': 200,
            'message': '验证码已发送',
            'data': {'expires_in': 300, 'dev_code': code}
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'发送失败：{str(e)}'}), 500


# ============== 登录/注册 ==============

@phase8_bp.route('/api/v1/auth/login', methods=['POST'])
def login():
    """手机号 + 验证码登录/注册"""
    try:
        data = request.get_json()
        phone = data.get('phone')
        code = data.get('code')
        
        if not phone or not code:
            return jsonify({'code': 400, 'message': '缺少手机号或验证码'}), 400
        
        # 验证验证码
        # 开发模式：支持固定验证码 888888
        if code == '888888':
            pass  # 开发模式，直接通过
        elif phone not in VERIFICATION_CODES:
            return jsonify({'code': 400, 'message': '请先获取验证码'}), 400
        else:
            stored = VERIFICATION_CODES[phone]
            if stored['code'] != code:
                return jsonify({'code': 400, 'message': '验证码错误'}), 400
            if datetime.now() > stored['expires_at']:
                del VERIFICATION_CODES[phone]
                return jsonify({'code': 400, 'message': '验证码已过期'}), 400
            # 删除验证码（一次性使用）
            del VERIFICATION_CODES[phone]
        
        db = get_db()
        cursor = db.cursor()
        
        # 查找用户
        cursor.execute('SELECT * FROM users WHERE phone = ?', (phone,))
        user = cursor.fetchone()
        
        user_id = None
        is_new = False
        
        if user:
            # 老用户登录
            user_id = user['id']
            is_new = False
        else:
            # 新用户注册
            user_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO users (id, phone, nickname, created_at)
                VALUES (?, ?, ?, ?)
            ''', (user_id, phone, f'用户{phone[-4:]}', datetime.now().isoformat()))
            
            # 赠送新用户 Token
            cursor.execute('''
                INSERT INTO token_balances (user_id, balance, created_at)
                VALUES (?, ?, ?)
            ''', (user_id, NEW_USER_TOKEN_BONUS, datetime.now().isoformat()))
            
            # 赠送 3 天会员体验
            cursor.execute('''
                INSERT INTO memberships (user_id, type, started_at, expires_at, status)
                VALUES (?, 'trial', ?, ?, 'active')
            ''', (
                user_id,
                datetime.now().isoformat(),
                (datetime.now() + timedelta(days=NEW_USER_TRIAL_DAYS)).isoformat()
            ))
            
            db.commit()
            is_new = True
        
        db.close()
        
        # 生成登录 token（简化版，生产环境应用 JWT）
        login_token = str(uuid.uuid4())
        
        return jsonify({
            'code': 200,
            'message': '登录成功',
            'data': {
                'is_new': is_new,
                'user': {
                    'id': user_id,
                    'phone': phone,
                    'nickname': f'用户{phone[-4:]}'
                },
                'token': login_token
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'code': 500, 'message': f'登录失败：{str(e)}'}), 500


# ============== 微信登录 ==============

@phase8_bp.route('/api/v1/auth/wx_login', methods=['POST'])
def wx_login():
    """微信小程序登录"""
    try:
        data = request.get_json()
        js_code = data.get('code')
        
        if not js_code:
            return jsonify({'code': 400, 'message': '缺少微信 code'}), 400
        
        # TODO: 调用微信接口获取 openid
        # 这里简化处理
        
        return jsonify({
            'code': 200,
            'message': '微信登录成功'
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'登录失败：{str(e)}'}), 500
