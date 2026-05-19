#!/usr/bin/env python3
# 会话压缩数据解压脚本
import gzip
import json
import base64

def decompress_sessions(archive_path):
    with open(archive_path) as f:
        data = json.load(f)
    
    compressed = base64.b64decode(data['compressed_data'])
    decompressed = gzip.decompress(compressed)
    sessions = json.loads(decompressed)
    
    print(f"解压完成：{len(sessions)} 个会话")
    for s in sessions:
        print(f"  - {s['session_id']}: {s['summary']}")
    return sessions

if __name__ == '__main__':
    decompress_sessions('/home/admin/xinhai_legal_api/sessions_archive.json')
