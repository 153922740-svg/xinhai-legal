#!/usr/bin/env python3
"""
知识库管理脚本
用途：知识条目 CRUD、搜索、统计
文件：/home/admin/xinhai_legal_api/skills/knowledge_manager.py
"""

import sqlite3
import json
import os
from datetime import datetime

DB_PATH = "/home/admin/xinhai_legal_api/knowledge_base.db"

class KnowledgeManager:
    """知识库管理器"""
    
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()
    
    def _init_db(self):
        c = self.conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT NOT NULL,
                tags TEXT,
                author TEXT,
                task_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                view_count INTEGER DEFAULT 0,
                useful_count INTEGER DEFAULT 0,
                version INTEGER DEFAULT 1
            )
        """)
        c.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
                title, content, tags, content_rowid=id
            )
        """)
        self.conn.commit()
        print(f"✅ 知识库初始化：{DB_PATH}")
    
    def add(self, title, content, category, tags="", author="", task_id=""):
        """添加知识条目"""
        c = self.conn.cursor()
        c.execute("""
            INSERT INTO knowledge_items (title, content, category, tags, author, task_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title, content, category, tags, author, task_id))
        item_id = c.lastrowid
        c.execute("INSERT INTO knowledge_fts (rowid, title, content, tags) VALUES (?, ?, ?, ?)",
                  (item_id, title, content, tags))
        self.conn.commit()
        return item_id
    
    def search(self, keywords, category=None, limit=10):
        """搜索知识库"""
        c = self.conn.cursor()
        if category:
            c.execute("""
                SELECT k.* FROM knowledge_items k
                JOIN knowledge_fts fts ON k.id = fts.rowid
                WHERE knowledge_fts MATCH ? AND k.category = ?
                ORDER BY rank LIMIT ?
            """, (keywords, category, limit))
        else:
            c.execute("""
                SELECT k.* FROM knowledge_items k
                JOIN knowledge_fts fts ON k.id = fts.rowid
                WHERE knowledge_fts MATCH ?
                ORDER BY rank LIMIT ?
            """, (keywords, limit))
        return [dict(r) for r in c.fetchall()]
    
    def stats(self):
        """知识库统计"""
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) FROM knowledge_items")
        total = c.fetchone()[0]
        
        c.execute("SELECT category, COUNT(*) as cnt FROM knowledge_items GROUP BY category")
        by_category = {r['category']: r['cnt'] for r in c.fetchall()}
        
        c.execute("SELECT COUNT(*) FROM knowledge_items WHERE view_count >= 3")
        reused = c.fetchone()[0]
        
        return {
            'total': total,
            'by_category': by_category,
            'reuse_rate': round(reused / max(total, 1) * 100, 1),
            'db_size': round(os.path.getsize(DB_PATH) / 1024, 1)
        }
    
    def list_recent(self, limit=10):
        """最近条目"""
        c = self.conn.cursor()
        c.execute("SELECT * FROM knowledge_items ORDER BY created_at DESC LIMIT ?", (limit,))
        return [dict(r) for r in c.fetchall()]

if __name__ == '__main__':
    import sys
    
    db = KnowledgeManager()
    
    if len(sys.argv) < 2:
        print("用法：")
        print("  python3 knowledge_manager.py stats        # 统计")
        print("  python3 knowledge_manager.py add <标题> <内容> <分类> [标签] [作者]")
        print("  python3 knowledge_manager.py search <关键词> [分类]")
        print("  python3 knowledge_manager.py recent       # 最近条目")
        sys.exit(0)
    
    cmd = sys.argv[1]
    
    if cmd == 'stats':
        s = db.stats()
        print("\n📊 知识库统计")
        print("=" * 40)
        print(f"总条目：{s['total']}")
        print(f"分类：{s['by_category']}")
        print(f"复用率：{s['reuse_rate']}%")
        print(f"数据库大小：{s['db_size']} KB")
    
    elif cmd == 'add' and len(sys.argv) >= 4:
        title = sys.argv[2]
        content = sys.argv[3]
        category = sys.argv[4] if len(sys.argv) > 4 else 'tech'
        tags = sys.argv[5] if len(sys.argv) > 5 else ''
        author = sys.argv[6] if len(sys.argv) > 6 else 'system'
        item_id = db.add(title, content, category, tags, author)
        print(f"✅ 已添加条目：ID={item_id}")
    
    elif cmd == 'search' and len(sys.argv) >= 3:
        keywords = sys.argv[2]
        category = sys.argv[3] if len(sys.argv) > 3 else None
        results = db.search(keywords, category)
        print(f"\n🔍 搜索「{keywords}」：共 {len(results)} 条")
        for r in results[:10]:
            print(f"\n[{r['category']}] {r['title']}")
            print(f"  {r['content'][:100]}...")
            print(f"  标签：{r['tags']}")
            print(f"  作者：{r['author']}")
    
    elif cmd == 'recent':
        items = db.list_recent()
        print("\n📋 最近条目")
        for r in items:
            print(f"[{r['category']}] {r['title']} - {r['author']} ({r['created_at']})")
