"""
心海法律 AI - Hindsight Cloud 记忆管理工具

用法:
    python hindsight_memory.py retain "记忆内容" --context "分类"
    python hindsight_memory.py recall "搜索关键词"
    python hindsight_memory.py list --limit 20
    python hindsight_memory.py sync  # 同步项目状态
"""

import argparse
import json
import datetime
import sys
from hindsight_client import Hindsight

# 配置
TOKEN = "hsk_87ff310d8059c5a1729da76b879abbf5_370e60b8e570220c"
API_URL = "https://api.hindsight.vectorize.io"
BANK_ID = "xinclaw_coo"

def get_client():
    return Hindsight(base_url=API_URL, api_key=TOKEN)

def retain(content, context="general"):
    """写入记忆"""
    h = get_client()
    result = h.retain(content=content, context=context, bank_id=BANK_ID)
    print(f"✅ 记忆已写入 (context={context})")
    return result

def recall(query, limit=10):
    """读取记忆"""
    h = get_client()
    result = h.recall(query=query, bank_id=BANK_ID)
    print(f"📖 找到 {len(result)} 条相关记忆:\n")
    for i, r in enumerate(result[:limit], 1):
        print(f"{i}. [{r.context or 'general'}] {r.text}")
        print(f"   时间：{r.mentioned_at or r.occurred_start}\n")
    return result

def list_memories(limit=20):
    """列出所有记忆"""
    h = get_client()
    result = h.list_memories(bank_id=BANK_ID, limit=limit)
    print(f"📋 共 {result.total} 条记忆:\n")
    for item in result.items[:limit]:
        if isinstance(item, dict):
            print(f"- [{item.get('context', 'general')}] {item.get('text', '')[:100]}...")
        else:
            print(f"- [{getattr(item, 'context', 'general')}] {getattr(item, 'text', '')[:100]}...")
    return result

def sync_project_status():
    """同步项目状态到云端"""
    print("="*70)
    print("心海法律 AI - 项目状态同步")
    print("="*70)
    
    h = get_client()
    now = datetime.datetime.now().isoformat()
    
    # 项目状态
    h.retain(
        content=f"心海法律 AI 项目已完成 15 个 Phase（Phase 2-11,13），代码量超过 24 万行。包括会员系统、支付系统、用户认证、AI 对话、文书生成等核心功能。",
        context="project_status",
        bank_id=BANK_ID
    )
    print("✅ 项目状态已同步")
    
    # 服务器信息
    h.retain(
        content=f"心海法律 AI 服务器：8.218.93.213 (root), API 路径 /home/admin/xinhai_legal_api, Flask 端口 5000",
        context="server_config",
        bank_id=BANK_ID
    )
    print("✅ 服务器信息已同步")
    
    # 待办事项
    h.retain(
        content="心海法律 AI 待办：1) Phase 3 合同审阅开发 2) 小程序登录修复 3) 图片识别 API 401 修复",
        context="pending_tasks",
        bank_id=BANK_ID
    )
    print("✅ 待办事项已同步")
    
    print("\n同步完成！")

def main():
    parser = argparse.ArgumentParser(description="Hindsight 记忆管理工具")
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # retain 命令
    retain_parser = subparsers.add_parser('retain', help='写入记忆')
    retain_parser.add_argument('content', help='记忆内容')
    retain_parser.add_argument('--context', '-c', default='general', help='记忆分类')
    
    # recall 命令
    recall_parser = subparsers.add_parser('recall', help='读取记忆')
    recall_parser.add_argument('query', help='搜索关键词')
    recall_parser.add_argument('--limit', '-l', type=int, default=10, help='返回数量')
    
    # list 命令
    list_parser = subparsers.add_parser('list', help='列出记忆')
    list_parser.add_argument('--limit', '-l', type=int, default=20, help='返回数量')
    
    # sync 命令
    sync_parser = subparsers.add_parser('sync', help='同步项目状态')
    
    args = parser.parse_args()
    
    if args.command == 'retain':
        retain(args.content, args.context)
    elif args.command == 'recall':
        recall(args.query, args.limit)
    elif args.command == 'list':
        list_memories(args.limit)
    elif args.command == 'sync':
        sync_project_status()
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
