"""
心海法律 AI - Phase 4 用户认证 API
用户注册、登录、短信验证码、微信授权等功能
"""

from flask import Blueprint, request, jsonify, g
from services.auth import AuthService, get_auth_service
import re

phase4_bp = Blueprint('phase4_user', __name__, url_prefix='/api/v4')


def get_auth() -> AuthService:
    """获取认证服务实例"""
    if not hasattr(g, 'auth_service'):
        g.auth_service = get_auth_service()
    return g.auth_service


# ============== 用户注册 ==============

@phase4_bp.route('/user/register', methods=['POST'])
def user_register():
    """
    用户注册
    POST /api/v4/user/register
    
    Body:
    {
        "phone": "13800138000",
        "password": "Test123456",
        "sms_code": "123456",
        "username": "张三",  // 可选
        "invite_code": "ABC123"  // 可选
    }
    
    Response:
    {
        "code": 200,
        "data": {
            "user_id": 123,
            "token": "eyJhbGciOiJIUzI1NiIs...",
            "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
            "expires_in": 86400
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
        
        phone = data.get('phone', '').strip()
        password = data.get('password', '')
        sms_code = data.get('sms_code', '')
        username = data.get('username', '').strip()
        invite_code = data.get('invite_code', '').strip()
        
        # 验证手机号
        if not re.match(r'^1[3-9]\d{9}$', phone):
            return jsonify({
                'code': 400,
                'message': '手机号格式不正确',
                'data': None
            }), 400
        
        # 验证密码
        if len(password) < 6 or len(password) > 20:
            return jsonify({
                'code': 400,
                'message': '密码长度应为 6-20 位',
                'data': None
            }), 400
        
        # 注册
        auth = get_auth()
        result = auth.create_user(phone, password, username, sms_code, invite_code)
        
        if not result['success']:
            return jsonify({
                'code': 400,
                'message': result['message'],
                'data': None
            }), 400
        
        # 生成 Token
        user = auth.get_user_by_id(result['user_id'])
        token = auth.generate_token(user['id'], user['username'], user['membership'])
        refresh_token = auth.generate_refresh_token(user['id'])
        
        # 记录登录
        auth.log_login(user['id'], login_type='register')
        
        return jsonify({
            'code': 200,
            'message': '注册成功',
            'data': {
                'user_id': user['id'],
                'username': user['username'],
                'phone': user['phone'],
                'membership': user['membership'],
                'token': token,
                'refresh_token': refresh_token,
                'expires_in': 86400
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'注册失败：{str(e)}',
            'data': None
        }), 500


# ============== 用户登录 ==============

@phase4_bp.route('/user/login', methods=['POST'])
def user_login():
    """
    用户登录（密码登录）
    POST /api/v4/user/login
    
    Body:
    {
        "phone": "13800138000",
        "password": "Test123456"
    }
    
    Response:
    {
        "code": 200,
        "data": {
            "user_id": 123,
            "token": "eyJhbGciOiJIUzI1NiIs...",
            "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
            "expires_in": 86400
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
        
        phone = data.get('phone', '').strip()
        password = data.get('password', '')
        
        # 验证手机号
        if not re.match(r'^1[3-9]\d{9}$', phone):
            return jsonify({
                'code': 400,
                'message': '手机号格式不正确',
                'data': None
            }), 400
        
        # 查询用户
        auth = get_auth()
        user = auth.get_user_by_phone(phone)
        
        if not user:
            return jsonify({
                'code': 401,
                'message': '手机号或密码错误',
                'data': None
            }), 401
        
        # 验证密码
        if not auth.verify_password(password, user['password_hash'], user['salt']):
            return jsonify({
                'code': 401,
                'message': '手机号或密码错误',
                'data': None
            }), 401
        
        # 生成 Token
        token = auth.generate_token(user['id'], user['username'], user['membership'])
        refresh_token = auth.generate_refresh_token(user['id'])
        
        # 记录登录
        auth.log_login(user['id'], login_type='password')
        
        return jsonify({
            'code': 200,
            'message': '登录成功',
            'data': {
                'user_id': user['id'],
                'username': user['username'],
                'phone': user['phone'],
                'membership': user['membership'],
                'token': token,
                'refresh_token': refresh_token,
                'expires_in': 86400
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'登录失败：{str(e)}',
            'data': None
        }), 500


# ============== 短信验证码登录 ==============

@phase4_bp.route('/user/login/sms', methods=['POST'])
def user_login_sms():
    """
    短信验证码登录（无密码登录）
    POST /api/v4/user/login/sms
    
    Body:
    {
        "phone": "13800138000",
        "sms_code": "123456"
    }
    
    Response: 同登录接口
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'code': 400,
                'message': '请求体不能为空',
                'data': None
            }), 400
        
        phone = data.get('phone', '').strip()
        sms_code = data.get('sms_code', '').strip()
        
        # 验证手机号
        if not re.match(r'^1[3-9]\d{9}$', phone):
            return jsonify({
                'code': 400,
                'message': '手机号格式不正确',
                'data': None
            }), 400
        
        # 验证验证码
        auth = get_auth()
        if not auth.verify_sms_code(phone, sms_code):
            return jsonify({
                'code': 401,
                'message': '验证码错误或已过期',
                'data': None
            }), 401
        
        # 查询或创建用户
        user = auth.get_user_by_phone(phone)
        
        if not user:
            # 新用户自动注册
            result = auth.create_user(phone, '', f"用户{phone[-4:]}")
            if not result['success']:
                return jsonify({
                    'code': 400,
                    'message': result['message'],
                    'data': None
                }), 400
            user = auth.get_user_by_id(result['user_id'])
        
        # 生成 Token
        token = auth.generate_token(user['id'], user['username'], user['membership'])
        refresh_token = auth.generate_refresh_token(user['id'])
        
        # 记录登录
        auth.log_login(user['id'], login_type='sms')
        
        return jsonify({
            'code': 200,
            'message': '登录成功',
            'data': {
                'user_id': user['id'],
                'username': user['username'],
                'phone': user['phone'],
                'membership': user['membership'],
                'token': token,
                'refresh_token': refresh_token,
                'expires_in': 86400
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'登录失败：{str(e)}',
            'data': None
        }), 500


# ============== 发送短信验证码 ==============

@phase4_bp.route('/sms/send', methods=['POST'])
def send_sms_code():
    """
    发送短信验证码
    POST /api/v4/sms/send
    
    Body:
    {
        "phone": "13800138000",
        "scene": "register"  // register/login/reset_password
    }
    
    Response:
    {
        "code": 200,
        "data": {
            "code": "123456",  // 开发环境返回验证码，生产环境应隐藏
            "expire_in": 300
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
        
        phone = data.get('phone', '').strip()
        scene = data.get('scene', 'login')
        
        # 验证手机号
        if not re.match(r'^1[3-9]\d{9}$', phone):
            return jsonify({
                'code': 400,
                'message': '手机号格式不正确',
                'data': None
            }), 400
        
        # 生成验证码
        auth = get_auth()
        code = auth.generate_sms_code(phone)
        
        # TODO: 调用短信服务商 API 发送短信
        # 开发环境直接返回验证码
        print(f"[SMS] {phone}: {code}")
        
        return jsonify({
            'code': 200,
            'message': '验证码已发送',
            'data': {
                'code': code,  # 开发环境，生产环境应移除
                'expire_in': 300
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'发送验证码失败：{str(e)}',
            'data': None
        }), 500


# ============== 重置密码 ==============

@phase4_bp.route('/user/password/reset', methods=['POST'])
def reset_password():
    """
    重置密码
    POST /api/v4/user/password/reset
    
    Body:
    {
        "phone": "13800138000",
        "sms_code": "123456",
        "new_password": "NewPass123"
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
        
        phone = data.get('phone', '').strip()
        sms_code = data.get('sms_code', '').strip()
        new_password = data.get('new_password', '')
        
        # 验证
        if not re.match(r'^1[3-9]\d{9}$', phone):
            return jsonify({
                'code': 400,
                'message': '手机号格式不正确',
                'data': None
            }), 400
        
        if len(new_password) < 6 or len(new_password) > 20:
            return jsonify({
                'code': 400,
                'message': '密码长度应为 6-20 位',
                'data': None
            }), 400
        
        # 重置密码
        auth = get_auth()
        result = auth.reset_password_by_phone(phone, sms_code, new_password)
        
        if not result['success']:
            return jsonify({
                'code': 400,
                'message': result['message'],
                'data': None
            }), 400
        
        return jsonify({
            'code': 200,
            'message': '密码重置成功',
            'data': None
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'重置密码失败：{str(e)}',
            'data': None
        }), 500


# ============== Token 刷新 ==============

@phase4_bp.route('/user/token/refresh', methods=['POST'])
def refresh_token():
    """
    刷新 Token
    POST /api/v4/user/token/refresh
    
    Body:
    {
        "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
    }
    
    Response:
    {
        "code": 200,
        "data": {
            "token": "eyJhbGciOiJIUzI1NiIs...",
            "expires_in": 86400
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
        
        refresh_token = data.get('refresh_token', '')
        
        # 验证刷新 Token
        auth = get_auth()
        payload = auth.verify_token(refresh_token)
        
        if not payload or payload.get('type') != 'refresh':
            return jsonify({
                'code': 401,
                'message': '刷新 Token 无效或已过期',
                'data': None
            }), 401
        
        # 查询用户
        user = auth.get_user_by_id(payload['user_id'])
        if not user:
            return jsonify({
                'code': 404,
                'message': '用户不存在',
                'data': None
            }), 404
        
        # 生成新 Token
        token = auth.generate_token(user['id'], user['username'], user['membership'])
        
        return jsonify({
            'code': 200,
            'message': 'Token 刷新成功',
            'data': {
                'token': token,
                'expires_in': 86400
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'刷新 Token 失败：{str(e)}',
            'data': None
        }), 500


# ============== 用户信息 ==============

@phase4_bp.route('/user/profile', methods=['GET'])
def get_user_profile():
    """
    获取用户信息
    GET /api/v4/user/profile
    
    Headers:
    Authorization: Bearer <token>
    
    Response:
    {
        "code": 200,
        "data": {
            "user_id": 123,
            "username": "张三",
            "phone": "138****8000",
            "membership": "monthly",
            "membership_end": "2026-06-17",
            "tokens_balance": 45000,
            "avatar": null
        }
    }
    """
    try:
        # 从 Header 获取 Token
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({
                'code': 401,
                'message': '未提供认证 Token',
                'data': None
            }), 401
        
        token = auth_header[7:]
        
        # 验证 Token
        auth = get_auth()
        payload = auth.verify_token(token)
        
        if not payload:
            return jsonify({
                'code': 401,
                'message': 'Token 无效或已过期',
                'data': None
            }), 401
        
        # 查询用户
        user = auth.get_user_by_id(payload['user_id'])
        if not user:
            return jsonify({
                'code': 404,
                'message': '用户不存在',
                'data': None
            }), 404
        
        # 脱敏手机号
        phone = user['phone']
        phone_masked = f"{phone[:3]}****{phone[-4:]}"
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'user_id': user['id'],
                'username': user['username'],
                'phone': phone_masked,
                'membership': user.get('membership', 'free'),
                'membership_end': user.get('membership_end'),
                'tokens_balance': user.get('tokens_balance', 0),
                'avatar': user.get('avatar'),
                'created_at': user.get('created_at'),
                'login_count': user.get('login_count', 0)
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取用户信息失败：{str(e)}',
            'data': None
        }), 500


# ============== 微信授权 ==============

@phase4_bp.route('/user/wechat/login', methods=['POST'])
def wechat_login():
    """
    微信授权登录
    POST /api/v4/user/wechat/login
    
    Body:
    {
        "openid": "oXXXXXX",
        "unionid": "uXXXXXX",  // 可选
        "nickname": "微信昵称",  // 可选
        "avatar": "https://..."  // 可选
    }
    
    Response:
    {
        "code": 200,
        "data": {
            "user_id": 123,
            "is_new": true,
            "token": "eyJhbGciOiJIUzI1NiIs...",
            "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
            "expires_in": 86400
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
        
        openid = data.get('openid', '')
        unionid = data.get('unionid', '')
        nickname = data.get('nickname', '')
        avatar = data.get('avatar', '')
        
        if not openid:
            return jsonify({
                'code': 400,
                'message': '缺少 openid',
                'data': None
            }), 400
        
        # 微信登录
        auth = get_auth()
        result = auth.login_by_wechat(openid, unionid)
        
        if not result['success']:
            return jsonify({
                'code': 400,
                'message': '微信登录失败',
                'data': None
            }), 400
        
        # 查询用户
        user = auth.get_user_by_id(result['user_id'])
        
        # 更新昵称和头像
        if nickname:
            from models.db import get_db
            conn = get_db('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
            conn.execute("""
                UPDATE users SET username=?, avatar=? WHERE id=?
            """, (nickname, avatar, user['id']))
            conn.commit()
            conn.close()
            user['username'] = nickname
            user['avatar'] = avatar
        
        # 生成 Token
        token = auth.generate_token(user['id'], user['username'], user['membership'])
        refresh_token = auth.generate_refresh_token(user['id'])
        
        return jsonify({
            'code': 200,
            'message': '登录成功',
            'data': {
                'user_id': user['id'],
                'is_new': result['is_new'],
                'username': user['username'],
                'membership': user['membership'],
                'token': token,
                'refresh_token': refresh_token,
                'expires_in': 86400
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'微信登录失败：{str(e)}',
            'data': None
        }), 500


# ============== 健康检查 ==============

@phase4_bp.route('/health', methods=['GET'])
def auth_health():
    """
    认证系统健康检查
    GET /api/v4/health
    """
    try:
        import sqlite3
        conn = sqlite3.connect('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
        conn.execute("SELECT 1")
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'auth_router': 'available',
            'auth_service': 'available',
            'database': 'connected'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'auth_router': 'unavailable',
            'error': str(e)
        }), 500
