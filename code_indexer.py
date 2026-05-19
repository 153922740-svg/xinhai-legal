#!/usr/bin/env python3
"""
心海法律 AI - 代码索引器
用途：建立代码索引，实现关键词检索，减少 Token 消耗

文件位置：/home/admin/xinhai_legal_api/code_indexer.py
"""

import sqlite3
import os
import re
from datetime import datetime
from typing import List, Dict, Optional

# 配置
INDEX_DB_PATH = "/home/admin/xinhai_legal_api/code_index.db"
CODE_DIR = "/home/admin/xinhai_legal_api/"
EXCLUDE_DIRS = ['__pycache__', '.git', 'node_modules', 'venv', '.venv']
EXCLUDE_FILES = ['*.pyc', '*.pyo', '*.so', '*.dll']


class CodeIndexer:
    """代码索引器 - 建立索引 + 关键词检索"""
    
    def __init__(self, db_path: str = INDEX_DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._init_tables()
    
    def _init_tables(self):
        """初始化数据库表"""
        # 文件表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                file_name TEXT,
                file_ext TEXT,
                file_size INTEGER,
                line_count INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 函数/类索引表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS symbols (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER,
                symbol_type TEXT,  -- 'function', 'class', 'method'
                symbol_name TEXT,
                line_start INTEGER,
                line_end INTEGER,
                signature TEXT,
                docstring TEXT,
                keywords TEXT,  -- 关键词 (逗号分隔)
                FOREIGN KEY (file_id) REFERENCES files(id)
            )
        ''')
        
        # 全文搜索虚拟表
        self.cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS symbols_fts USING fts5(
                symbol_name, signature, docstring, keywords,
                content_rowid=id
            )
        ''')
        
        # 索引
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbols_file ON symbols(file_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbols_type ON symbols(symbol_type)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(symbol_name)')
        
        self.conn.commit()
        print(f"✅ 代码索引数据库初始化完成：{self.db_path}")
    
    def scan_directory(self, directory: str = CODE_DIR):
        """扫描目录，建立索引"""
        print(f"\n📂 扫描目录：{directory}")
        
        file_count = 0
        symbol_count = 0
        
        for root, dirs, files in os.walk(directory):
            # 排除目录
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            
            for file in files:
                if not file.endswith('.py'):
                    continue
                
                file_path = os.path.join(root, file)
                file_count += 1
                
                # 索引文件
                file_id = self._index_file(file_path)
                if file_id:
                    # 索引符号
                    symbols = self._extract_symbols(file_path)
                    for symbol in symbols:
                        self._insert_symbol(file_id, symbol)
                        symbol_count += 1
                
                if file_count % 10 == 0:
                    print(f"  已处理 {file_count} 个文件...")
        
        self.conn.commit()
        print(f"\n✅ 索引完成：{file_count} 个文件，{symbol_count} 个符号")
        
        return file_count, symbol_count
    
    def _index_file(self, file_path: str) -> Optional[int]:
        """索引单个文件"""
        try:
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_path)[1]
            file_size = os.path.getsize(file_path)
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                line_count = sum(1 for _ in f)
            
            self.cursor.execute('''
                INSERT OR REPLACE INTO files
                (file_path, file_name, file_ext, file_size, line_count, updated_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            ''', (file_path, file_name, file_ext, file_size, line_count))
            
            return self.cursor.lastrowid
        
        except Exception as e:
            print(f"  ⚠️ 索引失败 {file_path}: {e}")
            return None
    
    def _extract_symbols(self, file_path: str) -> List[Dict]:
        """提取文件中的函数/类"""
        symbols = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
            
            # 提取函数定义
            func_pattern = re.compile(r'^def\s+(\w+)\s*\((.*?)\)\s*:', re.MULTILINE)
            for match in func_pattern.finditer(content):
                func_name = match.group(1)
                params = match.group(2)
                line_num = content[:match.start()].count('\n') + 1
                
                # 提取 docstring
                docstring = self._extract_docstring(lines, line_num)
                
                # 提取关键词
                keywords = self._extract_keywords(docstring + ' ' + params)
                
                symbols.append({
                    'type': 'function',
                    'name': func_name,
                    'line_start': line_num,
                    'line_end': line_num,
                    'signature': f"def {func_name}({params})",
                    'docstring': docstring[:500] if docstring else '',
                    'keywords': keywords
                })
            
            # 提取类定义
            class_pattern = re.compile(r'^class\s+(\w+)(?:\s*\((.*?)\))?\s*:', re.MULTILINE)
            for match in class_pattern.finditer(content):
                class_name = match.group(1)
                bases = match.group(2) or ''
                line_num = content[:match.start()].count('\n') + 1
                
                symbols.append({
                    'type': 'class',
                    'name': class_name,
                    'line_start': line_num,
                    'line_end': line_num,
                    'signature': f"class {class_name}({bases})" if bases else f"class {class_name}",
                    'docstring': '',
                    'keywords': self._extract_keywords(bases)
                })
        
        except Exception as e:
            print(f"  ⚠️ 提取符号失败 {file_path}: {e}")
        
        return symbols
    
    def _extract_docstring(self, lines: List[str], line_num: int) -> str:
        """提取函数文档字符串"""
        if line_num >= len(lines):
            return ''
        
        # 查找下一行的 docstring
        for i in range(line_num, min(line_num + 3, len(lines))):
            line = lines[i].strip()
            if line.startswith('"""') or line.startswith("'''"):
                quote = line[:3]
                if line.count(quote) >= 2:
                    return line.strip(quote)
                # 多行 docstring
                docstring_lines = [line.strip(quote)]
                for j in range(i + 1, len(lines)):
                    if quote in lines[j]:
                        docstring_lines.append(lines[j].split(quote)[0])
                        break
                    docstring_lines.append(lines[j])
                return ' '.join(docstring_lines)
        
        return ''
    
    def _extract_keywords(self, text: str) -> str:
        """提取关键词"""
        # 简单实现：提取中文词和英文单词
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,}', text)
        english_words = re.findall(r'\b[a-zA-Z_]{3,}\b', text)
        
        keywords = chinese_words + english_words
        return ','.join(keywords[:20])  # 限制 20 个关键词
    
    def _insert_symbol(self, file_id: int, symbol: Dict):
        """插入符号索引"""
        self.cursor.execute('''
            INSERT INTO symbols
            (file_id, symbol_type, symbol_name, line_start, line_end, signature, docstring, keywords)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            file_id,
            symbol['type'],
            symbol['name'],
            symbol['line_start'],
            symbol['line_end'],
            symbol['signature'],
            symbol['docstring'],
            symbol['keywords']
        ))
        
        symbol_id = self.cursor.lastrowid
        
        # 同步到 FTS 索引
        self.cursor.execute('''
            INSERT INTO symbols_fts (rowid, symbol_name, signature, docstring, keywords)
            VALUES (?, ?, ?, ?, ?)
        ''', (symbol_id, symbol['name'], symbol['signature'], symbol['docstring'], symbol['keywords']))
    
    def search(self, query: str, limit: int = 20) -> List[Dict]:
        """搜索符号"""
        self.cursor.execute('''
            SELECT s.*, f.file_path
            FROM symbols s
            JOIN symbols_fts fts ON s.id = fts.rowid
            JOIN files f ON s.file_id = f.id
            WHERE symbols_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        ''', (query, limit))
        
        return [dict(row) for row in self.cursor.fetchall()]
    
    def search_by_name(self, name: str, limit: int = 20) -> List[Dict]:
        """按名称搜索"""
        self.cursor.execute('''
            SELECT s.*, f.file_path
            FROM symbols s
            JOIN files f ON s.file_id = f.id
            WHERE s.symbol_name LIKE ?
            LIMIT ?
        ''', (f'%{name}%', limit))
        
        return [dict(row) for row in self.cursor.fetchall()]
    
    def search_by_file(self, file_pattern: str, limit: int = 20) -> List[Dict]:
        """按文件搜索"""
        self.cursor.execute('''
            SELECT s.*, f.file_path
            FROM symbols s
            JOIN files f ON s.file_id = f.id
            WHERE f.file_path LIKE ?
            LIMIT ?
        ''', (f'%{file_pattern}%', limit))
        
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        self.cursor.execute('SELECT COUNT(*) FROM files')
        file_count = self.cursor.fetchone()[0]
        
        self.cursor.execute('SELECT COUNT(*) FROM symbols')
        symbol_count = self.cursor.fetchone()[0]
        
        self.cursor.execute('SELECT symbol_type, COUNT(*) FROM symbols GROUP BY symbol_type')
        by_type = {row[0]: row[1] for row in self.cursor.fetchall()}
        
        return {
            'file_count': file_count,
            'symbol_count': symbol_count,
            'by_type': by_type,
            'db_path': self.db_path,
            'db_size': os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        }
    
    def close(self):
        """关闭连接"""
        self.conn.close()


# 命令行工具
if __name__ == '__main__':
    import sys
    
    indexer = CodeIndexer()
    
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python3 code_indexer.py scan [dir]     # 扫描目录建立索引")
        print("  python3 code_indexer.py stats          # 显示统计")
        print("  python3 code_indexer.py search <query> # 搜索符号")
        print("  python3 code_indexer.py test           # 测试")
        sys.exit(0)
    
    command = sys.argv[1]
    
    if command == 'scan':
        directory = sys.argv[2] if len(sys.argv) > 2 else CODE_DIR
        indexer.scan_directory(directory)
    
    elif command == 'stats':
        stats = indexer.get_stats()
        print("\n📊 代码索引统计")
        print("=" * 50)
        print(f"文件数：{stats['file_count']}")
        print(f"符号数：{stats['symbol_count']}")
        print(f"数据库大小：{stats['db_size'] / 1024 / 1024:.2f} MB")
        print("\n符号类型分布:")
        for stype, count in stats['by_type'].items():
            print(f"  {stype}: {count}")
    
    elif command == 'search' and len(sys.argv) > 2:
        query = ' '.join(sys.argv[2:])
        print(f"\n🔍 搜索：{query}")
        print("=" * 50)
        results = indexer.search(query, limit=10)
        for r in results:
            print(f"\n{r['symbol_type']}: {r['symbol_name']}")
            print(f"  文件：{r['file_path']}:{r['line_start']}")
            print(f"  签名：{r['signature']}")
            if r['docstring']:
                print(f"  文档：{r['docstring'][:100]}...")
    
    elif command == 'test':
        print("\n🧪 测试索引功能...")
        
        # 扫描当前目录
        file_count, symbol_count = indexer.scan_directory(CODE_DIR)
        
        # 测试搜索
        print("\n🔍 测试搜索 '登录'...")
        results = indexer.search("登录", limit=5)
        for r in results:
            print(f"  找到：{r['symbol_name']} @ {r['file_path']}:{r['line_start']}")
    
    indexer.close()
