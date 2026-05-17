#!/usr/bin/env python3
"""
心海法律 AI - 管理后台统计 API
提供业务数据给管理后台展示
"""

import sqlite3
import json
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

DB_PATH = "/root/xinhai-legal/data/xinhai_legal.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_business_stats():
    """获取业务统计数据"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    stats = {}
    
    # 用户统计
    cursor.execute("SELECT COUNT(*) as count FROM users WHERE is_active = 1")
    stats['total_users'] = cursor.fetchone()['count']
    
    # 今日新增用户
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("""
        SELECT COUNT(*) as count FROM users 
        WHERE DATE(created_at) = DATE(?)
    """, (today,))
    stats['new_users_today'] = cursor.fetchone()['count']
    
    # 会员用户统计
    cursor.execute("""
        SELECT COUNT(*) as count FROM users 
        WHERE membership IS NOT NULL AND membership != '' 
        AND membership_end > datetime('now')
    """)
    stats['vip_users'] = cursor.fetchone()['count']
    
    # 今日新增会员
    cursor.execute("""
        SELECT COUNT(DISTINCT user_id) as count FROM membership_orders
        WHERE DATE(created_at) = DATE(?) AND status = 'paid'
    """, (today,))
    stats['new_vip_today'] = cursor.fetchone()['count']
    
    # 订单统计
    cursor.execute("SELECT COUNT(*) as count FROM membership_orders WHERE status = 'paid'")
    stats['total_orders'] = cursor.fetchone()['count']
    
    # 待处理订单
    cursor.execute("SELECT COUNT(*) as count FROM membership_orders WHERE status = 'pending'")
    stats['pending_orders'] = cursor.fetchone()['count']
    
    # 收入统计
    cursor.execute("SELECT SUM(price) as total FROM membership_orders WHERE status = 'paid'")
    result = cursor.fetchone()
    stats['total_revenue'] = result['total'] or 0
    
    # 今日收入
    cursor.execute("""
        SELECT SUM(price) as total FROM membership_orders 
        WHERE DATE(created_at) = DATE(?) AND status = 'paid'
    """, (today,))
    result = cursor.fetchone()
    stats['today_revenue'] = result['total'] or 0
    
    conn.close()
    return stats

class StatsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/v1/admin/stats':
            try:
                stats = get_business_stats()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(stats, ensure_ascii=False).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}, ensure_ascii=False).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        print(f"[Stats API] {args[0]}")

if __name__ == '__main__':
    port = 8644
    server = HTTPServer(('127.0.0.1', port), StatsHandler)
    print(f"📊 业务统计 API 启动在 http://127.0.0.1:{port}")
    print(f"   端点：/v1/admin/stats")
    server.serve_forever()
