"""
心海法律 AI - 性能优化脚本
阶段1：缺失索引添加（覆盖全库高频查询表）
阶段2：响应缓存SQLite（高频只读API）
阶段3：配置常量缓存
"""

import sqlite3
import os
import json
import functools
import time
import hashlib

DB_PATH = '/home/admin/xinhai_legal_api/data/xinhai_legal.db'

# ============================================================
# 阶段1：缺失索引
# ============================================================

MISSING_INDEXES = {
    # 律师模块高频查询
    'lawyer_cases': [
        ('idx_lawyer_cases_lawyer', 'lawyer_id'),
        ('idx_lawyer_cases_status', 'status'),
        ('idx_lawyer_cases_created', 'created_at'),
    ],
    'lawyer_profiles': [
        ('idx_lawyer_profiles_user', 'user_id'),
        ('idx_lawyer_profiles_status', 'status'),
    ],
    'lawyer_invites': [
        ('idx_lawyer_invites_lawyer', 'lawyer_id'),
        ('idx_lawyer_invites_status', 'status'),
    ],
    'lawyer_schedules': [
        ('idx_lawyer_schedule_lawyer', 'lawyer_id'),
        ('idx_lawyer_schedule_date', 'event_date'),
    ],
    'lawyer_wallet': [
        ('idx_lawyer_wallet_user', 'user_id'),
    ],
    'lawyer_fee_records': [
        ('idx_fee_records_lawyer', 'lawyer_id'),
    ],
    'lawyer_notifications': [
        ('idx_notif_lawyer', 'lawyer_id'),
    ],
    'lawyer_case_documents': [
        ('idx_case_docs_case', 'case_id'),
    ],
    'lawyer_ai_tool_logs': [
        ('idx_ai_tool_logs_lawyer', 'lawyer_id'),
        ('idx_ai_tool_logs_tool', 'tool_type'),
    ],
    # 企业常法模块
    'enterprise_companies': [
        ('idx_enterprise_status', 'status'),
        ('idx_enterprise_plan', 'plan'),
        ('idx_enterprise_created', 'created_at'),
    ],
    'enterprise_service_logs': [
        ('idx_service_logs_enterprise', 'enterprise_id'),
        ('idx_service_logs_type', 'service_type'),
    ],
    'enterprise_user_bindings': [
        ('idx_ent_bind_user', 'user_id'),
        ('idx_ent_bind_enterprise', 'enterprise_id'),
    ],
    # 委托付费
    'entrust_orders': [
        ('idx_entrust_user', 'user_id'),
        ('idx_entrust_lawyer', 'lawyer_id'),
        ('idx_entrust_status', 'status'),
    ],
    # 用户高频查询
    'membership_orders': [
        ('idx_member_orders_created', 'created_at'),
        ('idx_member_orders_status', 'status'),
    ],
    'sign_in_records': [
        ('idx_signin_user', 'user_id'),
        ('idx_signin_date', 'sign_date'),
    ],
    'login_logs': [
        ('idx_login_logs_user', 'user_id'),
        ('idx_login_logs_time', 'login_time'),
    ],
    'referrals': [
        ('idx_referrals_partner', 'partner_id'),
        ('idx_referrals_referred', 'referred_user_id'),
    ],
    'promotions': [
        ('idx_promotions_status', 'status'),
        ('idx_promotions_date', 'start_date'),
    ],
}

def add_missing_indexes():
    """添加所有缺失索引"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 获取已有索引
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    existing = {r[0] for r in cursor.fetchall()}

    added = 0
    for table, indexes in MISSING_INDEXES.items():
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        if not cursor.fetchone():
            continue
        for idx_name, column in indexes:
            if idx_name not in existing:
                try:
                    cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})")
                    added += 1
                    print(f"  ✅ {idx_name} ON {table}({column})")
                except Exception as e:
                    print(f"  ⚠️ {idx_name}: {e}")

    conn.commit()
    conn.close()
    print(f"\n共添加 {added} 个索引")
    return added


# ============================================================
# 阶段2：响应缓存
# ============================================================

CACHE_DB_PATH = '/home/admin/xinhai_legal_api/response_cache.sqlite'

def init_cache_db():
    """初始化缓存数据库"""
    conn = sqlite3.connect(CACHE_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS response_cache (
            cache_key TEXT PRIMARY KEY,
            response TEXT,
            created_at REAL,
            ttl INTEGER DEFAULT 300
        )
    """)
    # 清理过期缓存
    cursor.execute("DELETE FROM response_cache WHERE created_at + ttl < ?", (time.time(),))
    conn.commit()
    conn.close()

def cached(ttl=300):
    """缓存装饰器 - 用于高频只读API"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存key
            key_parts = [func.__name__] + [str(a) for a in args] + [f"{k}={v}" for k, v in sorted(kwargs.items())]
            cache_key = hashlib.md5('|'.join(key_parts).encode()).hexdigest()

            conn = sqlite3.connect(CACHE_DB_PATH)
            cursor = conn.cursor()

            # 查缓存
            cursor.execute(
                "SELECT response FROM response_cache WHERE cache_key = ? AND created_at + ttl > ?",
                (cache_key, time.time())
            )
            row = cursor.fetchone()
            if row:
                conn.close()
                return json.loads(row[0])

            # 执行函数
            result = func(*args, **kwargs)

            # 写入缓存
            try:
                cursor.execute(
                    "INSERT OR REPLACE INTO response_cache (cache_key, response, created_at, ttl) VALUES (?, ?, ?, ?)",
                    (cache_key, json.dumps(result, ensure_ascii=False), time.time(), ttl)
                )
                conn.commit()
            except:
                pass
            conn.close()
            return result
        return wrapper
    return decorator


# ============================================================
# 阶段3：配置常量缓存
# ============================================================

class ConfigCache:
    """配置常量缓存 - 减少重复数据库查询"""
    
    _cache = {}
    _ttl = {}
    
    @classmethod
    def get(cls, key, loader_func, ttl=600):
        """获取缓存（带TTL过期）"""
        now = time.time()
        if key in cls._cache and now < cls._ttl.get(key, 0):
            return cls._cache[key]
        
        value = loader_func()
        cls._cache[key] = value
        cls._ttl[key] = now + ttl
        return value
    
    @classmethod
    def invalidate(cls, key):
        """主动失效缓存"""
        cls._cache.pop(key, None)
        cls._ttl.pop(key, None)
    
    @classmethod
    def clear(cls):
        """清空全部缓存"""
        cls._cache.clear()
        cls._ttl.clear()


# ============================================================
# 阶段4：数据库连接池优化
# ============================================================

# SQLite 连接配置：启用 WAL 模式 + 增大缓存
def optimize_db_connection():
    """优化数据库连接参数"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    optimizations = [
        "PRAGMA journal_mode=WAL",
        "PRAGMA synchronous=NORMAL",
        "PRAGMA cache_size=-8000",      # 8MB 缓存
        "PRAGMA temp_store=MEMORY",
        "PRAGMA mmap_size=268435456",   # 256MB 内存映射
        "PRAGMA page_size=4096",
    ]
    for opt in optimizations:
        try:
            cursor.execute(opt)
        except:
            pass
    conn.close()
    print("✅ 数据库连接参数已优化（WAL/NORMAL/8MB缓存/256MB mmap）")


# ============================================================
# 主入口
# ============================================================

if __name__ == '__main__':
    print("=" * 50)
    print("心海法律 AI · 性能优化")
    print("=" * 50)
    
    print("\n📦 阶段1：添加缺失索引...")
    idx_count = add_missing_indexes()
    
    print("\n📦 阶段2：初始化响应缓存数据库...")
    init_cache_db()
    print(f"  ✅ 缓存数据库: {CACHE_DB_PATH}")
    
    print("\n📦 阶段3：配置常量缓存...")
    print("  ✅ ConfigCache 已就绪（支持TTL自动过期）")
    
    print("\n📦 阶段4：数据库连接优化...")
    optimize_db_connection()
    
    print(f"\n{'=' * 50}")
    print(f"✅ 优化完成：{idx_count}个索引 + 响应缓存 + ConfigCache + WAL模式")
    print(f"{'=' * 50}")
