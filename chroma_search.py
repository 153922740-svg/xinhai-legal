#!/usr/bin/env python3
"""
心海法律 AI - ChromaDB 向量检索
用途：语义搜索，相似问题查找，减少 Token 消耗

文件位置：/home/admin/xinhai_legal_api/chroma_search.py
"""

import chromadb
from chromadb.config import Settings
import os
from datetime import datetime
from typing import List, Dict, Optional

# 配置
CHROMA_DIR = "/home/admin/xinhai_legal_api/chroma_db/"
COLLECTION_NAME = "xinclaw_memories"


class ChromaSearch:
    """ChromaDB 向量检索 - 语义搜索"""
    
    def __init__(self, chroma_dir: str = CHROMA_DIR):
        self.chroma_dir = chroma_dir
        os.makedirs(chroma_dir, exist_ok=True)
        
        # 初始化客户端 (本地持久化)
        self.client = chromadb.Client(Settings(
            persist_directory=chroma_dir,
            anonymized_telemetry=False
        ))
        
        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "心海法律 AI 记忆和知识库"}
        )
        
        print(f"✅ ChromaDB 初始化完成：{chroma_dir}")
        print(f"   集合：{COLLECTION_NAME}")
        print(f"   当前文档数：{self.collection.count()}")
    
    def add_memory(self, id: str, content: str, metadata: Dict = None):
        """添加记忆到向量库"""
        if metadata is None:
            metadata = {}
        
        self.collection.add(
            documents=[content],
            metadatas=[metadata],
            ids=[id]
        )
        
        print(f"✅ 添加记忆：{id}")
    
    def add_memories_batch(self, memories: List[Dict]):
        """批量添加记忆"""
        if not memories:
            return
        
        documents = [m['content'] for m in memories]
        metadatas = [m.get('metadata', {}) for m in memories]
        ids = [m['id'] for m in memories]
        
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"✅ 批量添加 {len(memories)} 条记忆")
    
    def search(self, query: str, n_results: int = 5, filter_metadata: Dict = None) -> List[Dict]:
        """语义搜索"""
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=filter_metadata
        )
        
        # 格式化结果
        formatted = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                item = {
                    'content': doc,
                    'id': results['ids'][0][i],
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                    'distance': results['distances'][0][i] if 'distances' in results else None
                }
                formatted.append(item)
        
        return formatted
    
    def search_similar_questions(self, question: str, n_results: int = 5) -> List[Dict]:
        """搜索相似问题"""
        return self.search(
            query=question,
            n_results=n_results,
            filter_metadata={"type": "question"}
        )
    
    def search_code(self, query: str, n_results: int = 5) -> List[Dict]:
        """搜索代码片段"""
        return self.search(
            query=query,
            n_results=n_results,
            filter_metadata={"type": "code"}
        )
    
    def delete_memory(self, id: str):
        """删除记忆"""
        self.collection.delete(ids=[id])
        print(f"✅ 删除记忆：{id}")
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'collection_name': COLLECTION_NAME,
            'document_count': self.collection.count(),
            'chroma_dir': self.chroma_dir,
            'dir_size': self._get_dir_size()
        }
    
    def _get_dir_size(self) -> int:
        """计算目录大小"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(self.chroma_dir):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        return total_size
    
    def close(self):
        """关闭连接"""
        pass  # ChromaDB 自动持久化


# 命令行工具
if __name__ == '__main__':
    import sys
    
    search = ChromaSearch()
    
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python3 chroma_search.py stats              # 显示统计")
        print("  python3 chroma_search.py add <id> <content> # 添加记忆")
        print("  python3 chroma_search.py search <query>     # 语义搜索")
        print("  python3 chroma_search.py test               # 测试")
        sys.exit(0)
    
    command = sys.argv[1]
    
    if command == 'stats':
        stats = search.get_stats()
        print("\n📊 ChromaDB 统计")
        print("=" * 50)
        print(f"集合名称：{stats['collection_name']}")
        print(f"文档数量：{stats['document_count']}")
        print(f"数据目录：{stats['chroma_dir']}")
        print(f"目录大小：{stats['dir_size'] / 1024 / 1024:.2f} MB")
    
    elif command == 'add' and len(sys.argv) > 3:
        memory_id = sys.argv[2]
        content = ' '.join(sys.argv[3:])
        search.add_memory(
            id=memory_id,
            content=content,
            metadata={"type": "manual", "added_at": datetime.now().isoformat()}
        )
    
    elif command == 'search' and len(sys.argv) > 2:
        query = ' '.join(sys.argv[2:])
        print(f"\n🔍 语义搜索：{query}")
        print("=" * 50)
        results = search.search(query, n_results=5)
        for i, r in enumerate(results, 1):
            print(f"\n{i}. [{r['id']}]")
            print(f"   内容：{r['content'][:200]}...")
            if r['metadata']:
                print(f"   元数据：{r['metadata']}")
            if r['distance']:
                print(f"   距离：{r['distance']:.4f}")
    
    elif command == 'test':
        print("\n🧪 测试 ChromaDB...")
        
        # 添加测试数据
        test_memories = [
            {
                "id": "test_001",
                "content": "心海法律 AI 的会员价格：新人福利 3 天免费，首月¥1，次月¥30/月，季卡¥80，年卡¥288",
                "metadata": {"type": "question", "category": "pricing"}
            },
            {
                "id": "test_002",
                "content": "Token 计费规则：2 元=10,000 Token，新用户赠送 2,000 Token，所有 AI 操作按实际消耗扣费",
                "metadata": {"type": "question", "category": "token"}
            },
            {
                "id": "test_003",
                "content": "登录接口问题修复：数据库路径从/xinhai_legal.db 改为/xinhai_legal_api/data/xinhai_legal.db",
                "metadata": {"type": "fix", "category": "bug"}
            }
        ]
        
        print("\n添加测试数据...")
        search.add_memories_batch(test_memories)
        
        # 测试搜索
        print("\n🔍 测试搜索 '会员价格'...")
        results = search.search("会员价格多少钱", n_results=3)
        for r in results:
            print(f"\n  [{r['id']}] 距离：{r['distance']:.4f}")
            print(f"  {r['content'][:100]}...")
        
        print("\n🔍 测试搜索 'Token 计费'...")
        results = search.search("Token 怎么收费", n_results=3)
        for r in results:
            print(f"\n  [{r['id']}] 距离：{r['distance']:.4f}")
            print(f"  {r['content'][:100]}...")
        
        print("\n✅ 测试完成")
    
    search.close()
