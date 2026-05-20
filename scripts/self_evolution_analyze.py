#!/usr/bin/env python3
"""
心海法律 AI - 自进化自动分析脚本
每天执行一次，分析Badcase并生成优化建议
执行方式：Cron（每天早上8点）
"""

import sys
import os
import sqlite3
import json
from datetime import datetime, timedelta

DB_PATH = '/home/admin/xinhai_legal_api/data/xinhai_legal.db'
# 自进化API使用旧库，分析时两个库都查
DB_PATH_OLD = '/home/admin/xinhai_legal.db'

def analyze_badcases():
    """分析待处理的Badcase（两个数据库都查）"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # 检查新库是否有badcases表
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='badcases'")
    has_new = cur.fetchone() is not None
    
    # 旧库的自进化数据
    conn_old = sqlite3.connect(DB_PATH_OLD)
    conn_old.row_factory = sqlite3.Row
    cur_old = conn_old.cursor()
    
    cur_old.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='badcases'")
    has_old = cur_old.fetchone() is not None
    
    # 获取待处理的Badcase
    if has_new:
        results = {}
        for status in ['pending', 'confirmed', 'fixed']:
            cur.execute("SELECT COUNT(*) as cnt FROM badcases WHERE status=?", [status])
            results[status] = cur.fetchone()[0]
    else:
        results = {'pending': 0, 'confirmed': 0, 'fixed': 0}
    
    if has_old:
        for status in ['pending', 'confirmed', 'fixed']:
            cur_old.execute("SELECT COUNT(*) as cnt FROM badcases WHERE status=?", [status])
            results[status] = results.get(status, 0) + cur_old.fetchone()[0]
    
    # 今日新增
    today = datetime.now().strftime('%Y-%m-%d')
    today_new = 0
    if has_new:
        cur.execute("SELECT COUNT(*) as cnt FROM badcases WHERE created_at LIKE ?", [f'{today}%'])
        today_new += cur.fetchone()[0]
    if has_old:
        cur_old.execute("SELECT COUNT(*) as cnt FROM badcases WHERE created_at LIKE ?", [f'{today}%'])
        today_new += cur_old.fetchone()[0]
    
    conn_old.close()
    conn.close()
    
    return {
        'pending': results.get('pending', 0),
        'confirmed': results.get('confirmed', 0),
        'fixed': results.get('fixed', 0),
        'today_new': today_new,
        'analyzed_at': datetime.now().isoformat()
    }


def record_iteration(stats):
    """记录模型迭代分析结果（写入新库）"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 确保表存在
    cur.execute("""CREATE TABLE IF NOT EXISTS model_iterations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        version TEXT NOT NULL,
        description TEXT,
        training_data_count INTEGER DEFAULT 0,
        metrics TEXT DEFAULT '{}',
        created_at TEXT NOT NULL
    )""")
    
    version = f"auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    cur.execute("""
        INSERT INTO model_iterations (version, description, training_data_count, metrics, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, [
        version,
        f"自动分析：待处理{stats['pending']}个，已确认{stats['confirmed']}个，已修复{stats['fixed']}个",
        stats['confirmed'] + stats['fixed'],
        json.dumps(stats, ensure_ascii=False),
        datetime.now().isoformat()
    ])
    
    conn.commit()
    conn.close()
    
    return version


if __name__ == '__main__':
    print(f"[自进化] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 开始自动分析...")
    
    stats = analyze_badcases()
    print(f"  Badcase统计: 待处理{stats['pending']}个, 已确认{stats['confirmed']}个, 已修复{stats['fixed']}个")
    print(f"  今日新增: {stats['today_new']}个")
    
    if stats['pending'] > 0:
        print(f"  ⚠️ 有{stats['pending']}个待处理Badcase需要人工确认")
    
    version = record_iteration(stats)
    print(f"  分析记录已保存(version={version})")
    
    print(f"[自进化] 分析完成 ✅")
