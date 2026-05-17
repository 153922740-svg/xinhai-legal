"""
心海法律 AI - 用户认证服务
提供 JWT Token、短信验证码、微信授权等认证功能
"""

import jwt
import hashlib
import random
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import sqlite3
import os

# JWT 配置
JWT_CONFIG = {
    'secret': 'xinclaw-law-2026-jwt-secret-key-change-in-production',
    'algorithm': 'HS256',
    'expire_hours': 24,
    'refresh_expire_days': 7
}

# 短信验证码配置
SMS_CONFIG = {
    'code_length': 6,
    'expire_minutes': 5,
    'max_attempts': 3
}


class AuthService:
    """用户认证服务"""
    
    def __init__(self, db_path: str = '/home/admin/xinhai_legal_api/data/xinhai_legal.db'):
        self.db_path = db_path
        self._sms_codes: Dict[str, Dict] = {}  # 内存存储短信验证码（生产环境应使用 Redis）
    
    def _get_conn(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    # ============== 密码处理 ==============
    
    def hash_password(self, password: str, salt: str = None) -> tuple:
        """
        密码哈希
        返回：(hashed_password, salt)
        """
        if salt is None:
            salt = hashlib.sha256(os.urandom(32)).hexdigest()
        
        hashed = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return hashed.hex(), salt
    
    def verify_password(self, password: str, hashed: str, salt: str) -> bool:
        """验证密码"""
        computed_hash, _ = self.hash_password(password, salt)
        return computed_hash == hashed
    
    # ============== JWT Token ==============
    
    def generate_token(self, user_id: int, username: str, membership: str = 'free') -> str:
        """
        生成 JWT Token
        """
        payload = {
            'user_id': user_id,
            'username': username,
            'membership': membership,
            'exp': datetime.utcnow() + timedelta(hours=JWT_CONFIG['expire_hours']),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, JWT_CONFIG['secret'], algorithm=JWT_CONFIG['algorithm'])
    
    def generate_refresh_token(self, user_id: int) -> str:
        """
        生成刷新 Token
        """
        payload = {
            'user_id': user_id,
            'type': 'refresh',
            'exp': datetime.utcnow() + timedelta(days=JWT_CONFIG['refresh_expire_days']),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, JWT_CONFIG['secret'], algorithm=JWT_CONFIG['algorithm'])
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        验证 JWT Token
        返回：payload 或 None（无效/过期）
        """
        try:
            payload = jwt.decode(token, JWT_CONFIG['secret'], algorithms=[JWT_CONFIG['algorithm']])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    # ============== 短信验证码 ==============
    
    def generate_sms_code(self, phone: str) -> str:
        """
        生成短信验证码
        """
        code = ''.join([str(random.randint(0, 9)) for _ in range(SMS_CONFIG['code_length'])])
        
        self._sms_codes[phone] = {
            'code': code,
            'created_at': time.time(),
            'attempts': 0
        }
        
        # 清理过期验证码
        self._cleanup_sms_codes()
        
        return code
    
    def verify_sms_code(self, phone: str, code: str) -> bool:
        """
        验证短信验证码
        """
        if phone not in self._sms_codes:
            return False
        
        sms_data = self._sms_codes[phone]
        
        # 检查尝试次数
        if sms_data['attempts'] >= SMS_CONFIG['max_attempts']:
            del self._sms_codes[phone]
            return False
        
        # 检查是否过期
        if time.time() - sms_data['created_at'] > SMS_CONFIG['expire_minutes'] * 60:
            del self._sms_codes[phone]
            return False
        
        # 验证验证码
        sms_data['attempts'] += 1
        if sms_data['code'] != code:
            return False
        
        # 验证成功，删除验证码
        del self._sms_codes[phone]
        return True
    
    def _cleanup_sms_codes(self):
        """清理过期验证码"""
        now = time.time()
        expired = [
            phone for phone, data in self._sms_codes.items()
            if now - data['created_at'] > SMS_CONFIG['expire_minutes'] * 60
        ]
        for phone in expired:
            del self._sms_codes[phone]
    
    # ============== 用户管理 ==============
    
    def get_user_by_phone(self, phone: str) -> Optional[Dict]:
        """
        根据手机号查询用户
        """
        conn = self._get_conn()
        conn.row_factory = sqlite3.Row
        user = conn.execute(
            "SELECT * FROM users WHERE phone=?", (phone,)
        ).fetchone()
        conn.close()
        return dict(user) if user else None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """
        根据用户 ID 查询用户
        """
        conn = self._get_conn()
        conn.row_factory = sqlite3.Row
        user = conn.execute(
            "SELECT * FROM users WHERE id=?", (user_id,)
        ).fetchone()
        conn.close()
        return dict(user) if user else None
    
    def create_user(self, phone: str, password: str, username: str = None, 
                    sms_code: str = None, invite_code: str = None) -> Dict:
        """
        创建新用户
        返回：{'success': bool, 'user_id': int, 'message': str}
        """
        # 验证短信验证码
        if sms_code and not self.verify_sms_code(phone, sms_code):
            return {'success': False, 'message': '短信验证码错误'}
        
        # 检查手机号是否已注册
        existing = self.get_user_by_phone(phone)
        if existing:
            return {'success': False, 'message': '手机号已注册'}
        
        # 生成密码哈希
        hashed_password, salt = self.hash_password(password)
        
        # 生成用户名（如果未提供）
        if not username:
            username = f"用户{phone[-4:]}"
        
        # 插入用户
        conn = self._get_conn()
        cursor = conn.execute("""
            INSERT INTO users (phone, username, password_hash, salt, membership, tokens_balance)
            VALUES (?, ?, ?, ?, 'free', 1000)
        """, (phone, username, hashed_password, salt))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        
        # 赠送新人福利（3 天会员体验）
        self._grant_new_user_bonus(user_id)
        
        return {'success': True, 'user_id': user_id, 'message': '注册成功'}
    
    def _grant_new_user_bonus(self, user_id: int):
        """
        赠送新人福利
        """
        from datetime import datetime, timedelta
        conn = self._get_conn()
        
        # 赠送 3 天体验会员
        expire_at = datetime.now() + timedelta(days=3)
        conn.execute("""
            UPDATE users 
            SET membership='trial', membership_end=?, tokens_balance=tokens_balance+1000
            WHERE id=?
        """, (expire_at.isoformat(), user_id))
        
        # 记录 Token 赠送
        conn.execute("""
            INSERT INTO token_transactions (user_id, amount, balance_after, transaction_type, description)
            VALUES (?, 1000, (SELECT tokens_balance FROM users WHERE id=?), 'bonus', '新人注册赠送')
        """, (user_id, user_id))
        
        conn.commit()
        conn.close()
    
    def update_password(self, user_id: int, new_password: str) -> bool:
        """
        更新密码
        """
        hashed_password, salt = self.hash_password(new_password)
        
        conn = self._get_conn()
        conn.execute("""
            UPDATE users 
            SET password_hash=?, salt=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        """, (hashed_password, salt, user_id))
        conn.commit()
        conn.close()
        return True
    
    def reset_password_by_phone(self, phone: str, sms_code: str, new_password: str) -> Dict:
        """
        通过手机号重置密码
        """
        # 验证短信验证码
        if not self.verify_sms_code(phone, sms_code):
            return {'success': False, 'message': '短信验证码错误'}
        
        # 查询用户
        user = self.get_user_by_phone(phone)
        if not user:
            return {'success': False, 'message': '手机号未注册'}
        
        # 更新密码
        self.update_password(user['id'], new_password)
        
        return {'success': True, 'message': '密码重置成功'}
    
    # ============== 微信授权 ==============
    
    def login_by_wechat(self, openid: str, unionid: str = None) -> Dict:
        """
        微信授权登录
        返回：{'success': bool, 'user_id': int, 'is_new': bool}
        """
        conn = self._get_conn()
        conn.row_factory = sqlite3.Row
        
        # 查询用户
        user = conn.execute(
            "SELECT * FROM users WHERE wechat_openid=?", (openid,)
        ).fetchone()
        
        if user:
            # 已有账号，更新登录时间
            conn.execute("""
                UPDATE users SET last_login=CURRENT_TIMESTAMP WHERE id=?
            """, (user['id'],))
            conn.commit()
            conn.close()
            return {'success': True, 'user_id': user['id'], 'is_new': False}
        
        # 新用户，创建账号
        username = f"微信用户{openid[-6:]}"
        cursor = conn.execute("""
            INSERT INTO users (wechat_openid, wechat_unionid, username, membership, tokens_balance)
            VALUES (?, ?, ?, 'free', 1000)
        """, (openid, unionid, username))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        
        # 赠送新人福利
        self._grant_new_user_bonus(user_id)
        
        return {'success': True, 'user_id': user_id, 'is_new': True}
    
    def bind_wechat(self, user_id: int, openid: str, unionid: str = None) -> bool:
        """
        绑定微信账号
        """
        conn = self._get_conn()
        conn.execute("""
            UPDATE users 
            SET wechat_openid=?, wechat_unionid=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        """, (openid, unionid, user_id))
        conn.commit()
        conn.close()
        return True
    
    # ============== 登录日志 ==============
    
    def log_login(self, user_id: int, ip: str = None, device: str = None, 
                  login_type: str = 'password') -> None:
        """
        记录登录日志
        """
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO login_logs (user_id, ip_address, device_info, login_type)
            VALUES (?, ?, ?, ?)
        """, (user_id, ip, device, login_type))
        conn.execute("""
            UPDATE users SET last_login=CURRENT_TIMESTAMP, login_count=login_count+1 WHERE id=?
        """, (user_id,))
        conn.commit()
        conn.close()


# 全局实例
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """获取认证服务实例"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
