"""
心海法律 AI - 数据库模型
SQLite + embeddings，支撑 PRD v4.0 所有数据需求
"""

import sqlite3
import json
import uuid
import time
import hashlib
import re
import os
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field

# ========== 数据库连接管理 ==========

_db_connections = {}

def get_db(db_path: str = None) -> sqlite3.Connection:
    """获取数据库连接（线程级缓存）"""
    import threading
    key = db_path or 'default'
    tid = threading.get_ident()
    if tid not in _db_connections:
        _db_connections[tid] = {}
    if key not in _db_connections[tid]:
        if not db_path:
            raise ValueError("db_path is required on first call")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _db_connections[tid][key] = conn
    else:
        # 检查连接是否已关闭
        conn = _db_connections[tid][key]
        try:
            conn.execute("SELECT 1")
        except:
            # 连接已关闭，重新创建
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            _db_connections[tid][key] = conn
    return _db_connections[tid][key]


def close_db(db_path: str = None):
    """关闭并清理连接"""
    import threading
    key = db_path or 'default'
    tid = threading.get_ident()
    if tid in _db_connections and key in _db_connections[tid]:
        try:
            _db_connections[tid][key].close()
        except:
            pass
        del _db_connections[tid][key]


def init_db(db_path: str):
    """初始化数据库，创建所有表"""
    conn = get_db(db_path)
    cursor = conn.cursor()
    
    # ========== 基础表 ==========
    
    # users - 用户表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT,
        email TEXT,
        phone TEXT,
        role TEXT DEFAULT 'user' CHECK(role IN ('user', 'agent', 'admin')),
        status TEXT DEFAULT 'active',
        avatar TEXT,
        full_name TEXT,
        id_number TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP,
        is_verified INTEGER DEFAULT 0
    );
    """)
    
    # ========== PRD v4.0 核心表 ==========
    # 扩展 users 表（忽略已存在的列）
    for col_sql in [
        "ALTER TABLE users ADD COLUMN psych_openness REAL DEFAULT 5.0",
        "ALTER TABLE users ADD COLUMN psych_conscientiousness REAL DEFAULT 5.0",
        "ALTER TABLE users ADD COLUMN psych_extraversion REAL DEFAULT 5.0",
        "ALTER TABLE users ADD COLUMN psych_agreeableness REAL DEFAULT 5.0",
        "ALTER TABLE users ADD COLUMN psych_neuroticism REAL DEFAULT 5.0",
        "ALTER TABLE users ADD COLUMN psych_risk_tolerance REAL DEFAULT 5.0",
        "ALTER TABLE users ADD COLUMN consultation_preference TEXT DEFAULT 'text'",
        "ALTER TABLE users ADD COLUMN last_consultation_at TIMESTAMP",
        "ALTER TABLE users ADD COLUMN total_consultations INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN tokens_balance INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN membership TEXT DEFAULT 'free'",
        "ALTER TABLE users ADD COLUMN membership_start TIMESTAMP",
        "ALTER TABLE users ADD COLUMN membership_end TIMESTAMP",
    ]:
        try:
            cursor.execute(col_sql)
        except sqlite3.OperationalError:
            pass  # 列已存在，忽略
    
    # token_transactions - Token交易记录
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS token_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        amount INTEGER NOT NULL,
        balance_after INTEGER NOT NULL DEFAULT 0,
        transaction_type TEXT NOT NULL,
        description TEXT,
        reference_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_token_transactions_user ON token_transactions(user_id);")

    # membership_orders - 会员订单
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS membership_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        plan TEXT NOT NULL,
        price REAL NOT NULL,
        duration_days INTEGER NOT NULL,
        tokens_granted INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',
        paid_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_membership_orders_user ON membership_orders(user_id);")

    # chat_logs - 聊天记录
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        session_id TEXT NOT NULL,
        message_type TEXT NOT NULL CHECK(message_type IN ('user', 'assistant', 'system')),
        content TEXT NOT NULL,
        content_embedding TEXT,
        model_used TEXT,
        tokens_used INTEGER DEFAULT 0,
        response_time_ms INTEGER DEFAULT 0,
        confidence_score REAL DEFAULT 0,
        is_helpful INTEGER,
        feedback_comment TEXT,
        metadata TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_logs_user ON chat_logs(user_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_logs_session ON chat_logs(session_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_logs_created ON chat_logs(created_at);")
    
    # psych_profiles - 心理画像
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS psych_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        openness REAL DEFAULT 5.0 CHECK(openness >= 0 AND openness <= 10),
        conscientiousness REAL DEFAULT 5.0 CHECK(conscientiousness >= 0 AND conscientiousness <= 10),
        extraversion REAL DEFAULT 5.0 CHECK(extraversion >= 0 AND extraversion <= 10),
        agreeableness REAL DEFAULT 5.0 CHECK(agreeableness >= 0 AND agreeableness <= 10),
        neuroticism REAL DEFAULT 5.0 CHECK(neuroticism >= 0 AND neuroticism <= 10),
        risk_tolerance REAL DEFAULT 5.0 CHECK(risk_tolerance >= 0 AND risk_tolerance <= 10),
        assessment_source TEXT DEFAULT 'behavior',
        assessment_confidence REAL DEFAULT 0.5,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_psych_profiles_user ON psych_profiles(user_id);")
    
    # consultation_intents - 咨询意向
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS consultation_intents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        intent_type TEXT NOT NULL DEFAULT 'initial',
        legal_domain TEXT,
        case_type TEXT,
        urgency_level TEXT DEFAULT 'medium',
        budget_range TEXT,
        preferred_contact TEXT,
        description TEXT,
        status TEXT DEFAULT 'new',
        assigned_agent_id INTEGER REFERENCES users(id),
        source TEXT DEFAULT 'web',
        converted_order_id INTEGER,
        priority_score REAL DEFAULT 0,
        notes TEXT,
        contacted_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_consultation_intents_user ON consultation_intents(user_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_consultation_intents_status ON consultation_intents(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_consultation_intents_domain ON consultation_intents(legal_domain);")
    
    # orders - 订单表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_no TEXT UNIQUE NOT NULL,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        order_type TEXT NOT NULL,
        product_id TEXT,
        product_name TEXT NOT NULL,
        original_price REAL NOT NULL DEFAULT 0,
        discount_rate REAL DEFAULT 1.0,
        final_price REAL NOT NULL DEFAULT 0,
        pricing_strategy_id INTEGER REFERENCES pricing_strategies(id),
        quantity INTEGER DEFAULT 1,
        tokens_included INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',
        payment_id INTEGER,
        delivery_id INTEGER,
        agent_id INTEGER REFERENCES users(id),
        commission_amount REAL DEFAULT 0,
        coupon_code TEXT,
        coupon_discount REAL DEFAULT 0,
        remarks TEXT,
        paid_at TIMESTAMP,
        completed_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at);")
    
    # payments - 支付记录
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        payment_no TEXT UNIQUE NOT NULL,
        order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        amount REAL NOT NULL DEFAULT 0,
        currency TEXT DEFAULT 'CNY',
        payment_method TEXT NOT NULL,
        payment_channel TEXT,
        transaction_id TEXT,
        status TEXT DEFAULT 'pending',
        error_code TEXT,
        error_message TEXT,
        paid_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_order ON payments(order_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);")
    
    # chat_contexts - 对话上下文
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_contexts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT UNIQUE NOT NULL,
        user_id INTEGER REFERENCES users(id),
        messages TEXT NOT NULL DEFAULT '[]',
        current_intent TEXT,
        legal_domain TEXT,
        psych_trigger_count INTEGER DEFAULT 0,
        last_psych_trigger TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        message_count INTEGER DEFAULT 0
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_contexts_session ON chat_contexts(session_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_contexts_user ON chat_contexts(user_id);")
    
    # ========== PRD V1.1 用户记忆系统 ==========
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        memory_type TEXT NOT NULL CHECK(memory_type IN ('personal', 'case', 'preference', 'summary')),
        content TEXT NOT NULL,
        session_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_memory_user ON user_memory(user_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_memory_type ON user_memory(memory_type);")

    conn.commit()


# ========== 用户模型 ==========

class UserModel:
    """用户数据访问层"""
    
    @staticmethod
    def create(db_path: str, username: str, password_hash: str = None, email: str = None,
               phone: str = None, role: str = 'user', full_name: str = None) -> Dict:
        """创建用户"""
        conn = get_db(db_path)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO users (username, password_hash, email, phone, role, full_name, created_at, last_login)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (username, password_hash, email, phone, role, full_name, now, now))
        conn.commit()
        user_id = cursor.lastrowid
        return UserModel.get_by_id(db_path, user_id)
    
    @staticmethod
    def get_by_id(db_path: str, user_id: int) -> Optional[Dict]:
        """通过ID获取用户"""
        conn = get_db(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    @staticmethod
    def get_by_username(db_path: str, username: str) -> Optional[Dict]:
        """通过用户名获取用户"""
        conn = get_db(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    @staticmethod
    def get_by_phone(db_path: str, phone: str) -> Optional[Dict]:
        """通过手机号获取用户"""
        conn = get_db(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE phone = ?", (phone,))
        row = cursor.fetchone()
        return dict(row) if row else None

    @staticmethod
    def update_login(db_path: str, user_id: int):
        """更新登录时间"""
        conn = get_db(db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET last_login = ? WHERE id = ?",
                      (datetime.now().isoformat(), user_id))
        conn.commit()
    
    @staticmethod
    def update_profile(db_path: str, user_id: int, **kwargs) -> Optional[Dict]:
        """更新用户信息"""
        allowed = ['email', 'phone', 'full_name', 'avatar', 'id_number']
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return UserModel.get_by_id(db_path, user_id)
        sets = ', '.join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [user_id]
        conn = get_db(db_path)
        cursor = conn.cursor()
        cursor.execute(f"UPDATE users SET {sets} WHERE id = ?", values)
        conn.commit()
        return UserModel.get_by_id(db_path, user_id)
    
    @staticmethod
    def add_tokens(db_path: str, user_id: int, tokens: int, transaction_type: str = 'gift', description: str = '') -> bool:
        """增加用户Token余额"""
        conn = get_db(db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE users SET tokens_balance = COALESCE(tokens_balance, 0) + ? WHERE id = ?
            """, (tokens, user_id))
            # 记录token交易
            cursor.execute("""
                INSERT INTO token_transactions (user_id, amount, balance_after, transaction_type, description)
                VALUES (?, ?, (SELECT COALESCE(tokens_balance, 0) FROM users WHERE id=?), ?, ?)
            """, (user_id, tokens, user_id, transaction_type, description))
            conn.commit()
            return True
        except Exception as e:
            print(f"[UserModel] add_tokens error: {e}")
            conn.rollback()
            return False

    @staticmethod
    def list_users(db_path: str, role: str = None, status: str = 'active',
                   offset: int = 0, limit: int = 20) -> List[Dict]:
        """列出用户"""
        conn = get_db(db_path)
        cursor = conn.cursor()
        conditions = []
        params = []
        if role:
            conditions.append("role = ?")
            params.append(role)
        if status:
            conditions.append("status = ?")
            params.append(status)
        where = " AND ".join(conditions) if conditions else "1=1"
        cursor.execute(f"SELECT * FROM users WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                      params + [limit, offset])
        return [dict(r) for r in cursor.fetchall()]


# ========== 用户记忆模型 ==========

class UserMemoryModel:
    """用户记忆数据访问层"""

    @staticmethod
    def get_db(db_path: str) -> sqlite3.Connection:
        return get_db(db_path)

    @staticmethod
    def save_memory(db_path: str, user_id: int, memory_type: str, content: str, session_id: str = None) -> Dict:
        """保存一条用户记忆"""
        conn = get_db(db_path)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO user_memory (user_id, memory_type, content, session_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, memory_type, content, session_id, now, now))
        conn.commit()
        mem_id = cursor.lastrowid
        cursor.execute("SELECT * FROM user_memory WHERE id = ?", (mem_id,))
        return dict(cursor.fetchone())

    @staticmethod
    def get_memories(db_path: str, user_id: int, memory_type: str = None, limit: int = 50) -> List[Dict]:
        """获取用户记忆"""
        conn = get_db(db_path)
        cursor = conn.cursor()
        if memory_type:
            cursor.execute(
                "SELECT * FROM user_memory WHERE user_id = ? AND memory_type = ? ORDER BY updated_at DESC LIMIT ?",
                (user_id, memory_type, limit)
            )
        else:
            cursor.execute(
                "SELECT * FROM user_memory WHERE user_id = ? ORDER BY updated_at DESC LIMIT ?",
                (user_id, limit)
            )
        return [dict(r) for r in cursor.fetchall()]

    @staticmethod
    def delete_memories(db_path: str, user_id: int, memory_type: str = None):
        """清除用户记忆"""
        conn = get_db(db_path)
        cursor = conn.cursor()
        if memory_type:
            cursor.execute("DELETE FROM user_memory WHERE user_id = ? AND memory_type = ?", (user_id, memory_type))
        else:
            cursor.execute("DELETE FROM user_memory WHERE user_id = ?", (user_id,))
        conn.commit()
        return True
