#!/usr/bin/env python3
"""
代码片段管理脚本
文件：/home/admin/xinhai_legal_api/skills/snippet_manager.py
"""

import sqlite3, json, os

DB_PATH = "/home/admin/xinhai_legal_api/code_snippets.db"

class SnippetManager:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        c = self.conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS code_snippets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                code TEXT NOT NULL,
                language TEXT DEFAULT 'python',
                category TEXT,
                tags TEXT,
                author TEXT DEFAULT '灵指',
                usage_count INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS snippets_fts USING fts5(
                title, description, code, tags, content_rowid=id
            )
        """)
        self.conn.commit()
    
    def add(self, title, desc, code, category="general", tags="", author="灵指"):
        c = self.conn.cursor()
        c.execute("INSERT INTO code_snippets (title, description, code, category, tags, author) VALUES (?,?,?,?,?,?)",
                  (title, desc, code, category, tags, author))
        sid = c.lastrowid
        c.execute("INSERT INTO snippets_fts (rowid, title, description, code, tags) VALUES (?,?,?,?,?)",
                  (sid, title, desc, code, tags))
        self.conn.commit()
        return sid
    
    def search(self, keywords, category=None, limit=10):
        c = self.conn.cursor()
        if category:
            c.execute("SELECT s.* FROM code_snippets s JOIN snippets_fts fts ON s.id=fts.rowid WHERE fts MATCH ? AND s.category=? ORDER BY rank LIMIT ?",
                      (keywords, category, limit))
        else:
            c.execute("SELECT s.* FROM code_snippets s JOIN snippets_fts fts ON s.id=fts.rowid WHERE fts MATCH ? ORDER BY rank LIMIT ?",
                      (keywords, limit))
        return [dict(r) for r in c.fetchall()]
    
    def stats(self):
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) FROM code_snippets")
        total = c.fetchone()[0]
        c.execute("SELECT category, COUNT(*) as cnt FROM code_snippets GROUP BY category")
        by_cat = {r['category']: r['cnt'] for r in c.fetchall()}
        return {'total': total, 'by_category': by_cat,
                'db_size': round(os.path.getsize(DB_PATH)/1024, 1) if os.path.exists(DB_PATH) else 0}

if __name__ == '__main__':
    import sys
    db = SnippetManager()
    if len(sys.argv) < 2:
        print("用法：\n  stats  # 统计\n  add <标题> <说明> <代码> [分类] [标签] [作者]\n  search <关键词> [分类]")
        sys.exit(0)
    cmd = sys.argv[1]
    if cmd == 'stats':
        s = db.stats()
        print(f"📊 代码片段库：{s['total']} 条，{s['by_category']}，{s['db_size']}KB")
    elif cmd == 'search' and len(sys.argv) >= 3:
        cat = sys.argv[3] if len(sys.argv) > 3 else None
        for r in db.search(sys.argv[2], cat):
            print(f"\n[{r['category']}] {r['title']} - {r['author']}")
            print(f"  {r['description'][:80]}{'...' if len(r['description'])>80 else ''}")
