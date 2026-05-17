#!/usr/bin/env python3
"""
心海法律 AI - PRD v4.0 数据库迁移脚本
执行数据库迁移并验证结果
"""

import sqlite3
import os
import sys
from datetime import datetime
from pathlib import Path

# 配置
DB_PATH = "/root/xinhai-legal/data/xinhai_legal.db"
BACKUP_DIR = "/root/xinhai-legal/data/backups"
MIGRATION_SQL = "/root/xinhai-legal/migrations/001_prd_v4_core_tables.sql"

# 预期表列表
EXPECTED_TABLES = [
    'users', 'chat_logs', 'psych_profiles', 'consultation_intents',
    'orders', 'payments', 'deliveries', 'system_prompts',
    'pricing_strategies', 'optimization_logs'
]

EXPECTED_VIEWS = [
    'v_user_full_profile', 'v_order_full', 'v_consultation_funnel'
]

EXPECTED_INDICES_COUNT = 25  # 预期索引数量


def backup_database():
    """备份原数据库"""
    import shutil
    
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{BACKUP_DIR}/xinhai_legal.db.backup.{timestamp}"
    
    if os.path.exists(DB_PATH):
        shutil.copy2(DB_PATH, backup_path)
        print(f"✓ 数据库已备份至：{backup_path}")
        return backup_path
    else:
        print(f"⚠ 原数据库不存在，跳过备份")
        return None


def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def run_migration():
    """执行迁移脚本"""
    print("\n" + "="*60)
    print("开始执行数据库迁移...")
    print("="*60)
    
    if not os.path.exists(MIGRATION_SQL):
        print(f"✗ 迁移文件不存在：{MIGRATION_SQL}")
        return False
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        with open(MIGRATION_SQL, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        # 执行 SQL 脚本
        cursor.executescript(sql_script)
        conn.commit()
        
        print("✓ 迁移脚本执行成功")
        return True
        
    except sqlite3.Error as e:
        print(f"✗ 迁移执行失败：{e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def verify_tables():
    """验证表是否创建成功"""
    print("\n" + "="*60)
    print("验证表结构...")
    print("="*60)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    results = {
        'tables': {'expected': len(EXPECTED_TABLES), 'found': 0, 'missing': []},
        'views': {'expected': len(EXPECTED_VIEWS), 'found': 0, 'missing': []},
        'indices': {'expected': EXPECTED_INDICES_COUNT, 'found': 0}
    }
    
    # 验证表
    print("\n【核心表验证】")
    for table in EXPECTED_TABLES:
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """, (table,))
        if cursor.fetchone():
            print(f"  ✓ {table}")
            results['tables']['found'] += 1
        else:
            print(f"  ✗ {table} (缺失)")
            results['tables']['missing'].append(table)
    
    # 验证视图
    print("\n【视图验证】")
    for view in EXPECTED_VIEWS:
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='view' AND name=?
        """, (view,))
        if cursor.fetchone():
            print(f"  ✓ {view}")
            results['views']['found'] += 1
        else:
            print(f"  ✗ {view} (缺失)")
            results['views']['missing'].append(view)
    
    # 验证索引数量
    cursor.execute("""
        SELECT COUNT(*) FROM sqlite_master 
        WHERE type='index' AND name NOT LIKE 'sqlite_%'
    """)
    results['indices']['found'] = cursor.fetchone()[0]
    print(f"\n【索引验证】共 {results['indices']['found']} 个索引")
    
    conn.close()
    return results


def verify_table_structure():
    """验证关键表的字段结构"""
    print("\n" + "="*60)
    print("验证表字段结构...")
    print("="*60)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 验证 users 表扩展字段
    print("\n【users 表扩展字段】")
    cursor.execute("PRAGMA table_info(users)")
    users_columns = {row[1] for row in cursor.fetchall()}
    
    expected_extensions = [
        'psych_openness', 'psych_conscientiousness', 'psych_extraversion',
        'psych_agreeableness', 'psych_neuroticism', 'psych_risk_tolerance',
        'consultation_preference', 'last_consultation_at', 'total_consultations'
    ]
    
    for col in expected_extensions:
        if col in users_columns:
            print(f"  ✓ {col}")
        else:
            print(f"  ✗ {col} (缺失)")
    
    # 验证 chat_logs 表
    print("\n【chat_logs 表结构】")
    cursor.execute("PRAGMA table_info(chat_logs)")
    chat_columns = {row[1] for row in cursor.fetchall()}
    expected_chat = {'id', 'user_id', 'session_id', 'message_type', 'content', 'created_at'}
    for col in expected_chat:
        status = "✓" if col in chat_columns else "✗"
        print(f"  {status} {col}")
    
    # 验证 psych_profiles 表
    print("\n【psych_profiles 表结构】")
    cursor.execute("PRAGMA table_info(psych_profiles)")
    psych_columns = {row[1] for row in cursor.fetchall()}
    expected_psych = {'id', 'user_id', 'openness', 'conscientiousness', 'extraversion', 
                      'agreeableness', 'neuroticism', 'risk_tolerance'}
    for col in expected_psych:
        status = "✓" if col in psych_columns else "✗"
        print(f"  {status} {col}")
    
    # 验证 orders 表
    print("\n【orders 表结构】")
    cursor.execute("PRAGMA table_info(orders)")
    orders_columns = {row[1] for row in cursor.fetchall()}
    expected_orders = {'id', 'order_no', 'user_id', 'order_type', 'original_price', 
                       'final_price', 'pricing_strategy_id', 'status'}
    for col in expected_orders:
        status = "✓" if col in orders_columns else "✗"
        print(f"  {status} {col}")
    
    conn.close()


def verify_default_data():
    """验证默认数据是否插入"""
    print("\n" + "="*60)
    print("验证默认数据...")
    print("="*60)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 验证 system_prompts 默认数据
    cursor.execute("SELECT COUNT(*) FROM system_prompts")
    prompts_count = cursor.fetchone()[0]
    print(f"\n【system_prompts】{prompts_count} 条记录")
    
    cursor.execute("SELECT prompt_name FROM system_prompts WHERE is_default=1")
    default_prompts = [row[0] for row in cursor.fetchall()]
    print(f"  默认提示词：{default_prompts}")
    
    # 验证 pricing_strategies 默认数据
    cursor.execute("SELECT COUNT(*) FROM pricing_strategies")
    pricing_count = cursor.fetchone()[0]
    print(f"\n【pricing_strategies】{pricing_count} 条记录")
    
    cursor.execute("SELECT strategy_name FROM pricing_strategies WHERE is_active=1")
    active_strategies = [row[0] for row in cursor.fetchall()]
    print(f"  激活策略：{active_strategies}")
    
    conn.close()


def test_constraints():
    """测试约束条件"""
    print("\n" + "="*60)
    print("测试约束条件...")
    print("="*60)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    tests_passed = 0
    tests_total = 0
    
    # 测试 CHECK 约束 - psych_profiles 范围
    tests_total += 1
    try:
        cursor.execute("""
            INSERT INTO psych_profiles (user_id, openness) VALUES (999999, 15.0)
        """)
        print("  ✗ psych_profiles.openness 范围约束失效")
        conn.rollback()
    except sqlite3.IntegrityError:
        print("  ✓ psych_profiles.openness 范围约束有效 (0-10)")
        tests_passed += 1
        conn.rollback()
    
    # 测试 CHECK 约束 - message_type
    tests_total += 1
    try:
        cursor.execute("""
            INSERT INTO chat_logs (user_id, session_id, message_type, content) 
            VALUES (999999, 'test', 'invalid_type', 'test')
        """)
        print("  ✗ chat_logs.message_type 约束失效")
        conn.rollback()
    except sqlite3.IntegrityError:
        print("  ✓ chat_logs.message_type 约束有效 (user/assistant/system)")
        tests_passed += 1
        conn.rollback()
    
    # 测试 CHECK 约束 - order status
    tests_total += 1
    try:
        cursor.execute("""
            INSERT INTO orders (order_no, user_id, order_type, product_name, status) 
            VALUES ('TEST001', 999999, 'consultation', 'Test', 'invalid_status')
        """)
        print("  ✗ orders.status 约束失效")
        conn.rollback()
    except sqlite3.IntegrityError:
        print("  ✓ orders.status 约束有效")
        tests_passed += 1
        conn.rollback()
    
    # 测试 UNIQUE 约束
    tests_total += 1
    try:
        cursor.execute("""
            INSERT INTO system_prompts (prompt_name, prompt_category, prompt_template, version) 
            VALUES ('test_duplicate', 'consultation', 'test', '1.0.0')
        """)
        cursor.execute("""
            INSERT INTO system_prompts (prompt_name, prompt_category, prompt_template, version) 
            VALUES ('test_duplicate', 'consultation', 'test', '1.0.0')
        """)
        print("  ✗ system_prompts 唯一约束失效")
        conn.rollback()
    except sqlite3.IntegrityError:
        print("  ✓ system_prompts (name, version) 唯一约束有效")
        tests_passed += 1
        conn.rollback()
    
    print(f"\n约束测试通过率：{tests_passed}/{tests_total}")
    
    conn.close()
    return tests_passed == tests_total


def generate_report(results):
    """生成验证报告"""
    print("\n" + "="*60)
    print("迁移验证报告")
    print("="*60)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = f"""
================================================================================
                    心海法律 AI - PRD v4.0 数据库迁移验证报告
================================================================================

执行时间：{timestamp}
数据库路径：{DB_PATH}

--------------------------------------------------------------------------------
【表创建情况】
--------------------------------------------------------------------------------
预期表数：{results['tables']['expected']}
实际创建：{results['tables']['found']}
缺失表：{results['tables']['missing'] if results['tables']['missing'] else '无'}
状态：{'✓ 通过' if results['tables']['found'] == results['tables']['expected'] else '✗ 失败'}

--------------------------------------------------------------------------------
【视图创建情况】
--------------------------------------------------------------------------------
预期视图数：{results['views']['expected']}
实际创建：{results['views']['found']}
缺失视图：{results['views']['missing'] if results['views']['missing'] else '无'}
状态：{'✓ 通过' if results['views']['found'] == results['views']['expected'] else '✗ 失败'}

--------------------------------------------------------------------------------
【索引创建情况】
--------------------------------------------------------------------------------
索引总数：{results['indices']['found']}
状态：{'✓ 通过' if results['indices']['found'] >= results['indices']['expected'] else '⚠ 部分通过'}

--------------------------------------------------------------------------------
【迁移总结】
--------------------------------------------------------------------------------
"""
    
    all_passed = (
        results['tables']['found'] == results['tables']['expected'] and
        results['views']['found'] == results['views']['expected']
    )
    
    if all_passed:
        report += "迁移状态：✓ 成功完成\n"
        report += "\n所有核心表、视图和索引已创建成功。\n"
    else:
        report += "迁移状态：✗ 存在问题\n"
        report += "\n请检查上述缺失的表和视图。\n"
    
    report += """
================================================================================
                              报告结束
================================================================================
"""
    
    # 保存报告
    report_path = "/root/xinhai-legal/docs/migration_report.txt"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(report)
    print(f"\n报告已保存至：{report_path}")
    
    return all_passed


def main():
    """主函数"""
    print("\n" + "="*60)
    print("心海法律 AI - PRD v4.0 数据库迁移工具")
    print("="*60)
    
    # 1. 备份数据库
    backup_path = backup_database()
    
    # 2. 执行迁移
    if not run_migration():
        print("\n✗ 迁移失败，请检查错误信息")
        if backup_path:
            print(f"可从备份恢复：{backup_path}")
        sys.exit(1)
    
    # 3. 验证表结构
    results = verify_tables()
    
    # 4. 验证字段结构
    verify_table_structure()
    
    # 5. 验证默认数据
    verify_default_data()
    
    # 6. 测试约束条件
    test_constraints()
    
    # 7. 生成报告
    success = generate_report(results)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
