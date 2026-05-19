#!/usr/bin/env python3
"""
心海法律 AI - Token 优化器
用途：Token 计数/缓存/压缩，节省 Token 使用

文件位置：/home/admin/xinhai_legal_api/token_optimizer.py
"""

import sqlite3
import hashlib
import json
import gzip
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

# 配置
CACHE_DB_PATH = "/home/admin/xinhai_legal_api/token_cache.db"
CACHE_EXPIRY_HOURS = 24  # 缓存过期时间 (小时)
MAX_CACHE_SIZE = 10000  # 最大缓存条目数


class TokenOptimizer:
    """Token 优化器 - 缓存 + 计数 + 压缩"""
    
    def __init__(self, cache_db_path: str = CACHE_DB_PATH):
        self.cache_db_path = cache_db_path
        self._init_cache_db()
        self.token_stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'tokens_saved': 0,
            'tokens_used': 0
        }
    
    def _init_cache_db(self):
        """初始化缓存数据库"""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        # 缓存表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS response_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_hash TEXT UNIQUE NOT NULL,
                question TEXT,
                response TEXT NOT NULL,
                tokens_used INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 1,
                last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_question_hash ON response_cache(question_hash)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_created_at ON response_cache(created_at)
        ''')
        
        # Token 使用统计表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE DEFAULT CURRENT_DATE,
                endpoint TEXT,
                tokens_in INTEGER DEFAULT 0,
                tokens_out INTEGER DEFAULT 0,
                tokens_total INTEGER DEFAULT 0,
                cache_hits INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"✅ Token 缓存数据库初始化完成：{self.cache_db_path}")
    
    def get_cached_response(self, question: str) -> Optional[str]:
        """获取缓存的回答"""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        # 计算问题哈希
        q_hash = hashlib.md5(question.encode('utf-8')).hexdigest()
        
        # 查询缓存 (未过期的)
        cursor.execute('''
            SELECT response, tokens_used FROM response_cache
            WHERE question_hash = ?
            AND created_at > datetime('now', ?)
        ''', (q_hash, f'-{CACHE_EXPIRY_HOURS} hours'))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            self.token_stats['cache_hits'] += 1
            self.token_stats['tokens_saved'] += row[1]
            
            # 更新访问计数
            self._update_cache_access(q_hash)
            
            return row[0]
        
        self.token_stats['cache_misses'] += 1
        return None
    
    def cache_response(self, question: str, response: str, tokens_used: int = 0):
        """缓存回答"""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        q_hash = hashlib.md5(question.encode('utf-8')).hexdigest()
        
        cursor.execute('''
            INSERT OR REPLACE INTO response_cache
            (question_hash, question, response, tokens_used, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        ''', (q_hash, question, response, tokens_used))
        
        # 清理旧缓存 (保持最大大小)
        cursor.execute('''
            DELETE FROM response_cache
            WHERE id NOT IN (
                SELECT id FROM response_cache
                ORDER BY last_accessed DESC
                LIMIT ?
            )
        ''', (MAX_CACHE_SIZE,))
        
        conn.commit()
        conn.close()
    
    def _update_cache_access(self, question_hash: str):
        """更新缓存访问时间"""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE response_cache
            SET access_count = access_count + 1,
                last_accessed = datetime('now')
            WHERE question_hash = ?
        ''', (question_hash,))
        
        conn.commit()
        conn.close()
    
    def record_token_usage(self, endpoint: str, tokens_in: int, tokens_out: int, cache_hits: int = 0):
        """记录 Token 使用"""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        tokens_total = tokens_in + tokens_out
        
        cursor.execute('''
            INSERT INTO token_usage (endpoint, tokens_in, tokens_out, tokens_total, cache_hits)
            VALUES (?, ?, ?, ?, ?)
        ''', (endpoint, tokens_in, tokens_out, tokens_total, cache_hits))
        
        conn.commit()
        conn.close()
        
        self.token_stats['tokens_used'] += tokens_total
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        # 缓存统计
        cursor.execute('SELECT COUNT(*) FROM response_cache')
        cache_size = cursor.fetchone()[0]
        
        cursor.execute('SELECT AVG(access_count) FROM response_cache')
        avg_access = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT SUM(tokens_used) FROM response_cache')
        total_cached_tokens = cursor.fetchone()[0] or 0
        
        # 今日 Token 使用
        cursor.execute('''
            SELECT SUM(tokens_total), SUM(cache_hits)
            FROM token_usage
            WHERE date = CURRENT_DATE
        ''')
        row = cursor.fetchone()
        today_tokens = row[0] or 0
        today_cache_hits = row[1] or 0
        
        conn.close()
        
        return {
            'cache_size': cache_size,
            'avg_cache_access': round(avg_access, 2),
            'total_cached_tokens': total_cached_tokens,
            'today_tokens': today_tokens,
            'today_cache_hits': today_cache_hits,
            'cache_hit_rate': f"{today_cache_hits / max(today_tokens, 1) * 100:.1f}%",
            'session_stats': self.token_stats
        }
    
    def compress_text(self, text: str, level: int = 1) -> str:
        """
        压缩文本 (gzip)
        
        level: 1-9, 1=最快，9=最高压缩率
        """
        compressed = gzip.compress(text.encode('utf-8'), compresslevel=level)
        
        # Base64 编码便于存储
        import base64
        return base64.b64encode(compressed).decode('ascii')
    
    def decompress_text(self, compressed_text: str) -> str:
        """解压缩文本"""
        import base64
        compressed = base64.b64decode(compressed_text.encode('ascii'))
        return gzip.decompress(compressed).decode('utf-8')
    
    def estimate_tokens(self, text: str) -> int:
        """
        估算 Token 数 (中文字符 ≈ 1.5 token/字，英文 ≈ 0.75 token/词)
        """
        # 简单估算：中文字符数 + 英文单词数 * 0.75
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        english_words = len(text.split())
        
        return int(chinese_chars * 1.5 + english_words * 0.75)
    
    def close(self):
        """关闭连接"""
        pass  # SQLite 自动管理


# 命令行工具
if __name__ == '__main__':
    import sys
    
    optimizer = TokenOptimizer()
    
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python3 token_optimizer.py stats              # 显示统计")
        print("  python3 token_optimizer.py test               # 测试缓存")
        print("  python3 token_optimizer.py compress <text>    # 测试压缩")
        print("  python3 token_optimizer.py estimate <text>    # 估算 token")
        sys.exit(0)
    
    command = sys.argv[1]
    
    if command == 'stats':
        stats = optimizer.get_stats()
        print("\n💰 Token 优化器统计")
        print("=" * 50)
        print(f"缓存大小：{stats['cache_size']} 条")
        print(f"平均访问次数：{stats['avg_cache_access']}")
        print(f"缓存 Token 总量：{stats['total_cached_tokens']:,}")
        print(f"\n今日使用:")
        print(f"  Token 使用：{stats['today_tokens']:,}")
        print(f"  缓存命中：{stats['today_cache_hits']}")
        print(f"  命中率：{stats['cache_hit_rate']}")
        print(f"\n会话统计:")
        print(f"  缓存命中：{stats['session_stats']['cache_hits']}")
        print(f"  缓存未命中：{stats['session_stats']['cache_misses']}")
        print(f"  节省 Token: {stats['session_stats']['tokens_saved']:,}")
        print(f"  使用 Token: {stats['session_stats']['tokens_used']:,}")
    
    elif command == 'test':
        print("\n🧪 测试缓存功能...")
        
        # 测试写入
        question = "测试问题：心海法律 AI 的会员价格是多少？"
        response = "新人福利：注册免费 3 天会员；连续包月：首月¥1，次月¥30/月；标准套餐：月卡¥30，季卡¥80，年卡¥288"
        
        print(f"缓存问题：{question}")
        optimizer.cache_response(question, response, tokens_used=100)
        print("✅ 缓存成功")
        
        # 测试读取
        cached = optimizer.get_cached_response(question)
        if cached:
            print(f"✅ 缓存命中：{cached[:50]}...")
        else:
            print("❌ 缓存未命中")
        
        # 再次读取 (应该命中)
        cached2 = optimizer.get_cached_response(question)
        if cached2:
            print(f"✅ 第二次缓存命中：{cached2[:50]}...")
    
    elif command == 'compress' and len(sys.argv) > 2:
        text = ' '.join(sys.argv[2:])
        print(f"\n原文：{text[:100]}...")
        print(f"原文大小：{len(text)} 字符")
        
        compressed = optimizer.compress_text(text)
        print(f"压缩后：{len(compressed)} 字符")
        print(f"压缩率：{len(compressed) / len(text) * 100:.1f}%")
        
        decompressed = optimizer.decompress_text(compressed)
        print(f"解压后：{decompressed[:100]}...")
        print(f"解压验证：{'✅ 正确' if decompressed == text else '❌ 错误'}")
    
    elif command == 'estimate' and len(sys.argv) > 2:
        text = ' '.join(sys.argv[2:])
        tokens = optimizer.estimate_tokens(text)
        print(f"\n文本：{text[:100]}...")
        print(f"字符数：{len(text)}")
        print(f"估算 Token 数：{tokens}")
