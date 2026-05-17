#!/usr/bin/env python3
"""
心海法律 AI - PRD v4.0 数据库迁移验证脚本
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = "/root/xinhai-legal/data/xinhai_legal.db"

EXPECTED_TABLES = [
    'users', 'chat_logs', 'psych_profiles', 'consultation_intents',
    'orders', 'payments', 'deliveries', 'system_prompts',
    'pricing_strategies', 'optimization_logs'
]

def verify_migration():
    """验证迁移结果"""
    print("=" * 60)
    print("心海法律 AI - PRD v4.0 数据库迁移验证")
    print("=" * 60)
    print(f"\n数据库路径：{DB_PATH}")
    print(f"验证时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    if not os.path.exists(DB_PATH):
        print("✗ 数据库文件不存在")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 验证表
    print("【核心表验证】")
    tables_found = 0
    for table in EXPECTED_TABLES:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        if cursor.fetchone():
            print(f"  ✓ {table}")
            tables_found += 1
        else:
            print(f"  ✗ {table} (缺失)")
    
    print(f"\n表创建进度：{tables_found}/{len(EXPECTED_TABLES)}")
    
    # 验证 users 表扩展字段
    print("\n【users 表扩展字段验证】")
    cursor.execute("PRAGMA table_info(users)")
    users_cols = {row[1] for row in cursor.fetchall()}
    
    expected_cols = [
        'psych_openness', 'psych_conscientiousness', 'psych_extraversion',
        'psych_agreeableness', 'psych_neuroticism', 'psych_risk_tolerance',
        'consultation_preference', 'last_consultation_at', 'total_consultations'
    ]
    
    for col in expected_cols:
        if col in users_cols:
            print(f"  ✓ {col}")
        else:
            print(f"  ✗ {col} (缺失)")
    
    # 统计索引
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")
    index_count = cursor.fetchone()[0]
    print(f"\n【索引统计】共 {index_count} 个自定义索引")
    
    conn.close()
    
    # 总结
    print("\n" + "=" * 60)
    if tables_found == len(EXPECTED_TABLES):
        print("迁移验证结果：✓ 成功")
        print("所有 10 张核心表已创建完成")
        return True
    else:
        print(f"迁移验证结果：✗ 部分失败")
        print(f"缺失 {len(EXPECTED_TABLES) - tables_found} 张表")
        return False

if __name__ == "__main__":
    verify_migration()
