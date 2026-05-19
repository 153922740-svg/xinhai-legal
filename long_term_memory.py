#!/usr/bin/env python3
"""
心海法律 AI - SQLite 长记忆系统
用途：无限制本地长记忆存储，支持全文搜索

文件位置：/home/admin/xinhai_legal_api/long_term_memory.py
数据库路径：/home/admin/xinhai_legal_api/long_term_memory.db
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

# 配置
DB_PATH = "/home/admin/xinhai_legal_api/long_term_memory.db"

class LongTermMemory:
    """SQLite 长记忆系统"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._init_tables()
    
    def _init_tables(self):
        """初始化数据库表"""
        # 主表：存储记忆
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                content TEXT NOT NULL,
                memory_type TEXT DEFAULT 'general',
                tags TEXT,
                metadata TEXT,
                priority INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 全文搜索虚拟表 (FTS5)
        self.cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                content,
                tags,
                content_rowid=id
            )
        ''')
        
        # 索引
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_session_id ON memories(session_id)
        ''')
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_memory_type ON memories(memory_type)
        ''')
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp ON memories(timestamp)
        ''')
        
        self.conn.commit()
        print(f"✅ 数据库初始化完成：{self.db_path}")
    
    def insert(self, session_id: str, content: str, memory_type: str = 'general',
               tags: List[str] = None, metadata: Dict = None, priority: int = 0) -> int:
        """插入记忆"""
        tags_str = ','.join(tags) if tags else ''
        metadata_str = json.dumps(metadata, ensure_ascii=False) if metadata else '{}'
        
        self.cursor.execute('''
            INSERT INTO memories (session_id, content, memory_type, tags, metadata, priority)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session_id, content, memory_type, tags_str, metadata_str, priority))
        
        memory_id = self.cursor.lastrowid
        
        # 同步到 FTS 索引
        self.cursor.execute('''
            INSERT INTO memories_fts (rowid, content, tags)
            VALUES (?, ?, ?)
        ''', (memory_id, content, tags_str))
        
        self.conn.commit()
        return memory_id
    
    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """全文搜索记忆"""
        self.cursor.execute('''
            SELECT m.* FROM memories m
            JOIN memories_fts fts ON m.id = fts.rowid
            WHERE memories_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        ''', (query, limit))
        
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]
    
    def search_by_session(self, session_id: str, limit: int = 50) -> List[Dict]:
        """按会话 ID 搜索"""
        self.cursor.execute('''
            SELECT * FROM memories
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (session_id, limit))
        
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]
    
    def search_by_type(self, memory_type: str, limit: int = 50) -> List[Dict]:
        """按类型搜索"""
        self.cursor.execute('''
            SELECT * FROM memories
            WHERE memory_type = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (memory_type, limit))
        
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        self.cursor.execute('SELECT COUNT(*) as count FROM memories')
        total = self.cursor.fetchone()['count']
        
        self.cursor.execute('SELECT memory_type, COUNT(*) as count FROM memories GROUP BY memory_type')
        by_type = {row['memory_type']: row['count'] for row in self.cursor.fetchall()}
        
        self.cursor.execute('SELECT DATE(timestamp) as date, COUNT(*) as count FROM memories GROUP BY DATE(timestamp) ORDER BY date DESC LIMIT 7')
        by_date = {row['date']: row['count'] for row in self.cursor.fetchall()}
        
        return {
            'total': total,
            'by_type': by_type,
            'by_date': by_date,
            'db_path': self.db_path,
            'db_size': os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        }
    
    def export_to_json(self, output_path: str) -> int:
        """导出为 JSON"""
        self.cursor.execute('SELECT * FROM memories ORDER BY timestamp DESC')
        rows = self.cursor.fetchall()
        
        data = [dict(row) for row in rows]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return len(data)
    
    def close(self):
        """关闭连接"""
        self.conn.close()


# 命令行工具
if __name__ == '__main__':
    import sys
    
    mem = LongTermMemory()
    
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python3 long_term_memory.py stats          # 显示统计")
        print("  python3 long_term_memory.py search <query> # 搜索记忆")
        print("  python3 long_term_memory.py export <path>  # 导出 JSON")
        print("  python3 long_term_memory.py test           # 测试写入")
        sys.exit(0)
    
    command = sys.argv[1]
    
    if command == 'stats':
        stats = mem.get_stats()
        print("\n📊 长记忆系统统计")
        print("=" * 50)
        print(f"总记忆数：{stats['total']}")
        print(f"数据库大小：{stats['db_size'] / 1024 / 1024:.2f} MB")
        print(f"数据库路径：{stats['db_path']}")
        print("\n按类型分布:")
        for mtype, count in stats['by_type'].items():
            print(f"  {mtype}: {count}")
        print("\n近 7 天:")
        for date, count in stats['by_date'].items():
            print(f"  {date}: {count}")
    
    elif command == 'search' and len(sys.argv) > 2:
        query = ' '.join(sys.argv[2:])
        print(f"\n🔍 搜索：{query}")
        print("=" * 50)
        results = mem.search(query, limit=10)
        for r in results:
            print(f"\n[{r['timestamp']}] (类型：{r['memory_type']})")
            print(f"内容：{r['content'][:200]}...")
    
    elif command == 'export' and len(sys.argv) > 2:
        output_path = sys.argv[2]
        count = mem.export_to_json(output_path)
        print(f"\n✅ 导出完成：{count} 条记忆 → {output_path}")
    
    elif command == 'test':
        print("\n🧪 测试写入...")
        mem_id = mem.insert(
            session_id="test_session",
            content="这是一条测试记忆，用于验证 SQLite 长记忆系统",
            memory_type="test",
            tags=["测试", "验证"],
            metadata={"source": "cli_test"}
        )
        print(f"✅ 写入成功，ID={mem_id}")
        
        print("\n🔍 测试搜索...")
        results = mem.search("测试", limit=5)
        for r in results:
            print(f"  找到：{r['content'][:50]}...")
    
    mem.close()
