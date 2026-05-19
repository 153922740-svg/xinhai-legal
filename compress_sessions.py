#!/usr/bin/env python3
"""
会话压缩脚本 - 心海法律 AI
用途：将历史会话压缩存储到 Hindsight 云记忆，防止 COO 失忆

使用方法:
    python3 compress_sessions.py [会话摘要文件]

输出:
    - sessions_archive.json (压缩存档)
    - 同时尝试存入 Hindsight 云记忆
"""

import gzip
import json
import base64
import sys
import os
from datetime import datetime

# 配置
ARCHIVE_PATH = "/home/admin/xinhai_legal_api/sessions_archive.json"
HINDSIGHT_CONFIG = "~/.hindsight/config.json"

def load_hindsight_config():
    """加载 Hindsight 配置"""
    config_path = os.path.expanduser(HINDSIGHT_CONFIG)
    try:
        with open(config_path) as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ 无法加载 Hindsight 配置：{e}")
        return None

def compress_sessions(sessions_data):
    """压缩会话数据"""
    sessions_json = json.dumps(sessions_data, ensure_ascii=False)
    original_size = len(sessions_json.encode('utf-8'))
    
    # gzip 压缩
    compressed = gzip.compress(sessions_json.encode('utf-8'))
    compressed_size = len(compressed)
    compression_ratio = (1 - compressed_size / original_size) * 100
    
    # base64 编码
    compressed_b64 = base64.b64encode(compressed).decode('ascii')
    
    return {
        "compressed_data": compressed_b64,
        "original_size": original_size,
        "compressed_size": compressed_size,
        "compression_ratio": compression_ratio,
        "session_count": len(sessions_data),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "description": "心海法律 AI 历史会话压缩存档"
    }

def save_archive(archive_data, path):
    """保存压缩存档到文件"""
    with open(path, 'w') as f:
        json.dump(archive_data, f, ensure_ascii=False, indent=2)
    print(f"✅ 压缩存档已保存到 {path}")

def decompress_archive(path):
    """解压会话存档"""
    with open(path) as f:
        data = json.load(f)
    
    compressed = base64.b64decode(data['compressed_data'])
    decompressed = gzip.decompress(compressed)
    sessions = json.loads(decompressed)
    
    return sessions, data

def main():
    print("══════════════════════════════════════════════")
    print("  心海法律 AI · 会话压缩工具")
    print(f"  时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("══════════════════════════════════════════════")
    
    # 示例会话数据（实际使用时从 session_search 获取）
    sample_sessions = [
        {
            "session_id": "20260518_063100_current",
            "when": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "source": "weixin",
            "summary": "会话压缩存储系统建立：创建 ISSUES_TRACKING.md/压缩脚本/解压脚本/工作流文档"
        }
    ]
    
    # 如果有输入文件，读取会话数据
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        try:
            with open(input_file) as f:
                sample_sessions = json.load(f)
            print(f"📋 从 {input_file} 加载了 {len(sample_sessions)} 个会话")
        except Exception as e:
            print(f"⚠️ 无法读取 {input_file}: {e}")
    
    print(f"\n📋 准备压缩 {len(sample_sessions)} 个会话...")
    
    # 压缩
    archive_data = compress_sessions(sample_sessions)
    
    print(f"   原始大小：{archive_data['original_size']:,} 字节")
    print(f"   压缩后：{archive_data['compressed_size']:,} 字节")
    print(f"   压缩率：{archive_data['compression_ratio']:.1f}%")
    print(f"   Base64 后：{len(archive_data['compressed_data']):,} 字符")
    
    # 保存
    save_archive(archive_data, ARCHIVE_PATH)
    
    # 检查 Hindsight 配置
    config = load_hindsight_config()
    if config:
        print(f"\n✅ Hindsight 配置已加载:")
        print(f"   Bank ID: {config.get('bank_id', 'N/A')}")
        print(f"   Mode: {config.get('mode', 'N/A')}")
        print(f"   API URL: {config.get('api_url', 'N/A')}")
        print("\n💡 下一步：使用 curl 将压缩数据存入 Hindsight")
        print(f"""
curl -X POST https://api.hindsight.vectorize.io/retain \\
  -H "Authorization: Bearer $HINDSIGHT_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "bank_id": "{config.get('bank_id', 'xinclaw_coo')}",
    "content": "会话压缩存档...",
    "metadata": {{"type": "sessions_archive", "date": "{datetime.now().strftime('%Y-%m-%d')}"}}
  }}'
        """)
    else:
        print("\n⚠️ Hindsight 配置未找到，仅保存到文件系统")
    
    print("\n══════════════════════════════════════════════")
    print("  压缩完成")
    print("══════════════════════════════════════════════")

if __name__ == '__main__':
    main()
